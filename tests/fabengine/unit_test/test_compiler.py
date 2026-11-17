##############################################################################
# (C) Crown copyright, Met Office. All rights reserved.
# The file LICENCE, distributed with this code, contains details of the terms
# under which the code may be used.
##############################################################################
from pathlib import Path

from pytest import MonkeyPatch, fixture, mark, raises
from pytest_subprocess import FakeProcess

from fabengine.compiler import FortranCompiler
from fabengine.exception import FabEngineError


class TestFortranCompiler:
    @mark.parametrize("addendum", ["", "-1.2.3"])
    def test_constructor(self, addendum: str):
        test_unit = FortranCompiler(Path(f"fortran{addendum}"), "-C",
                                    "-I", "-L", "-M", "-l", "-o")
        assert test_unit.identifier == "fortran"

    def test_compile_object(self, fake_process: FakeProcess):
        fake_process.register([fake_process.any()])

        test_unit = FortranCompiler(Path("/usr/local/bin/tfortran"),
                                    "-no-link",
                                    "-include-path", "-library-path",
                                    "-module-path","-library",
                                    "-output-path")
        _ = test_unit.compile_object([Path("/usr/local/include"),
                                      Path("include")],
                                     Path("work/modules"),
                                     Path("source/test.f90"),
                                     Path("work/test.o"))
        assert list(fake_process.calls) == [
            ["/usr/local/bin/tfortran",
             "-module-path", "work/modules",
             "-include-path", "/usr/local/include",
             "-include-path", "include",
             "-output-path", "work/test.o",
             "-no-link",
             "source/test.f90"]
        ]

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
                assert compiler == FortranCompiler(
                    environment_file, "-C", "-I", "-L", "-M", "-l", "-o"
                )
            else:
                assert compiler == FortranCompiler(
                    command_file, "-C", "-I", "-L", "-M", "-l", "-o"
                )
