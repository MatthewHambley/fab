##############################################################################
# (c) Crown copyright Met Office. All rights reserved.
# For further details please refer to the file COPYRIGHT
# which you should have received as part of this distribution
##############################################################################
"""
PSyclone tooling.
"""
from pathlib import Path
import re
from typing import Callable, List, Optional, Tuple, Union, TYPE_CHECKING

from fab.tools.category import Category
from fab.tools.tool import Tool

from source.fab import FabException

if TYPE_CHECKING:
    # TODO 314: see if this circular dependency can be broken
    # Otherwise we have a circular dependency:
    # BuildConfig needs ToolBox which imports __init__ which imports this
    from fab.build_config import BuildConfig


class Psyclone(Tool):
    """
    Invokes the PSyclone tool.
    """
    def __init__(self):
        super().__init__("psyclone", "psyclone", Category.PSYCLONE)
        self._version = None

    @property
    def is_available(self) -> bool:
        """
        Determines PSyclone availability.

        In addition, it also determines the version since a number of
         behaviours are version dependent.
        """
        available = super().is_available

        if available and self._version is None:
            version_output = self.run(["--version"], capture_output=True)
            pattern = r"PSyclone version: (\d[\d.]+\d)"
            match = re.search(pattern, version_output)
            if match:
                self._version = tuple(int(x) for x in match.group(1).split('.'))
            else:
                raise FabException(
                    f"Unexpected version information for PSyclone: "
                    f"'{version_output}'."
                )

        return available and (self._version is not None)

    @property
    def version(self) -> Tuple[int, ...]:
        if self._version is None:
            _ = self.is_available
        return self._version

    def process(self,
                config: "BuildConfig",
                x90_file: Path,
                psy_file: Optional[Path] = None,
                alg_file: Optional[Union[Path, str]] = None,
                transformed_file: Optional[Path] = None,
                transformation_script: Optional[Callable[[Path, "BuildConfig"],
                                                         Path]] = None,
                additional_parameters: Optional[List[str]] = None,
                kernel_roots: Optional[List[Union[str, Path]]] = None,
                api: Optional[str] = None,
                ):
        # pylint: disable=too-many-arguments, too-many-branches
        '''Run PSyclone with the specified parameters. If PSyclone is used to
        transform existing Fortran files, `api` must be None, and the output
        file name is `transformed_file`. If PSyclone is using its DSL
        features, api must be a valid PSyclone API, and the two output
        filenames are `psy_file` and `alg_file`.

        :param api: the PSyclone API.
        :param x90_file: the input file for PSyclone
        :param psy_file: the output PSy-layer file.
        :param alg_file: the output modified algorithm file.
        :param transformed_file: the output filename if PSyclone is called
            as transformation tool.
        :param transformation_script: an optional transformation script
        :param additional_parameters: optional additional parameters
            for PSyclone
        :param kernel_roots: optional directories with kernels.
        '''
        try:
            _ = self.is_available
        except RuntimeError as ex:
            raise RuntimeError(
                "PSyclone present but version unobtainable."
                " Is installation broken?"
            ) from ex

        # Convert the old style API nemo to be empty
        if api and api.lower() == "nemo":
            api = ""

        if api:
            # API specified, we need both psy- and alg-file, but not
            # transformed file.
            if not psy_file:
                raise RuntimeError(f"PSyclone called with api '{api}', but "
                                   f"no psy_file is specified.")
            if not alg_file:
                raise RuntimeError(f"PSyclone called with api '{api}', but "
                                   f"no alg_file is specified.")
            if transformed_file:
                raise RuntimeError(f"PSyclone called with api '{api}' and "
                                   f"transformed_file.")
        else:
            if psy_file:
                raise RuntimeError("PSyclone called without api, but "
                                   "psy_file is specified.")
            if alg_file:
                raise RuntimeError("PSyclone called without api, but "
                                   "alg_file is specified.")
            if not transformed_file:
                raise RuntimeError("PSyclone called without api, but "
                                   "transformed_file is not specified.")

        parameters: List[Union[str, Path]] = []
        # If an api is defined in this call (or in the constructor) add it
        # as parameter. No API is required if PSyclone works as
        # transformation tool only, so calling PSyclone without api is
        # actually valid.
        if api:
            if self.version >= (3, 0, 0):
                api_param = "--psykal-dsl"
                # Mapping from old names to new names:
                mapping = {"dynamo0.3": "lfric",
                           "gocean1.0": "gocean"}
            else:
                api_param = "-api"
                # Mapping from new names to old names:
                mapping = {"lfric": "dynamo0.3",
                           "gocean": "gocean1.0"}
            # Make mypy happy - we tested above that these variables
            # are defined
            assert psy_file
            assert alg_file
            parameters.extend([api_param, mapping.get(api, api),
                               "-opsy", psy_file, "-oalg", alg_file])
        else:   # no api
            # Make mypy happy - we tested above that transformed_file is
            # specified when no api is specified.
            assert transformed_file
            if self.version >= (3, 0, 0):
                # New version: no API, parameter, but -o for output name:
                parameters.extend(["-o", transformed_file])
            else:
                # 2.5.0 or earlier: needs api nemo, output name is -opsy
                parameters.extend(["-api", "nemo", "-opsy", transformed_file])
        parameters.extend(["-l", "all"])

        if transformation_script:
            transformation_script_return_path = \
                transformation_script(x90_file, config)
            if transformation_script_return_path:
                parameters.extend(['-s', transformation_script_return_path])

        if additional_parameters:
            parameters.extend(additional_parameters)
        if kernel_roots:
            roots_with_dash_d: List[str] = sum([['-d', str(k)]
                                                for k in kernel_roots], [])
            parameters.extend(roots_with_dash_d)
        parameters.append(str(x90_file))
        return self.run(additional_parameters=parameters)
