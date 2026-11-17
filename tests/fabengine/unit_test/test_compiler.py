##############################################################################
# (C) Crown copyright, Met Office. All rights reserved.
# The file LICENCE, distributed with this code, contains details of the terms
# under which the code may be used.
##############################################################################
import os
from pathlib import Path

from pytest import MonkeyPatch, fixture, mark, raises

from fabengine.compiler import FortranCompiler
from fabengine.exception import FabEngineError


class TestFortranCompiler:
    def test_constructor(self):
        """
        Checks basic constructor functionality.
        """
        test_unit = FortranCompiler(Path("fish"))

    def test_determine_compiler_no_command(self, monkeypatch):
        """
        Checks an exception is thrown if no way to determine compiler.
        """
        monkeypatch.delenv("FC", raising=False)
        with raises(FabEngineError):
            FortranCompiler.determine_compile()

    @fixture(scope="function", params=[True, False])
    def executable(self, request):
        return request.param

    @fixture(scope="function",
             params=[None, Path("/absolute_command"), Path("relative_command")])
    def command(self, request, executable, tmp_path: Path):
        if request.param is None:
            filename = tmp_path / "missing_command"
            return filename, None

        if request.param.is_absolute():
            filename = tmp_path / request.param.relative_to("/")
        else:
            filename = tmp_path / request.param
        filename.touch()
        if request.param.is_absolute():
            command = filename
        else:
            command = request.param

        if executable:
            filename.chmod(0o755)

        return filename, command

    @fixture(scope="function",
             params=[None, Path("/absolute_environment"), Path("relative_environment")])
    def environment(self, request, executable: bool, tmp_path: Path, monkeypatch: MonkeyPatch):
        if request.param is None:
            filename = tmp_path/ "missing_environment"
            monkeypatch.delenv("FC", raising=False)
            return filename, None

        if request.param.is_absolute():
            filename = tmp_path / request.param.relative_to("/")
        else:
            filename = tmp_path / request.param
        filename.touch()
        if executable:
            filename.chmod(0o755)

        if request.param.is_absolute():
            environment = filename
        else:
            environment = request.param

        monkeypatch.setenv("FC", str(environment))

        return filename, environment

    def test_determine_compiler_command(self,
                                        command: tuple[Path, Path],
                                        environment: tuple[Path, Path],
                                        executable: bool,
                                        tmp_path: Path,
                                        monkeypatch: MonkeyPatch):
        command_file, command_arg = command
        environment_file, environment_arg = environment

        error_condition = ((command_arg is None and environment_arg is None)
                           or not executable)
        if error_condition:
            with raises(FabEngineError):
                FortranCompiler.determine_compile(command_arg)
        else:
            monkeypatch.chdir(tmp_path)
            compiler = FortranCompiler.determine_compile(command_arg)
            if command_arg is None:
                assert compiler == FortranCompiler(environment_file)
            else:
                assert compiler == FortranCompiler(command_file)

    @mark.parametrize("addendum", ["", "-1.2.3"])
    def test_determine_compiler_identifier(self, addendum: str,
                                           tmp_path: Path):
        filename = tmp_path / f"fortran{addendum}"
        filename.touch()
        filename.chmod(0o755)
        compiler = FortranCompiler.determine_compile(filename)
        assert compiler.identifier == "fortran"
