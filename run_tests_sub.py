#!/usr/bin/env python

"""

Runs tests in subprocesses using subprocess and async_sub. Will poll tests for
return code and if tests don't return after TIME_OUT, will kill process with 
os.kill.

os.kill is defined on win32 platform using subprocess.Popen to call either 
pskill or taskkill if available on the system $PATH. If not, the script will
raise SystemExit. 

taskkill is shipped with windows from XP on.
pskill is available from SysInternals website

Dependencies:
    async_sub.py:
        Requires win32 extensions when run on windows:
            Maybe able to get away with win32file.pyd, win32pipe.pyd zipped to 
            about 35kbytes and ship with that.
"""

#################################### IMPORTS ###################################

import sys, os, re, unittest, subprocess, time, pygame.threads, async_sub

main_dir = os.path.split(os.path.abspath(sys.argv[0]))[0]
test_subdir = os.path.join(main_dir, 'test')

sys.path += [test_subdir]

import test_utils

################################### CONSTANTS ##################################

# If an xxxx_test.py take longer than TIME_OUT seconds it will be killed

TIME_OUT = 30

# Any tests in IGNORE will not be ran

IGNORE = (
    # "scrap_test.py",         # No need to ignore as pygame.init() in another
                               # process
)

# Division in test output that afterwards shows "Ran x tests, OK" etc
DIV = (70 * "-") + "\nRan"

################################################################################

TEST_MODULE_RE = re.compile('^(.+_test\.py)$')

NUM_TESTS_RE   = re.compile(r"Ran (\d+) tests?")
NUM_FAILS_RE   = re.compile(r"failures=(\d+)")
NUM_ERRORS_RE  = re.compile(r"errors=(\d+)")

def count_of(regex, test_output):
    count = regex.search(test_output)
    return count and int(count.group(1)) or 0

################################################################################

if sys.platform == 'win32':
    win32_kill_commands = (
        ('pskill', 'pskill -t %s'),
        ('taskkill /?', 'taskkill /F /T /PID %s'),  # /? so no err code
    )

    for test_cmd, kill_cmd in win32_kill_commands:
        test_cmd_ret_code = subprocess.Popen(
            test_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            shell = 1,
        ).wait()

        if test_cmd_ret_code is not 1:
            os.kill = lambda pid: (
                subprocess.Popen(
                    kill_cmd % pid, stdout=subprocess.PIPE, 
                    stderr=subprocess.STDOUT, shell = 1,
                )
            )
            print '\nUsing subprocess.Popen("%s" '%kill_cmd+'% pid) for os.kill\n'
            break

        else: os.kill = None

    if os.kill is None:
        raise SystemExit('No way of killing unruly processes. Try installing '
                         'sysinternals pskill and placing on %PATH%.')

################################################################################

def run_test(cmd):
    test_name = os.path.basename(cmd)
    print 'running %s' % test_name

    proc = async_sub.Popen (
        cmd, shell = True, bufsize = -1,
        stdin = subprocess.PIPE, stdout = subprocess.PIPE, 
        stderr = subprocess.STDOUT, universal_newlines = 1
    )

    ret_code = None
    response = []

    t = time.time()
    while ret_code is None and ((time.time() -t) < TIME_OUT):
        ret_code = proc.poll()
        response += [proc.read_async(wait=0.1, e=0)]

    if ret_code is None:
        os.kill(proc.pid)
        ret_code = '"Process timed out (TIME_OUT = %s secs)"' % TIME_OUT

    response = ''.join(response)

    return test_name, ret_code, response

################################################################################

os.chdir(main_dir) 
test_cmds = [('python test/%s' % f) for f in os.listdir(test_subdir) 
                                          if TEST_MODULE_RE.match(f) 
                                          and f not in IGNORE]
t = time.time()

if '-t' in sys.argv:
    test_results = pygame.threads.tmap (
        run_test, test_cmds,
        stop_on_error = False,
        num_workers = len(sys.argv) == 3 and int(sys.argv[2]) or 4
    )
else:
    test_results = map(run_test, test_cmds)

t = time.time() - t

################################################################################

total_tests = total_fails = total_errors = 0

complete_failures = {}

for module, ret_code, ret in test_results:
    if ret_code:
        complete_failures[module] = ret_code, ret
        continue

    total_errors += count_of(NUM_ERRORS_RE, ret)
    total_fails  += count_of(NUM_FAILS_RE,  ret)
    total_tests  += count_of(NUM_TESTS_RE,  ret)

    print "%s %s" % (module, 'OK' in ret and 'OK' or ret.split(DIV)[0])

print "\n%s %s tests in %.3fs\n" % (DIV, total_tests, t)

if not total_errors and not total_fails:
    print 'OK'
else:
    print 'FAILED (failures=%s, errors=%s)' % (total_fails, total_errors)

################################################################################

if complete_failures: print '\n%s\nComplete Failures\n' % (70 * '=')
for module, (ret_code, ret) in complete_failures.iteritems():
    print "%s failed with return code of %s\n%s" % (module, ret_code, ret)

################################################################################