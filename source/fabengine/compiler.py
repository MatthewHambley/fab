##############################################################################
# (C) Crown copyright, Met Office. All rights reserved.
# The file LICENCE, distributed with this code, contains details of the terms
# under which the code may be used.
##############################################################################
"""
Manages compiler calling details.
"""
from __future__ import annotations

from os import access, environ, X_OK
from pathlib import Path
from shutil import which
from subprocess import run
from typing import Any

from fabengine.exception import FabEngineError


class FortranCompiler:
    def __init__(self, command: Path, no_link_arg: str,
                 include_path_arg: str, library_path_arg: str,
                 module_path_arg: str, library_arg: str, output_arg: str):
        self._command = command
        self._no_link_arg = no_link_arg
        self._include_path_arg = include_path_arg
        self._library_path_arg = library_path_arg
        self._module_path_arg = module_path_arg
        self._library_arg = library_arg
        self._output_arg = output_arg

        # Sometimes the command has the version tacked on the end. We need
        # to remove that.
        #
        self._identifier = self._command.name.split("-", maxsplit=1)[0]

    def __repr__(self) -> str:
        return f"FortranCompiler({self._command})"

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, FortranCompiler):
            return False
        return self._command == other._command

    @property
    def identifier(self) -> str:
        return self._identifier

    def compile_object(self, include_path: list[Path], module_path: Path,
                       source_path: Path, object_path: Path):
        command = [str(self._command), self._module_path_arg, str(module_path)]
        for path in include_path:
            command.extend(([self._include_path_arg, str(path)]))
        command.extend([self._output_arg, str(object_path), self._no_link_arg,
                        str(source_path)])

        result = run(command, capture_output=True, encoding="utf-8")

        if result.returncode != 0:
            raise FabEngineError(
                f"Command {command} failed with code {result.returncode}\n\n"
                f"Standard output:\n{result.stdout}\n\n"
                f"Standard error:\n{result.stderr}\n"
            )

    @staticmethod
    def determine_compile(filename: Path | None = None) -> FortranCompiler:
        try:
            filename = filename or Path(environ["FC"])
        except KeyError:
            raise FabEngineError("Compiler must be specified directly, "
                                 "or through FC environment variable.")
        # If compiler is given as an absolute path, use that. Otherwise, check
        # to see if it's on PATH, if not check to see if it's relative and if
        # so, make it absolute.
        #
        if filename.is_absolute():
            pass
        else:  # filename is relative
            on_path = which(filename)
            if on_path is None:  # Not on path
                filename = filename.resolve()
            else:  # On path
                filename = on_path

        # Confirm we've found something...
        #
        if not filename.exists():
            raise FabEngineError(f"No compiler at <{filename}>")

        # Confirm the thing is actually executable!
        #
        if not access(filename, X_OK):
            raise FabEngineError(f"Compiler <{filename}> is not executable.")

        return FortranCompiler(filename, "-C", "-I", "-L", "-M", "-l", "-o")
