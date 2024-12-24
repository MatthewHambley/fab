##############################################################################
# (c) Crown copyright Met Office. All rights reserved.
# For further details please refer to the file COPYRIGHT
# which you should have received as part of this distribution
##############################################################################
"""
Source code preprocessor support.
"""
from pathlib import Path
from typing import List, Optional, Union

from fab.category import Category
from fab.tools import Tool


class Preprocessor(Tool):
    '''This is the base class for any preprocessor.

    :param name: the name of the preprocessor.
    :param executable: the name of the executable.
    :param category: the category (C_PREPROCESSOR or FORTRAN_PREPROCESSOR)
    '''

    def __init__(self, name: str, executable: Union[str, Path],
                 category: Category,
                 availability_argument: Optional[str] = None):
        super().__init__(name, executable, category)
        self._version = None

    def preprocess(self, input_file: Path, output_file: Path,
                   add_flags: Optional[List[Union[Path, str]]] = None):
        """
        Calls the preprocessor to process the specified input file,
        creating the requested output file.

        :param input_file: input file.
        :param output_file: the output filename.
        :param add_flags: List with additional flags to be used.
        """
        params: List[Union[str, Path]] = []
        if add_flags is not None:
            # Make a copy to avoid modifying the caller's list
            params.extend(add_flags)

        # Input and output files come as the last two parameters
        params.extend([input_file, output_file])

        return self.run(additional_parameters=params)


# ============================================================================
class Cpp(Preprocessor):
    '''Class for cpp.
    '''
    def __init__(self):
        super().__init__("cpp", "cpp", Category.C_PREPROCESSOR)


# ============================================================================
class CppFortran(Preprocessor):
    '''Class for cpp when used as a Fortran preprocessor
    '''
    def __init__(self):
        super().__init__("cpp", "cpp", Category.FORTRAN_PREPROCESSOR)
        self.flags.extend(["-traditional-cpp", "-P"])


# ============================================================================
class Fpp(Preprocessor):
    '''Class for Intel's Fortran-specific preprocessor.
    '''
    def __init__(self):
        # fpp -V prints version information, but then hangs (i.e. reading
        # from stdin), so use -what to see if it is available
        super().__init__("fpp", "fpp", Category.FORTRAN_PREPROCESSOR,
                         availability_argument="-what")
