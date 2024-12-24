##############################################################################
# (c) Crown copyright Met Office. All rights reserved.
# For further details please refer to the file COPYRIGHT
# which you should have received as part of this distribution
##############################################################################

"""This file contains the Rsync class for synchronising file trees.
"""

import os
from pathlib import Path
from typing import List, Union

from fab.category import Category
from fab.tools import Tool


class Rsync(Tool):
    '''This is the base class for `rsync`.
    '''

    def __init__(self):
        super().__init__("rsync", "rsync", Category.RSYNC)

    def execute(self, src: Path, dst: Path):
        """
        Rsync from src to dst.

        "~" expansion is supported for src and makes sure that `src` ends with
        a `/` to avoid creating a sub-directory.

        :param src: the input path.
        :param dst: destination path.
        """
        src_str = os.path.expanduser(str(src))
        if not src_str.endswith('/'):
            src_str += '/'

        parameters: List[Union[str, Path]] = [
            '--times', '--links', '--stats', '-ru', src_str, dst]
        return self.run(additional_parameters=parameters)
