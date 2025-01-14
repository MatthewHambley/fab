##############################################################################
# (c) Crown copyright Met Office. All rights reserved.
# For further details please refer to the file COPYRIGHT
# which you should have received as part of this distribution
##############################################################################

'''Tests the compiler wrapper implementation.
'''
from collections import deque
from pathlib import Path
from typing import Tuple

from pytest import raises, warns
from pytest_subprocess.fake_process import FakeProcess, ProcessRecorder

from fab.category import Category
from fab.tools.compiler import CCompiler, Gcc, Gfortran, Icc, Ifort
from fab.tools.compiler_wrapper import CompilerWrapper, Mpicc, Mpif90


def test_compiler_wrapper_compiler_getter():
    '''Tests that the compiler wrapper getter returns the
    wrapper compiler instance.
    '''
    gcc = Gcc()
    mpicc = Mpicc(gcc)
    assert mpicc.compiler is gcc


def test_compiler_wrapper_version_and_caching(fake_process: FakeProcess):
    '''Tests that the compiler wrapper reports the right version number
    from the actual compiler.
    '''
    fake_process.register(['gcc', '--version'], stdout="gcc (foo) 1.2.3")
    fake_process.register(['mpicc', '--version'], stdout="gcc (bar) 1.2.3")
    mpicc = Mpicc(Gcc())
    # The wrapper should report the version of the wrapped compiler:
    assert mpicc.get_version() == (1, 2, 3)
    assert mpicc.get_version() == (1, 2, 3)
    # Test that the value is cached:
    assert fake_process.calls == deque(
        [
            ['gcc', '--version'],
            ['mpicc', '--version']
        ]
    )


def test_compiler_wrapper_version_consistency(fake_process: FakeProcess):
    '''Tests that the compiler wrapper and compiler must report the
    same version number:
    '''

    # The wrapper must verify that the wrapper compiler and wrapper
    # report the same version number, otherwise raise an exception.
    # The first patch changes the return value which the compiler wrapper
    # will report (since it calls Compiler.get_version), the second
    # changes the return value of the wrapper compiler instance only:

    mpicc = Mpicc(Gcc())
    fake_process.register(['gcc', '--version'],
                          stdout="gcc (GCC) 8.6.0 20210514 (Red Hat 8.5.0-20)")
    fake_process.register(['mpicc', '--version'],
                          stdout="gcc (GCC) 8.5.0 20210514 (Red Hat 8.5.0-20)")
    with raises(RuntimeError) as err:
        mpicc.get_version()
    assert str(err.value) \
           == "Different version for compiler 'Gcc - gcc: gcc' (8.6.0) " \
              "and compiler wrapper 'Mpicc(gcc)' (8.5.0)."


def test_compiler_wrapper_version_compiler_unavailable(stub_c_compiler,
                                                       fake_process: FakeProcess):
    '''Checks the behaviour if the wrapped compiler is not available.
    The wrapper should then report an empty result.
    '''
    mpicc = Mpicc(stub_c_compiler)
    fake_process.register(['stubc', '--version'], returncode=2)
    with raises(RuntimeError) as err:
        assert mpicc.get_version() == ""
    assert str(err.value) == "Cannot get version of wrapped compiler 'StubC - stub_c_compiler: stubc'"


def test_compiler_is_available_ok(stub_c_compiler,
                                  fake_process: FakeProcess):
    """
    Tests that check_available works as expected.
    """
    fake_process.register(['stubc', '--version'], stdout="1.2.3")
    fake_process.register(['mpicc', '--version'], stdout="1.2.3")
    mpicc = Mpicc(stub_c_compiler)
    assert mpicc.is_available is True
    assert mpicc.is_available is True
    # Due to caching there should only be one invocation of the executable.


def test_compiler_is_available_no_version(fake_process):
    '''Make sure a compiler that does not return a valid version
    is marked as not available.
    '''
    mpicc = Mpicc(Gcc())
    fake_process.register(['gcc', '--version'], stdout='argle.bargle')
    # Now test if get_version raises an error
    assert mpicc.is_available is False


class HashStubC(CCompiler):
    def __init__(self, name: str, version: Tuple[int, ...]):
        super().__init__(name, 'vc', 'foo')
        self.__version = version

    def get_version(self) -> Tuple[int, ...]:
        return self.__version


def test_compiler_hash(monkeypatch):
    '''Test the hash functionality.'''
    def mpi_version():
        return (567,)

    mpicc = Mpicc(HashStubC('cheese', 123))
    monkeypatch.setattr(mpicc, 'get_version', mpi_version)
    hash1 = mpicc.get_hash()
    assert hash1 == 7572106968

    # The same result across instances
    mpicc2 = Mpicc(HashStubC('cheese', 123))
    monkeypatch.setattr(mpicc2, 'get_version', mpi_version)
    hash1_5 = mpicc2.get_hash()
    assert hash1_5 == hash1

    # A change in the version number must change the hash:
    def mpi_version2():
        return (89,)

    monkeypatch.setattr(mpicc, 'get_version', mpi_version2)
    hash2 = mpicc.get_hash()
    assert hash2 != hash1

    # A change in the name with the original version number
    # 567) must change the hash again:
    mpicc3 = Mpicc(HashStubC('beef', 123))
    monkeypatch.setattr(mpicc3, 'get_version', mpi_version)
    hash3 = mpicc3.get_hash()
    assert hash3 not in (hash1, hash2)

    # A change in the name with the modified version number
    # must change the hash again:
    monkeypatch.setattr(mpicc3, 'get_version', mpi_version2)
    hash4 = mpicc3.get_hash()
    assert hash4 not in (hash1, hash2, hash3)


def test_fortran_wrapper_syntax_only():
    """
    Tests "syntax only" behaviour of Fortran wrapper.
    """
    mpif90 = Mpif90(Gfortran())
    assert mpif90.has_syntax_only


def test_c_wrapper_syntax_only():
    """
    Tests that C wrapper rejects "syntax only" mode.
    """
    mpicc = Mpicc(Gcc())
    with raises(RuntimeError) as err:
        _ = mpicc.has_syntax_only
    assert str(err.value) == "Compiler 'gcc' has no has_syntax_only."


def test_forter_wrapper_module_output(mock_process):
    """
    Tests setting and getting module output control.
    """
    mpif90 = Mpif90(Gfortran())
    mpif90.set_module_output_path("/somewhere")
    assert mpif90.compiler._module_output_path == "/somewhere"


def test_c_wrapper_module_output(mock_process: ProcessRecorder):
    """
    Tests that setting module output control is rejected.
    """
    mpicc = Mpicc(Gcc())
    with raises(RuntimeError) as err:
        mpicc.set_module_output_path(Path("/tmp"))
    assert str(err.value) == "Compiler 'gcc' has no 'set_module_output_path' function."


def test_compiler_wrapper_fortran_with_add_args(mock_process: ProcessRecorder):
    '''Tests that additional arguments are handled as expected in
    a wrapper.'''
    mpif90 = Mpif90(Gfortran())
    mpif90.set_module_output_path(Path("/module_out"))
    with warns(UserWarning, match="Removing managed flag"):
        mpif90.compile_file(Path("a.f90"), Path("a.o"),
                            add_flags=["-J/b", "-O3"], openmp=False,
                            syntax_only=True)
        # Notice that "-J/b" has been removed
        assert [call.args for call in mock_process.calls] \
            == [['mpif90', '-c', "-O3", '-fsyntax-only', '-J', '/module_out',
                 'a.f90', '-o', 'a.o']]


def test_compiler_wrapper_fortran_with_add_args_unnecessary_openmp(mock_process: ProcessRecorder):
    '''Tests that additional arguments are handled as expected in
    a wrapper if also the openmp flags are specified.'''
    mpif90 = Mpif90(Gfortran())
    mpif90.set_module_output_path(Path("/module_out"))
    with warns(UserWarning,
               match="explicitly provided. "
                     "OpenMP should be enabled in the BuildConfiguration"):
        mpif90.compile_file(Path("a.f90"), Path("a.o"),
                            add_flags=["-fopenmp", "-O3"],
                            openmp=True, syntax_only=True)
    assert [call.args for call in mock_process.calls] \
        == [['mpif90', '-c', '-fopenmp', '-fopenmp', '-O3',
             '-fsyntax-only', '-J', '/module_out',
             'a.f90', '-o', 'a.o']]


def test_compiler_wrapper_c_with_add_args(mock_process: ProcessRecorder):
    """
    Tests argument handling of wrapped C compiler.
    """
    mpicc = Mpicc(Gcc())
    mpicc.compile_file(Path("a.f90"), Path("a.o"), openmp=False,
                       add_flags=["-O3"])
    assert [call.args for call in mock_process.calls] \
        == [['mpicc', '-c', "-O3", 'a.f90', '-o', 'a.o']]


def test_wrapped_c_rejects_fortran(mock_process):
    """
    Tests that a wrapped C compiler rejects Fortran only optons.

    In this case "syntax_only".
    """
    mpicc = Mpicc(Gcc())
    with raises(RuntimeError) as err:
        mpicc.compile_file(Path("a.f90"), Path("a.o"), openmp=False,
                           add_flags=["-O3"], syntax_only=True)
    assert str(err.value) == "Syntax-only cannot be used with compiler 'mpicc-gcc'."


def test_wrapped_c_warns_openmp(mock_process: ProcessRecorder):
    """
    Tests that providing an OpenMP argument raises a warning.
    """
    mpicc = Mpicc(Gcc())
    with warns(UserWarning,
               match="explicitly provided. "
                     "OpenMP should be enabled in the BuildConfiguration"):
        mpicc.compile_file(Path("a.f90"), Path("a.o"),
                           add_flags=["-fopenmp", "-O3"],
                           openmp=True)
    assert [call.args for call in mock_process.calls] \
        == [['mpicc', '-c', '-fopenmp', '-fopenmp', '-O3', 'a.f90', '-o', 'a.o']]


def test_compiler_wrapper_flags_independent():
    """
    Tests that flags set in the base compiler will be accessed in the
    wrapper, but not the other way round.
    """
    gcc = Gcc()
    mpicc = Mpicc(gcc)
    assert gcc.flags == []
    assert mpicc.flags == []
    # Setting flags in gcc must become visible in the wrapper compiler:
    gcc.add_flags(["-a", "-b"])
    assert gcc.flags == ["-a", "-b"]
    assert mpicc.flags == ["-a", "-b"]
    assert mpicc.openmp_flag == gcc.openmp_flag

    # Adding flags to the wrapper should not affect the wrapped compiler:
    mpicc.add_flags(["-d", "-e"])
    assert gcc.flags == ["-a", "-b"]
    # And the compiler wrapper should reports the wrapped compiler's flag
    # followed by the wrapper flag (i.e. the wrapper flag can therefore
    # overwrite the wrapped compiler's flags)
    assert mpicc.flags == ["-a", "-b", "-d", "-e"]


def test_compiler_wrapper_flags_with_add_arg(mock_process: ProcessRecorder):
    """
    Tests the handling of compiler arguments.

    They must be presented in the correct order, wrapper first, then compiler,
    finally additions.
    """
    gcc = Gcc()
    mpicc = Mpicc(gcc)
    gcc.add_flags(["-a", "-b"])
    mpicc.add_flags(["-d", "-e"])
    mpicc.compile_file(Path("a.f90"), Path("a.o"), add_flags=["-f"],
                       openmp=True)
    assert [call.args for call in mock_process.calls] \
        == [['mpicc', '-a', '-b', '-c', '-fopenmp',
             '-a', '-b', '-d', '-e', '-f', 'a.f90', '-o', 'a.o']]


def test_compiler_wrapper_flags_without_add_arg(mock_process: ProcessRecorder):
    """
    Tests the handling of compiler arguments.

    They must be presented in the correct order, wrapper first, then compiler.
    """
    gcc = Gcc()
    mpicc = Mpicc(gcc)
    gcc.add_flags(["-a", "-b"])
    mpicc.add_flags(["-d", "-e"])
    mpicc.compile_file(Path("a.f90"), Path("a.o"), openmp=True)
    assert [call.args for call in mock_process.calls] \
        == [['mpicc', "-a", "-b", '-c', '-fopenmp',
             '-a', '-b', '-d', '-e', 'a.f90', '-o', 'a.o']]
    assert mock_process.calls[0].kwargs is not None
    assert mock_process.calls[0].kwargs['cwd'] == '.'


def test_compiler_wrapper_mpi_gcc():
    '''Tests the MPI enables gcc class.'''
    mpi_gcc = Mpicc(Gcc())
    assert mpi_gcc.name == "mpicc-gcc"
    assert str(mpi_gcc) == "Mpicc(gcc)"
    assert isinstance(mpi_gcc, CompilerWrapper)
    assert mpi_gcc.category == Category.C_COMPILER
    assert mpi_gcc.mpi
    assert mpi_gcc.suite == "gnu"


def test_compiler_wrapper_mpi_gfortran():
    '''Tests the MPI enabled gfortran class.'''
    mpi_gfortran = Mpif90(Gfortran())
    assert mpi_gfortran.name == "mpif90-gfortran"
    assert str(mpi_gfortran) == "Mpif90(gfortran)"
    assert isinstance(mpi_gfortran, CompilerWrapper)
    assert mpi_gfortran.category == Category.FORTRAN_COMPILER
    assert mpi_gfortran.mpi
    assert mpi_gfortran.suite == "gnu"


def test_compiler_wrapper_mpi_icc():
    '''Tests the MPI enabled icc class.'''
    mpi_icc = Mpicc(Icc())
    assert mpi_icc.name == "mpicc-icc"
    assert str(mpi_icc) == "Mpicc(icc)"
    assert isinstance(mpi_icc, CompilerWrapper)
    assert mpi_icc.category == Category.C_COMPILER
    assert mpi_icc.mpi
    assert mpi_icc.suite == "intel-classic"


def test_compiler_wrapper_mpi_ifort():
    """
    Tests MPI wrapped IFort constructor.
    """
    mpi_ifort = Mpif90(Ifort())
    assert mpi_ifort.name == "mpif90-ifort"
    assert str(mpi_ifort) == "Mpif90(ifort)"
    assert isinstance(mpi_ifort, CompilerWrapper)
    assert mpi_ifort.category == Category.FORTRAN_COMPILER
    assert mpi_ifort.mpi
    assert mpi_ifort.suite == "intel-classic"
