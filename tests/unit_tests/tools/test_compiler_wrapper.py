##############################################################################
# (c) Crown copyright Met Office. All rights reserved.
# For further details please refer to the file COPYRIGHT
# which you should have received as part of this distribution
##############################################################################
"""
Validates wrapped compile functionality. e.g. MPI.
"""
from pathlib import Path

from pytest import raises, warns
from pytest_subprocess.fake_process import FakeProcess

from tests.conftest import ExtendedRecorder, call_list, not_found_callback

from fab.tools.category import Category
from fab.tools.compiler import (CCompiler, FortranCompiler,
                                Gcc, Gfortran, Icc, Ifort)
from fab.tools.compiler_wrapper import (CompilerWrapper, CrayCcWrapper,
                                        CrayFtnWrapper, Mpicc, Mpif90)


def test_compiler_wrapper_compiler_getter():
    '''Tests that the compiler wrapper getter returns the
    wrapper compiler instance.
    '''
    gcc = Gcc()
    mpicc = Mpicc(gcc)
    assert mpicc.compiler is gcc


def test_version_and_caching(stub_c_compiler: CCompiler,
                             fake_process: FakeProcess) -> None:
    """
    Tests the compiler wrapper reports the right version number from the
    actual compiler.
    """
    compiler_version = ['scc', '--version']
    fake_process.register(compiler_version, stdout='1.2.3')
    wrapper_version = ['mpicc', '--version']
    fake_process.register(wrapper_version, stdout='1.2.3')

    mpicc = Mpicc(stub_c_compiler)

    assert mpicc.get_version() == (1, 2, 3)

    # Test that the value is cached:
    assert mpicc.get_version() == (1, 2, 3)

    assert fake_process.call_count(compiler_version) == 1
    assert fake_process.call_count(wrapper_version) == 1


def test_version_consistency(stub_c_compiler: CCompiler,
                             fake_process: FakeProcess) -> None:
    """
    Tests that the compiler wrapper and compiler must report the
    same version number:
    """
    compiler_version = ['scc', '--version']
    fake_process.register(compiler_version, stdout='1.2.3')
    wrapper_version = ['mpicc', '--version']
    fake_process.register(wrapper_version, stdout='4.5.6')

    mpicc = Mpicc(stub_c_compiler)
    with raises(RuntimeError) as err:
        mpicc.get_version()
    assert str(err.value) \
        == "Different version for compiler " \
           "'CCompiler - some C compiler: scc' (1.2.3) " \
           "and compiler wrapper 'Mpicc(some C compiler)' (4.5.6)."


def test_version_compiler_unavailable(fake_process: FakeProcess) -> None:
    """
    Tests missing wrapped compiler.
    The wrapper should report an empty result.
    """
    compiler_version = ['scc', '--version']
    fake_process.register(compiler_version, callback=not_found_callback)

    compiler = CCompiler("Some C compiler", 'scc', 'some', r'([\d.]+)')
    mpicc = Mpicc(compiler)

    with raises(RuntimeError) as err:
        mpicc.get_version()
    assert str(err.value).startswith("Cannot get version of wrapped compiler")
    assert fake_process.call_count(compiler_version) == 1


def test_compiler_is_available_ok(stub_c_compiler: CCompiler,
                                  fake_process: FakeProcess) -> None:
    """
    Tests availability check in success conditions.

    ToDo: Messing with "private" state.
    """
    compiler_command = ['scc', '--version']
    fake_process.register(compiler_command, stdout='1.2.3')
    wrapper_command = ['mpicc', '--version']
    fake_process.register(wrapper_command, stdout='1.2.3')
    mpicc = Mpicc(stub_c_compiler)

    # Just make sure we get the right object:
    assert isinstance(mpicc, CompilerWrapper)
    assert mpicc.is_available

    # Test that the value is indeed cached:
    assert mpicc._is_available
    # Due to caching there should only be one call to check_avail
    assert fake_process.call_count(compiler_command) == 1
    assert fake_process.call_count(wrapper_command) == 1


def test_compiler_is_available_no_version(fake_process: FakeProcess) -> None:
    """
    Tests invalid version makes compielr unavailable.
    """
    fake_process.register(['scc', '--version'], stdout='bad version number')
    mpicc = Mpicc(CCompiler("Some C compiler", 'scc', 'some', r'([\d.]+)'))
    assert not mpicc.is_available


def test_compiler_hash(fake_process: FakeProcess) -> None:
    """
    Test the hash functionality.
    """
    fake_process.register(['scc', '--version'], stdout='567.0')
    mpicc1 = CCompiler("Some C compiler", 'scc', 'some', r'([\d.]+)')

    hash1 = mpicc1.get_hash()
    assert hash1 == 5574914495

    # A change in the version number must change the hash:
    fake_process.register(['scc', '--version'], stdout='89.0')
    mpicc2 = CCompiler("Some C compiler", 'scc', 'some', r'([\d.]+)')
    hash2 = mpicc2.get_hash()
    assert hash2 != hash1

    # A change in the name with the original version number
    # 567) must change the hash again:
    fake_process.register(['scc', '--version'], stdout='567.0')
    mpicc3 = CCompiler("Some other C compiler", 'scc', 'some', r'([\d.]+)')
    hash3 = mpicc3.get_hash()
    assert hash3 not in (hash1, hash2)

    # A change in the name with the modified version number
    # must change the hash again:
    fake_process.register(['scc', '--version'], stdout='89.0')
    mpicc4 = CCompiler("Some other C compiler", 'scc', 'some', r'([\d.]+)')
    hash4 = mpicc4.get_hash()
    assert hash4 not in (hash1, hash2, hash3)


def test_fortran_syntax_only() -> None:
    """
    Tests handling of syntax only flags in wrapper.
    """
    compiler = FortranCompiler('Some Fortran compiler', 'sfc', 'some', r'([\d.]+)',
                               syntax_only_flag='-sax')
    mpif90 = Mpif90(compiler)
    assert mpif90.has_syntax_only


def test_c_syntax_only(stub_c_compiler: CCompiler) -> None:
    """
    Tests attempt to use "syntax only" on C compiler is rejected.
    """
    mpicc = Mpicc(stub_c_compiler)
    with raises(RuntimeError) as err:
        _ = mpicc.has_syntax_only
    assert str(err.value) == "Compiler 'some C compiler' has no has_syntax_only."


def test_fortran_module_output(stub_fortran_compiler: FortranCompiler) -> None:
    """
    Tests handling of module output_flags in a wrapper.
    """
    mpif90 = Mpif90(stub_fortran_compiler)
    mpif90.set_module_output_path(Path("/somewhere"))
    assert mpif90.compiler._module_output_path == "/somewhere"  # type: ignore[attr-defined]


def test_c_module_output(stub_c_compiler: CCompiler) -> None:
    """
    Tests Wrapped C compiler rejects Fortran module arguments.
    """
    mpicc = Mpicc(stub_c_compiler)
    with raises(RuntimeError) as err:
        mpicc.set_module_output_path(Path("/tmp"))
    assert str(err.value) == "Compiler 'some C compiler' " \
                             "has no 'set_module_output_path' function."


def test_module_output_c():
    """
    Tests handling of module destination argument. This only applies to
    Fortran compilers.
    """
    compiler = CCompiler('some compiler', Path('compiler'), 'some',
                         r'([\d.]+)')
    wrapper = CompilerWrapper('some wrapper', 'swrap', compiler)

    with raises(RuntimeError) as err:
        wrapper.set_module_output_path("/tmp")
    assert str(err.value).startswith(
        "Compiler 'some compiler' has no 'set_module_output_path' function"
    )


def test_fortran_with_add_args(fake_process: FakeProcess) -> None:
    """
    Tests management of Fortran compiler arguments by wrapper.
    """
    command = ['wrapf', '-c', "-O3", '-sox', '-J', '/module_out',
               'a.f90', '-o', 'a.o']
    fake_process.register(command)

    compiler = FortranCompiler('some fortran', 'sfort', 'some',
                               r'([\d.]+)', module_folder_flag='-J',
                               syntax_only_flag='-sox')
    wrapper = CompilerWrapper('some fortran wrapper', 'wrapf', compiler)
    wrapper.set_module_output_path(Path("/module_out"))
    with warns(UserWarning, match="Removing managed flag"):
        wrapper.compile_file(Path("a.f90"), Path("a.o"),
                             add_flags=["-J/b", "-O3"], openmp=False,
                             syntax_only=True)
    # Notice that "-J/b" has been removed


def test_fortran_with_add_args_openmp(fake_process: FakeProcess) -> None:
    """
    Tests Fortran compiler refuses Fortran compiler arguments and flags
    duplicate OpenMP argument.
    """
    command = ['wrapf', '-c', '-omp', '-omp', '-O3', '-sox',
               '-mod', '/module_out', 'a.f90', '-o', 'a.o']
    fake_process.register(command)
    compiler = FortranCompiler('some fortran', 'sfort', 'some',
                               r'([\d.]+)', openmp_flag='-omp',
                               syntax_only_flag='-sox', module_folder_flag='-mod')
    wrapper = CompilerWrapper('some fortran wrapper', 'wrapf', compiler)
    wrapper.set_module_output_path(Path("/module_out"))
    with warns(UserWarning,
               match="explicitly provided. OpenMP should be "
                     "enabled in the BuildConfiguration"):
        wrapper.compile_file(Path("a.f90"), Path("a.o"),
                             add_flags=["-omp", "-O3"],
                             openmp=True, syntax_only=True)

    assert call_list(fake_process) == [command]


def test_c_with_add_args(subproc_record: ExtendedRecorder) -> None:
    """
    Tests additional arguments are handled as expected by a compiler wrapper.
    Also verify that requesting Fortran-specific options like syntax-only with
    the C compiler raises a runtime error.
    """
    compiler = CCompiler('some c', 'sc', 'some', r'([\d.]+)',
                         openmp_flag='-omp')
    wrapper = CompilerWrapper('some c wrapper', 'wrapc', compiler)

    wrapper.compile_file(Path("a.f90"), Path("a.o"), openmp=False,
                         add_flags=["-O3"])

    # Invoke C compiler with syntax-only flag (which is only supported
    # by Fortran compilers), which should raise an exception.
    with raises(RuntimeError) as err:
        wrapper.compile_file(Path("a.f90"), Path("a.o"), openmp=False,
                             add_flags=["-O3"], syntax_only=True)
    assert str(err.value).startswith(
        "Syntax-only cannot be used with compiler 'some c wrapper'.")

    # Check that providing the openmp flag in add_flag raises a warning:
    with warns(UserWarning,
               match="explicitly provided. OpenMP should be "
                     "enabled in the BuildConfiguration"):
        wrapper.compile_file(Path("a.f90"), Path("a.o"),
                             add_flags=["-omp", "-O3"],
                             openmp=True)


def test_arguments_independent(fake_process: FakeProcess) -> None:
    """
    Tests arguments set in the base compiler and the wrapper are independent
    of each other.
    """
    compiler = CCompiler('Some C compiler', 'scc', 'some', r'([\d.]+)',
                         openmp_flag='-omp')
    mpicc = Mpicc(compiler)
    assert compiler.flags == []
    assert mpicc.flags == []
    compiler.add_flags(["-a", "-b"])
    assert compiler.flags == ["-a", "-b"]
    assert mpicc.flags == []
    assert mpicc.openmp_flag == compiler.openmp_flag

    # Test  a compiler wrapper correctly queries the wrapper compiler for
    # openmp flag: Set the wrapper to have no _openmp_flag (which is
    # actually the default, since the wrapper never sets its own flag), but
    # gcc does have a flag, so mpicc should report that is supports openmp.
    # mpicc.openmp calls openmp of its base class (Compiler), which queries
    # if an openmp flag is defined. This query must go to the openmp property,
    # since the wrapper overwrites this property to return the wrapped
    # compiler's flag (and not the wrapper's flag, which would not be defined)
    #
    # ToDo: Monkeying with "private" state.
    #
    mpicc._openmp_flag = ""
    assert mpicc._openmp_flag == ""
    assert mpicc.openmp

    # Adding flags to the wrapper should not affect the wrapped compiler:
    mpicc.add_flags(["-d", "-e"])
    assert compiler.flags == ["-a", "-b"]
    # And the compiler wrapper should reports the wrapped compiler's flag
    # followed by the wrapper flag (i.e. the wrapper flag can therefore
    # overwrite the wrapped compiler's flags)
    assert mpicc.flags == ["-d", "-e"]


def test_c_args_with_add_arg(stub_c_compiler: CCompiler,
                             fake_process: FakeProcess,
                             monkeypatch) -> None:
    """
    Tests arguments set against the base compiler manifest in the wrapper
    even when additional arguments are specified.
    """
    command = ['mpicc', '-a', '-b', '-c', '-d', '-e', '-f',
               'a.f90', '-o', 'a.o']
    fake_process.register(command)

    monkeypatch.delenv('CFLAGS', raising=False)
    mpicc = Mpicc(stub_c_compiler)
    stub_c_compiler.add_flags(["-a", "-b"])
    mpicc.add_flags(["-d", "-e"])

    # Check that the flags are assembled in the right order in the
    # actual compiler call: first the wrapper compiler flag, then
    # the wrapper flag, then additional flags
    mpicc.compile_file(Path("a.f90"), Path("a.o"), add_flags=["-f"],
                       openmp=False)
    assert call_list(fake_process) == [command]


def test_arguments_without_add_arg(stub_c_compiler: CCompiler,
                                   fake_process: FakeProcess,
                                   monkeypatch) -> None:
    """
    Tests arguments set against the base compiler will be set for the wrapper
    when no additional flags are specified.
    """
    command = ['mpicc', '-a', '-b', '-c', '-d', '-e', 'a.f90', '-o', 'a.o']
    fake_process.register(command)

    monkeypatch.delenv('CFLAGS', raising=False)
    mpicc = Mpicc(stub_c_compiler)
    stub_c_compiler.add_flags(["-a", "-b"])
    mpicc.add_flags(["-d", "-e"])
    # Check that the flags are assembled in the right order in the
    # actual compiler call: first the wrapper compiler flag, then
    # the wrapper flag, then additional flags
    # Test if no add_flags are specified:
    mpicc.compile_file(Path("a.f90"), Path("a.o"), openmp=False)
    assert call_list(fake_process) == [command]


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
    '''Tests the MPI enabled ifort class.'''
    mpi_ifort = Mpif90(Ifort())
    assert mpi_ifort.name == "mpif90-ifort"
    assert str(mpi_ifort) == "Mpif90(ifort)"
    assert isinstance(mpi_ifort, CompilerWrapper)
    assert mpi_ifort.category == Category.FORTRAN_COMPILER
    assert mpi_ifort.mpi
    assert mpi_ifort.suite == "intel-classic"


def test_compiler_wrapper_cray_icc():
    '''Tests the Cray wrapper for icc.'''
    craycc = CrayCcWrapper(Icc())
    assert craycc.name == "craycc-icc"
    assert str(craycc) == "CrayCcWrapper(icc)"
    assert isinstance(craycc, CompilerWrapper)
    assert craycc.category == Category.C_COMPILER
    assert craycc.mpi
    assert craycc.suite == "intel-classic"


def test_compiler_wrapper_cray_ifort():
    '''Tests the Cray wrapper for ifort.'''
    crayftn = CrayFtnWrapper(Ifort())
    assert crayftn.name == "crayftn-ifort"
    assert str(crayftn) == "CrayFtnWrapper(ifort)"
    assert isinstance(crayftn, CompilerWrapper)
    assert crayftn.category == Category.FORTRAN_COMPILER
    assert crayftn.mpi
    assert crayftn.suite == "intel-classic"


def test_compiler_wrapper_cray_gcc():
    '''Tests the Cray wrapper for gcc.'''
    craycc = CrayCcWrapper(Gcc())
    assert craycc.name == "craycc-gcc"
    assert str(craycc) == "CrayCcWrapper(gcc)"
    assert isinstance(craycc, CompilerWrapper)
    assert craycc.category == Category.C_COMPILER
    assert craycc.mpi
    assert craycc.suite == "gnu"


def test_compiler_wrapper_cray_gfortran():
    '''Tests the Cray wrapper for gfortran.'''
    crayftn = CrayFtnWrapper(Gfortran())
    assert crayftn.name == "crayftn-gfortran"
    assert str(crayftn) == "CrayFtnWrapper(gfortran)"
    assert isinstance(crayftn, CompilerWrapper)
    assert crayftn.category == Category.FORTRAN_COMPILER
    assert crayftn.mpi
    assert crayftn.suite == "gnu"
