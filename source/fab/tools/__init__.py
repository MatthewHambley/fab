##############################################################################
# (c) Crown copyright Met Office. All rights reserved.
# For further details please refer to the file COPYRIGHT
# which you should have received as part of this distribution
##############################################################################
"""
Base classes for tools.

Each tool belongs to one category (e.g. FORTRAN_COMPILER). This category
is used when adding a tool to a ToolRepository or ToolBox.
It provides basic support for running a binary, and keeping track if
a tool is actually available.
"""
from logging import getLogger
from pathlib import Path
from subprocess import run
from typing import Union, Optional, List, Dict

from fab.category import Category
from fab.flags import Flags


PathLike = Union[Path, str]


class Tool:
    """
    Ultimate base class for all tools.

    It stores the name of the tool, the path of the executable and provides a
    `run` method.

    :param name: Identifier for the tool.
    :param executable: Path, absolute or relative, for the tool.
    :param category: This tool belongs to this category.
    :param availability_argument: Command-line argument used to check if the tool
                                exists on the current system.
    """
    def __init__(self, name: str, executable: PathLike,
                 category: Category = Category.MISC,
                 availability_argument: str = '--version'):
        self.__name = name
        self.__executable = Path(executable)
        self.__flags = Flags()
        self.__category = category
        self.__availability_argument = availability_argument

        # This flag keeps track if a tool is available on the system or not.
        # A value of `None` means that it has not been tested if a tool works
        # or not. It will be set to the output of `check_available` when
        # querying the `is_available` property.
        # If `_is_available` is False, any call to `run` will immediately
        # raise a RuntimeError. As long as it is still set to None (or True),
        # the `run` method will work, allowing the `check_available` method
        # to use `run` to determine if a tool is available or not.
        self.__is_available: Optional[bool] = None

    @property
    def is_available(self) -> bool:
        """
        Checks if the tool is available or not.
        """
        if self.__is_available is None:
            is_available = True
            try:
                self.run(self.__availability_argument)
            except (RuntimeError, FileNotFoundError):
                is_available = False
            self.__is_available = is_available
        return self.__is_available

    @property
    def is_compiler(self) -> bool:
        """
        Checks whether this tool is a compiler.
        """
        return self.__category.is_compiler

    @property
    def executable(self) -> Path:
        """
        Gets the executable filename.
        """
        return self.__executable

    def change_exec_name(self, executable: PathLike):
        """Changes the name of the executable This function should in general
        not be used (typically it is better to create a new tool instead). The
        function is only provided to support CompilerWrapper (like mpif90),
        which need all parameters from the original compiler, but call the
        wrapper. The name of the compiler will be changed just before
        compilation, and then set back to its original value"""
        self.__executable = Path(executable)

    @property
    def name(self) -> str:
        """
        Gets the identifying name of this tool.
        """
        return self.__name

    @property
    def availability_argument(self) -> str:
        """
        Gets the argument used to check for availability.
        """
        return self.__availability_argument

    @property
    def category(self) -> Category:
        """
        Gets this tool's category.
        """
        return self.__category

    @property
    def flags(self) -> Flags:
        """
        Gets the command-line arguments used with this tool.
        """
        return self.__flags

    def add_flags(self, new_flags: Union[str, List[str]]):
        """
        Extends the collection of command-line arguments to use with this tool.
        """
        self.__flags.add_flags(new_flags)

    def __str__(self):
        return f"{type(self).__name__} - {self.__name}: {self.__executable}"

    def run(self,
            additional_parameters: Optional[Union[str, List[PathLike]]] = None,
            env: Optional[Dict[str, str]] = None,
            cwd: Optional[PathLike] = None,
            capture_output=True) -> Optional[str]:
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
            Returns command's standard output if true, otherwise returns None.
            Either way, logs standard output at "debug" level.

        :raises RuntimeError: if the code is not available.
        :raises RuntimeError: if the return code of the executable is not 0.
        """

        command = [str(self.executable)] + self.flags
        if additional_parameters:
            if isinstance(additional_parameters, str):
                command.append(additional_parameters)
            else:
                # Convert everything to a str, this is useful for supporting
                # paths as additional parameter
                command.extend(str(i) for i in additional_parameters)

        # self._is_available is None when it is not known yet whether a tool
        # is available or not. Testing for `False` only means this `run`
        # function can be used to test if a tool is available.
        if self.__is_available is False:
            raise RuntimeError(f"Tool '{self.name}' is not available to run "
                               f"'{command}'.")
        getLogger(__name__).debug(f'run_command: {" ".join(command)}')
        try:
            cwd_arg: Optional[str]
            if cwd is not None:
                cwd_arg = str(cwd)
            else:
                cwd_arg = cwd
            res = run(command, capture_output=True,
                      env=env, cwd=cwd_arg, check=False)
        except FileNotFoundError as err:
            raise RuntimeError(f"Command '{' '.join(command)}' could not be "
                               f"executed.") from err
        if res.returncode != 0:
            msg = (f'Command failed with return code {res.returncode}:\n'
                   + ' '.join(command))
            if res.stdout:
                msg += f'\n{res.stdout.decode()}'
            if res.stderr:
                msg += f'\n{res.stderr.decode()}'
            raise RuntimeError(msg)
        getLogger(__name__).debug("Command output: " + res.stdout.decode())
        if capture_output:
            return res.stdout.decode()
        return None


class CompilerSuiteTool(Tool):
    """
    A tool that is part of a compiler suite (typically compiler
    and linker).

    :param name: name of the tool.
    :param executable: name of the executable to start.
    :param suite: name of the compiler suite.
    :param category: the Category to which this tool belongs.
    :param availability_argument: a command line option for the tool to test
        if the tool is available on the current system. Defaults to
        `--version`.
    """
    def __init__(self, name: str, executable: PathLike, suite: str,
                 category: Category,
                 availability_argument: Optional[str] = None):
        super().__init__(name, executable, category,
                         availability_argument=availability_argument or "--version")
        self._suite = suite

    @property
    def suite(self) -> str:
        ''':returns: the compiler suite of this tool.'''
        return self._suite
