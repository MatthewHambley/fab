##############################################################################
# (c) Crown copyright Met Office. All rights reserved.
# For further details please refer to the file COPYRIGHT
# which you should have received as part of this distribution
##############################################################################
"""
Base of all tools.

Each tool belongs to one category (e.g. FORTRAN_COMPILER). This category
is used when adding a tool to a ToolRepository or ToolBox.
It provides basic support for running a binary, and keeping track if
a tool is actually available.
"""
import logging
from pathlib import Path
from shutil import which as sh_which
from subprocess import run as subprocess_run
from typing import Dict, List, Optional, Sequence, Union

from fab.tools.category import Category
from fab.tools.flags import ProfileFlags


class Tool:
    """
    Embodies a simple tool.

    It stores the name of the tool, the name of the executable, and provides a
    `run` method.

    :param name: Unique identifier for tool.
    :param executable: Full or relative path of this tool's executable.
                       Relative paths must be a leaf name only.
    :param category: Sorts this tool into this grouping.
    """

    def __init__(self, name: str, executable: Union[str, Path],
                 category: Category = Category.MISC):
        self._logger = logging.getLogger(__name__)
        self._name = name
        self._executable = Path(executable)
        self._flags = ProfileFlags()
        self._category = category

        # This flag keeps track if a tool is available on the system or not.
        # A value of `None` means that it has not been tested if a tool works
        # or not. It will be set to the output of `check_available` when
        # querying the `is_available` property.
        # If `_is_available` is False, any call to `run` will immediately
        # raise a RuntimeError. As long as it is still set to None (or True),
        # the `run` method will work, allowing the `check_available` method
        # to use `run` to determine if a tool is available or not.
        self._is_available: Optional[bool] = None

    def set_full_path(self, full_path: Path):
        """
        Updates this tool's executable path.

        This is useful when a tool's executable is not on $PATH. Calling this
        will cause a new availability check.

        :param full_path: New executable path.
        """
        self._executable = full_path
        self._is_available = None
        self._check_availability()

    @property
    def is_available(self) -> bool:
        """
        Determines this tool's availability.

        The tool's executable is sought on $PATH. The result is cached for
        future inquiries.

        :returns: True if the executable is present, False otherwise.
        """
        return self._check_availability()

    @property
    def is_compiler(self) -> bool:
        '''Returns whether this tool is a (Fortran or C) compiler or not.'''
        return self._category.is_compiler

    @property
    def executable(self) -> Path:
        """
        Gets this tool's executable.
        """
        return self._executable

    @property
    def exec_name(self) -> str:
        ''':returns: the name of the executable.'''
        return self.executable.name

    @property
    def name(self) -> str:
        ''':returns: the name of the tool.'''
        return self._name

    @property
    def category(self) -> Category:
        ''':returns: the category of this tool.'''
        return self._category

    def get_flags(self, profile: Optional[str] = None):
        ''':returns: the flags to be used with this tool.'''
        return self._flags[profile]

    def add_flags(self, new_flags: Union[str, List[str]],
                  profile: Optional[str] = None):
        '''Adds the specified flags to the list of flags.

        :param new_flags: A single string or list of strings which are the
            flags to be added.
        '''
        self._flags.add_flags(new_flags, profile)

    def define_profile(self,
                       name: str,
                       inherit_from: Optional[str] = None):
        '''Defines a new profile name, and allows to specify if this new
        profile inherit settings from an existing profile.

        :param name: Name of the profile to define.
        :param inherit_from: Optional name of a profile to inherit
            settings from.
        '''
        self._flags.define_profile(name, inherit_from)

    @property
    def logger(self) -> logging.Logger:
        ''':returns: a logger object for convenience.'''
        return self._logger

    def __str__(self):
        '''Returns a name for this string.
        '''
        return f"{type(self).__name__} - {self._name}: {self._executable}"

    def run(self,
            additional_parameters: Optional[
                Union[str, Sequence[Union[Path, str]]]] = None,
            profile: Optional[str] = None,
            env: Optional[Dict[str, str]] = None,
            cwd: Optional[Union[Path, str]] = None,
            capture_output=True) -> str:
        """
        Run the binary as a subprocess.

        :param additional_parameters:
            List of strings or paths to be sent to :func:`subprocess.run`
            as additional parameters for the command. Any path will be
            converted to a normal string.
        :param env:
            Optional env for the command. By default it will use the current
            session's environment.
        :param capture_output:
            If True, capture and return stdout. If False, the command will
            print its output directly to the console.

        :raises RuntimeError: if the code is not available.
        :raises RuntimeError: if the return code of the executable is not 0.
        """
        command = [str(self.executable)] + self.get_flags(profile)
        if additional_parameters:
            if isinstance(additional_parameters, str):
                command.append(additional_parameters)
            else:
                # Convert everything to a str, this is useful for supporting
                # paths as additional parameter
                command.extend(str(i) for i in additional_parameters)

        if not self._check_availability():
            raise RuntimeError(f"Tool '{self.name}' is not available to run "
                               + str(command))
        self._logger.debug(f'run_command: {" ".join(command)}')
        res = subprocess_run(command, capture_output=capture_output,
                             env=env, cwd=cwd, check=False)
        if res.returncode != 0:
            msg = (f'Command failed with return code {res.returncode}:\n'
                   f'{command}')
            if res.stdout:
                msg += f'\n{res.stdout.decode()}'
            if res.stderr:
                msg += f'\n{res.stderr.decode()}'
            raise RuntimeError(msg)
        if capture_output:
            return res.stdout.decode()
        return ""

    def _check_availability(self) -> bool:
        if self._is_available is None:
            self._is_available = sh_which(self._executable) is not None
        return self._is_available


class CompilerSuiteTool(Tool):
    '''A tool that is part of a compiler suite (typically compiler
    and linker).

    :param name: name of the tool.
    :param executable: name of the executable to start.
    :param suite: name of the compiler suite.
    :param category: the Category to which this tool belongs.
    :param availability_option: a command line option for the tool to test
        if the tool is available on the current system. Defaults to
        `--version`.
    '''
    def __init__(self, name: str, executable: Union[str, Path], suite: str,
                 category: Category):
        super().__init__(name, executable, category)
        self._suite = suite

    @property
    def suite(self) -> str:
        ''':returns: the compiler suite of this tool.'''
        return self._suite
