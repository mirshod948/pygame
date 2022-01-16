"""
buildconfig/stubs/gen_consts.py
A helper script to generate constants.pyi typestub
"""

import pathlib
import pygame.constants

constants_file = pathlib.Path(__file__).parent / "pygame" / "constants.pyi"
with open(constants_file, "w") as f:
    # write the module docstring of this file in the generated file, so that
    # people know this file exists
    f.write(f'"""{__doc__}"""\n\n')
    f.write("from typing import List\n\n\n")

    for element in dir(pygame.constants):
        if element.startswith("_"):
            continue

        constant_type = getattr(pygame.constants, element).__class__.__name__
        f.write(f"{element}: {constant_type}\n")

    f.write("\n__all__: List[str]\n")
