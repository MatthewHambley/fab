##############################################################################
# (c) Crown copyright Met Office. All rights reserved.
# For further details please refer to the file COPYRIGHT
# which you should have received as part of this distribution
##############################################################################
"""
Tests the linker tool.
"""
from pathlib import Path
import warnings

from tests.conftest import ExtendedRecorder

from pytest import mark, raises, warns
from pytest_subprocess.fake_process import FakeProcess

from tests.conftest import call_list

from fab.tools import Category, Linker
from fab.tools.compiler import CCompiler, FortranCompiler


class TestLinker:
    def test_linker_c(self, stub_c_compiler: CCompiler) -> None:
        """
        Tests the constructor taking a compiler.
        """
        linker = Linker(stub_c_compiler)
        assert linker.category == Category.LINKER
        assert linker.name == "linker-some C compiler"
        assert linker.exec_name == "scc"
        assert linker.suite == "stub"
        assert linker.flags == []
        assert linker.output_flag == "-o"

    def test_linker_fortran(self, stub_fortran_compiler: FortranCompiler) -> None:
        """
        Tests the constructor taking a compiler.
        """
        linker = Linker(stub_fortran_compiler)
        assert linker.category == Category.LINKER
        assert linker.name == "linker-some Fortran compiler"
        assert linker.exec_name == "sfc"
        assert linker.suite == "stub"
        assert linker.flags == []
        assert linker.output_flag == "-o"

    @mark.parametrize("mpi", [True, False])
    def test_linker_mpi(self, mpi: bool) -> None:
        """
        Tests MPI switch is handled correctly.
        """
        compiler = CCompiler('stub C compiler', 'scc', 'stub', r'([\d.]+)',
                             mpi=mpi)
        linker = Linker(compiler)
        assert linker.mpi == mpi

        wrapped_linker = Linker(compiler, linker=linker)
        assert wrapped_linker.mpi == mpi

    @mark.parametrize("openmp", [True, False])
    def test_linker_openmp(self, openmp):
        """
        Tests OpenMP behaviour of linker tool.
        """
        if openmp:
            compiler = CCompiler('mock c', 'scc', 'mock', r'([\d.]+)', openmp_flag='-omp')
        else:
            compiler = CCompiler('mock c', 'scc', 'mock', r'([\d.]+)')
        linker = Linker(compiler=compiler)
        assert linker.openmp == openmp

        wrapped_linker = Linker(compiler, linker=linker)
        assert wrapped_linker.openmp == openmp

    def test_linker_gets_ldflags(self, stub_c_compiler: CCompiler,
                                 monkeypatch) -> None:
        """
        Tests the linker retrieves env.LDFLAGS.
        """
        monkeypatch.setenv('LDFLAGS', '-lm')
        linker = Linker(compiler=stub_c_compiler)
        assert "-lm" in linker.flags

    def test_linker_check_available(self, stub_c_compiler: CCompiler,
                                    fake_process: FakeProcess) -> None:
        """
        Tests availability checking.
        """
        compiler_command = ['scc', '--version']
        fake_process.register(compiler_command, stdout='1.2.3')

        linker = Linker(stub_c_compiler)
        assert linker.check_available()

        # Then test the usage of a linker wrapper. The linker will call the
        # corresponding function in the wrapper linker:
        wrapped_linker = Linker(stub_c_compiler, linker=linker)
        assert wrapped_linker.check_available()

        assert call_list(fake_process) == [['scc', '--version']]

    def test_check_unavailable(self, stub_c_compiler: CCompiler,
                               fake_process: FakeProcess) -> None:
        """
        Tests availability check when linker is missing.
        """
        command = ['scc', '--version']
        fake_process.register(command, returncode=1)
        linker = Linker(stub_c_compiler)
        assert linker.check_available() is False
        assert call_list(fake_process) == [command]


class TestLinkerLibFlags:
    def test_get_lib_flags_unknown(self, stub_c_compiler: CCompiler) -> None:
        """
        Tests error on unknown library.
        """
        linker = Linker(stub_c_compiler)
        with raises(RuntimeError) as err:
            linker.get_lib_flags("unknown")
        assert str(err.value).startswith("Unknown library name: 'unknown'")

    def test_library_lifecycle(self, stub_c_compiler: CCompiler) -> None:
        """
        Tests library replacement.
        """
        linker = Linker(stub_c_compiler)

        linker.add_lib_flags('netcdf', ['-lnetcdff', '-lnetcdf'])
        assert linker.get_lib_flags("netcdf") == ["-lnetcdff", "-lnetcdf"]

        # Replace them with another set of flags.
        warn_message = 'Replacing existing flags for library netcdf'
        with warns(UserWarning, match=warn_message):
            linker.add_lib_flags("netcdf", ["-Lnetcdf/lib", "-lnetcdf"])

        # Test that we can see our custom flags
        assert linker.get_lib_flags("netcdf") == ["-Lnetcdf/lib", "-lnetcdf"]

        # Now test without warning.
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            linker.add_lib_flags("netcdf", ["-t", "-b"],
                                 silent_replace=True)

        # Test that we can see our custom flags
        result = linker.get_lib_flags("netcdf")
        assert result == ["-t", "-b"]

    def test_linker_remove_lib_flags(self,
                                     stub_c_compiler: CCompiler) -> None:
        """
        Tests removing library not known to linker.
        """
        linker = Linker(stub_c_compiler)
        linker.remove_lib_flags("netcdf")

        with raises(RuntimeError) as err:
            linker.get_lib_flags("netcdf")
        assert str(err.value).startswith("Unknown library name: 'netcdf'")

    def test_remove_lib_flags_unknown(self,
                                      stub_c_compiler: CCompiler) -> None:
        """
        Tests silent removal of unknown library.
        """
        linker = Linker(stub_c_compiler)
        linker.remove_lib_flags("unknown")


class TestLinkerLinking:
    def test_linker_c(self, stub_c_compiler: CCompiler,
                      subproc_record: ExtendedRecorder) -> None:
        """
        Tests linkwhen no additional libraries are specified.
        """
        linker = Linker(compiler=stub_c_compiler)
        # Add a library to the linker, but don't use it in the link step
        linker.add_lib_flags("customlib", ["-lcustom", "-jcustom"])

        linker.link([Path("a.o")], Path("a.out"), openmp=False)
        assert subproc_record.invocations() == [
            ['scc', "a.o", "-o", "a.out"]
        ]

    def test_c_with_libraries(self, stub_c_compiler: CCompiler,
                              subproc_record: ExtendedRecorder) -> None:
        """
        Tests link when additional libraries are specified.
        """
        linker = Linker(compiler=stub_c_compiler)
        linker.add_lib_flags("customlib", ["-lcustom", "-jcustom"])

        linker.link([Path("a.o")], Path("a.out"),
                    libs=["customlib"], openmp=True)
        # The order of the 'libs' list should be maintained
        assert subproc_record.invocations() == [
            ['scc', "-omp", "a.o", "-lcustom", "-jcustom", "-o", "a.out"]
        ]

    def test_c_with_libraries_and_post_flags(self, stub_c_compiler: CCompiler,
                                             subproc_record: ExtendedRecorder) -> None:
        """
        Tests link when a library and additional flags are specified.
        """
        linker = Linker(compiler=stub_c_compiler)
        linker.add_lib_flags("customlib", ["-lcustom", "-jcustom"])
        linker.add_post_lib_flags(["-extra-flag"])

        linker.link([Path("a.o")], Path("a.out"),
                    libs=["customlib"], openmp=False)
        assert subproc_record.invocations() == [
            ['scc', "a.o", "-lcustom", "-jcustom", "-extra-flag", "-o", "a.out"]
        ]

    def test_c_with_libraries_and_pre_flags(self, stub_c_compiler: CCompiler,
                                            subproc_record: ExtendedRecorder) -> None:
        """
        Tests link when a library and additional flags are specified.
        """
        linker = Linker(compiler=stub_c_compiler)
        linker.add_lib_flags("customlib", ["-lcustom", "-jcustom"])
        linker.add_pre_lib_flags(["-L", "/common/path/"])

        linker.link([Path("a.o")], Path("a.out"),
                    libs=["customlib"], openmp=False)
        assert subproc_record.invocations() == [
            ['scc', "a.o", "-L", "/common/path/", "-lcustom", "-jcustom", "-o", "a.out"]
        ]

    def test_linker_c_with_unknown_library(self, stub_c_compiler: CCompiler):
        """
        Tests the link command raises an error when unknow libraries are specified.
        """
        linker = Linker(compiler=stub_c_compiler)\

        with raises(RuntimeError) as err:
            # Try to use "customlib" when we haven't added it to the linker
            linker.link([Path("a.o")], Path("a.out"),
                        libs=["customlib"], openmp=True)

        assert str(err.value).startswith("Unknown library name: 'customlib'")

    def test_add_compiler_flag(self, stub_c_compiler: CCompiler,
                               subproc_record: ExtendedRecorder) -> None:
        """
        Tests a flag added to the compiler will be automatically added to the link
        line (even if the flags are modified after creating the linker ... in case
        that the user specifies additional flags after creating the linker).
        """
        linker = Linker(compiler=stub_c_compiler)
        stub_c_compiler.flags.append("-my-flag")
        linker.link([Path("a.o")], Path("a.out"), openmp=False)
        command = ['scc', '-my-flag', 'a.o', '-o', 'a.out']
        assert subproc_record.invocations() == [command]

    def test_argument_ordering(self, stub_c_compiler: CCompiler,
                               subproc_record: ExtendedRecorder,
                               monkeypatch) -> None:
        """
        Tests linker argument ordering.
        """
        monkeypatch.setenv('LDFLAGS', '-ldflag')

        stub_c_compiler.add_flags(["-compiler-flag1", "-compiler-flag2"])

        linker = Linker(compiler=stub_c_compiler)
        linker.add_flags(["-linker-flag1", "-linker-flag2"])
        linker.add_pre_lib_flags(["-prelibflag1", "-prelibflag2"])
        linker.add_lib_flags("customlib1", ["-lib1flag1", "lib1flag2"])
        linker.add_lib_flags("customlib2", ["-lib2flag1", "lib2flag2"])
        linker.add_post_lib_flags(["-postlibflag1", "-postlibflag2"])

        linker.link([
            Path("a.o")], Path("a.out"),
            libs=["customlib2", "customlib1"],
            openmp=True)

        command = ['scc', "-ldflag", "-linker-flag1", "-linker-flag2",
                   "-compiler-flag1", "-compiler-flag2",
                   "-omp", "a.o",
                   "-prelibflag1", "-prelibflag2",
                   "-lib2flag1", "lib2flag2",
                   "-lib1flag1", "lib1flag2",
                   "-postlibflag1", "-postlibflag2",
                   "-o", "a.out"]
        assert subproc_record.invocations() == [command]

    def test_library_order(self, stub_c_compiler: CCompiler,
                           subproc_record: ExtendedRecorder) -> None:
        """
        Tests linker library ordering.
        """
        linker1 = Linker(compiler=stub_c_compiler)
        linker1.add_pre_lib_flags(["pre_lib1"])
        linker1.add_lib_flags("lib_a", ["a_from_1"])
        linker1.add_lib_flags("lib_c", ["c_from_1"])
        linker1.add_post_lib_flags(["post_lib1"])

        linker2 = Linker(stub_c_compiler, linker=linker1)
        linker2.add_pre_lib_flags(["pre_lib2"])
        linker2.add_lib_flags("lib_b", ["b_from_2"])
        linker2.add_lib_flags("lib_c", ["c_from_2"])
        linker1.add_post_lib_flags(["post_lib2"])

        linker2.link(
            [Path("a.o")], Path("a.out"),
            libs=["lib_a", "lib_b", "lib_c"],
            openmp=True)

        command = ['scc', '-omp', "a.o", "pre_lib2", "pre_lib1", "a_from_1",
                   "b_from_2", "c_from_2", "post_lib1", "post_lib2", "-o", "a.out"]
        assert subproc_record.invocations() == [command]

    def test_inheritance(self, stub_c_compiler: CCompiler) -> None:
        """
        Tests link libraries are avialable from the wrapping linker.
        """
        linker = Linker(stub_c_compiler)
        wrapper = Linker(stub_c_compiler, linker=linker)

        linker.add_lib_flags("lib_a", ["a_from_1"])
        assert wrapper.get_lib_flags("lib_a") == ["a_from_1"]

        with raises(RuntimeError) as err:
            wrapper.get_lib_flags("does_not_exist")
        assert str(err.value).startswith("Unknown library name: 'does_not_exist'")
