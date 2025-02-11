##############################################################################
# (c) Crown copyright Met Office. All rights reserved.
# For further details please refer to the file COPYRIGHT
# which you should have received as part of this distribution
##############################################################################
"""
Tests compiler wrapping tools.
"""
from pathlib import Path
from typing import Optional

from pytest import mark, raises, warns
from pytest_subprocess.fake_process import FakeProcess

from fab.tools.category import Category
from fab.tools.compiler import (Compiler, CCompiler, FortranCompiler,
                                Gcc, Gfortran, Icc, Ifort)
from fab.tools.compiler_wrapper import (CompilerWrapper,
                                        CrayCcWrapper, CrayFtnWrapper,
                                        Mpicc, Mpif90)


def test_wrapping() -> None:
    """
    Tests wrapping functionality.
    """
    compiler = FortranCompiler('some fortran', Path('sfortran'), 'some',
                               r'([\d.]+)')
    wrapper = CompilerWrapper('some wrapper', 'wrapf', compiler)
    assert wrapper.compiler is compiler


def test_version_and_caching(fake_process: FakeProcess) -> None:
    """
    Tests compiler version pass-through and caching.
    """
    fake_process.register(['sfortran', '--version'], stdout='2.3.4')
    fake_process.register(['wrapf', '--version'], stdout='2.3.4')

    compiler = FortranCompiler('some fortran', Path('sfortran'), 'some',
                               r'([\d.]+)')
    wrapper = CompilerWrapper('some wrapper', 'wrapf', compiler)

    # The wrapper should report the version of the wrapped compiler:
    assert wrapper.get_version() == (2, 3, 4)

    # Test that the value is cached:
    assert wrapper.get_version() == (2, 3, 4)
    assert [call for call in fake_process.calls] == [
        ['sfortran', '--version'], ['wrapf', '--version']
    ]


def test_version_consistency(fake_process: FakeProcess) -> None:
    """
    Tests compiler and wrapper reporting different versions.
    """
    fake_process.register(['scc', '--version'], stdout='1.2.3')
    fake_process.register(['wrapc', '--version'], stdout='4.5.6')

    compiler = CCompiler('some c', 'scc', 'some', r'([\d.]+)')
    wrapper = CompilerWrapper('some wrapper', 'wrapc', compiler)

    with raises(RuntimeError) as err:
        wrapper.get_version()
    assert str(err.value).startswith(
        "Different version for compiler 'CCompiler - some c: scc' (1.2.3) "
        "and compiler wrapper 'CompilerWrapper(some c)' (4.5.6)"
    )
    assert [call for call in fake_process.calls] == [
        ['scc', '--version'], ['wrapc', '--version']
    ]


def test_version_compiler_unavailable(fake_process: FakeProcess) -> None:
    """
    Tests missing compiler behaviour.
    """
    fake_process.register(['scc', '--version'], returncode=1)
    fake_process.register(['wrapc', '--version'], stdout='1.2.3')

    compiler = CCompiler('some c', 'scc', 'some', r'([\d.]+)')
    wrapper = CompilerWrapper('some wrapper', 'wrapc', compiler)

    with raises(RuntimeError) as err:
        assert wrapper.get_version() == ""
    assert str(err.value).startswith("Cannot get version of wrapped compiler")

    assert [call for call in fake_process.calls] == [['scc', '--version']]


def test_is_available_ok(fake_process: FakeProcess) -> None:
    """
    Tests availability checking.
    """
    fake_process.register(['scc', '--version'], stdout='1.2.3')
    fake_process.register(['wrapc', '--version'], stdout='1.2.3')

    compiler = CCompiler('some c', 'scc', 'some', r'([\d.]+)')
    wrapper = CompilerWrapper('some wrapper', 'wrapc', compiler)

    # Make sure that the compiler-wrapper itself reports that it is available:
    # even if mpicc is not installed:
    assert wrapper.is_available
    assert wrapper.is_available
    # Due to caching there should only be one call to check_avail
    assert [call for call in fake_process.calls] == [
        ['scc', '--version'], ['wrapc', '--version']
    ]


def test_is_available_no_version(fake_process: FakeProcess) -> None:
    """
    Tests invalid version behaviour.
    """
    fake_process.register(['scc', '--version'], returncode=1)

    compiler = CCompiler('some c', 'scc', 'some', r'([\d.]+)')
    wrapper = CompilerWrapper('some wrapper', 'wrapc', compiler)

    assert not wrapper.is_available
    assert [call for call in fake_process.calls] == [['scc', '--version']]


def test_get_hash(fake_process: FakeProcess) -> None:
    """
    Tests hashing functionality.
    """
    fake_process.register(['wrapc', '--version'], stdout='5.6.7')
    fake_process.register(['scc', '--version'], stdout='5.6.7')
    fake_process.register(['wrapc', '--version'], stdout='8.9')
    fake_process.register(['scc', '--version'], stdout='8.9')
    fake_process.register(['wrapc', '--version'], stdout='5.6.7')
    fake_process.register(['scc', '--version'], stdout='5.6.7')
    fake_process.register(['wrapc', '--version'], stdout='8.9')
    fake_process.register(['scc', '--version'], stdout='8.9')

    compiler = CCompiler('some c', 'scc', 'some', r'([\d.]+)')
    wrapper = CompilerWrapper('some wrapper', 'wrapc', compiler)

    hash1 = wrapper.get_hash()
    assert hash1 == 4007703339

    # A change in the version number must change the hash:
    #
    compiler = CCompiler('some c', 'scc', 'some', r'([\d.]+)')
    wrapper = CompilerWrapper('some wrapper', 'wrapc', compiler)

    hash2 = wrapper.get_hash()
    assert hash2 != hash1

    # A change in the name with the original version number
    # 567) must change the hash again:
    #
    compiler = CCompiler('some other c', 'scc', 'some', r'([\d.]+)')
    wrapper = CompilerWrapper('some other wrapper', 'wrapc', compiler)

    hash3 = wrapper.get_hash()
    assert hash3 not in (hash1, hash2)

    # A change in the name with the modified version number
    # must change the hash again:
    #
    compiler = CCompiler('some other c', 'scc', 'some', r'([\d.]+)')
    wrapper = CompilerWrapper('some other wrapper', 'wrapc', compiler)

    hash4 = wrapper.get_hash()
    assert hash4 not in (hash1, hash2, hash3)

    assert [call for call in fake_process.calls] == [
        ['scc', '--version'], ['wrapc', '--version'],
        ['scc', '--version'], ['wrapc', '--version'],
        ['scc', '--version'], ['wrapc', '--version'],
        ['scc', '--version'], ['wrapc', '--version']
    ]


def test_syntax_only_fortran():
    """
    Tests handling of "syntax only" feature. This only applies to Fortran
    compilers.
    """
    compiler = FortranCompiler('some fortran', 'sfort', 'some', r'([\d.]+)',
                               syntax_only_flag='-sox')
    wrapper = CompilerWrapper('some wrapper', 'wrapf', compiler)
    assert wrapper.has_syntax_only


def test_syntax_only_c():
    """
    Tests handling of "syntax only" feature. This only applies to Fortran
    compilers.
    """
    compiler = CCompiler('some c', 'sc', 'some', r'([\d.]+)')
    wrapper = CompilerWrapper('some wrapper', 'wrapc', compiler)

    with raises(RuntimeError) as err:
        _ = wrapper.has_syntax_only
    assert str(err.value).startswith(
        "Compiler 'some c' has no has_syntax_only"
    )


def test_module_output_fortran():
    """
    Tests handling of module destination argument. This only applies to
    Fortran compilers.
    """
    compiler = FortranCompiler('some compiler', Path('compiler'), 'some',
                               r'([\d.]+)')
    wrapper = CompilerWrapper('some wrapper', Path('swrap'), compiler)

    wrapper.set_module_output_path("/somewhere")
    # ToDo: Inquiery of "private" member smells.
    assert wrapper.compiler._module_output_path == "/somewhere"


def test_module_output_c():
    """
    Tests handling of module destination argument. This only applies to
    Fortran compilers.
    """
    compiler = CCompiler('some compiler', Path('compiler'), 'some',
                         r'([\d.]+)')
    wrapper = CompilerWrapper('some wrapper', Path('swrap'), compiler)

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

    compiler = FortranCompiler('some fortran', Path('sfort'), 'some',
                               r'([\d.]+)', module_folder_flag='-J',
                               syntax_only_flag='-sox')
    wrapper = CompilerWrapper('some fortran wrapper', Path('wrapf'), compiler)
    wrapper.set_module_output_path("/module_out")
    with warns(UserWarning, match="Removing managed flag"):
        wrapper.compile_file(Path("a.f90"), "a.o",
                             add_flags=["-J/b", "-O3"], openmp=False,
                             syntax_only=True)
    # Notice that "-J/b" has been removed

    assert [call for call in fake_process.calls] == [command]


def test_fortran_with_add_args_openmp(fake_process: FakeProcess) -> None:
    """
    Tests Fortran compiler refuses Fortran compiler arguments and flags
    duplicate OpenMP argument.
    """
    command = ['wrapf', '-c', '-omp', '-omp', '-O3', '-sox',
               '-mod', '/module_out', 'a.f90', '-o', 'a.o']
    fake_process.register(command)
    compiler = FortranCompiler('some fortran', Path('sfort'), 'some',
                               r'([\d.]+)', openmp_flag='-omp',
                               syntax_only_flag='-sox', module_folder_flag='-mod')
    wrapper = CompilerWrapper('some fortran wrapper', Path('wrapf'), compiler)
    wrapper.set_module_output_path("/module_out")
    with warns(UserWarning,
               match="explicitly provided. OpenMP should be "
                     "enabled in the BuildConfiguration"):
        wrapper.compile_file(Path("a.f90"), "a.o",
                             add_flags=["-omp", "-O3"],
                             openmp=True, syntax_only=True)

    assert [call for call in fake_process.calls] == [command]


def test_c_with_add_args(fake_process: FakeProcess) -> None:
    """
    Tests C compiler refuses Fortran compiler arguments and flags duplicate
    OpenMP argument.
    """
    command = ['wrapc', '-c', '-O3', 'a.f90', '-o', 'a.o']
    omp_command = ['wrapc', '-c', '-omp', '-omp', '-O3', 'a.f90', '-o', 'a.o']
    fake_process.register(command)
    fake_process.register(omp_command)

    compiler = CCompiler('some c', Path('sc'), 'some', r'([\d.]+)',
                         openmp_flag='-omp')
    wrapper = CompilerWrapper('some c wrapper', Path('wrapc'), compiler)

    wrapper.compile_file(Path("a.f90"), "a.o", openmp=False,
                         add_flags=["-O3"])

    # Invoke C compiler with syntax-only flag (which is only supported
    # by Fortran compilers), which should raise an exception.
    with raises(RuntimeError) as err:
        wrapper.compile_file(Path("a.f90"), "a.o", openmp=False,
                             add_flags=["-O3"], syntax_only=True)
    assert str(err.value).startswith(
        "Syntax-only cannot be used with compiler 'some c wrapper'.")

    # Check that providing the openmp flag in add_flag raises a warning:
    with warns(UserWarning,
               match="explicitly provided. OpenMP should be "
                     "enabled in the BuildConfiguration"):
        wrapper.compile_file(Path("a.f90"), "a.o",
                             add_flags=["-omp", "-O3"],
                             openmp=True)

    assert [call for call in fake_process.calls] == [command, omp_command]


def test_flags_independent(fake_process: FakeProcess) -> None:
    """
    Tests that setting compiler flags affects wrapper but not vice-versa.
    """
    compiler = Compiler('some comp', Path('scomp'), 'some',
                        r'([\d.]+)', category=Category.C_COMPILER)
    wrapper = CompilerWrapper('some wrapper', Path('wrapper'), compiler)
    assert compiler.flags == []
    assert wrapper.flags == []

    # Setting flags in the compiler must become visible in the wrapper compiler:
    compiler.add_flags(["-a", "-b"])
    assert compiler.flags == ["-a", "-b"]
    assert wrapper.flags == ["-a", "-b"]
    assert wrapper.openmp_flag == compiler.openmp_flag

    # Adding flags to the wrapper should not affect the wrapped compiler:
    wrapper.add_flags(["-d", "-e"])
    assert compiler.flags == ["-a", "-b"]
    # And the compiler wrapper should reports the wrapped compiler's flag
    # followed by the wrapper flag (i.e. the wrapper flag can therefore
    # overwrite the wrapped compiler's flags)
    assert wrapper.flags == ["-a", "-b", "-d", "-e"]


@mark.parametrize('openmp_argument', [None, '-omp'])
def test_openmp_flags(openmp_argument: Optional[str]) -> None:
    """
    Tests openmp is correctly inherited from the wrapper compiler.
    """
    compiler = Compiler('some comp', Path('scomp'), 'some',
                        r'([\d.]+)', Category.C_COMPILER,
                        openmp_flag=openmp_argument)
    wrapper = CompilerWrapper('some wrapper', Path('swrap'), compiler)

    assert compiler.openmp is (openmp_argument is not None)
    assert compiler.openmp_flag == (openmp_argument or '')
    assert wrapper.openmp is (openmp_argument is not None)
    assert wrapper.openmp_flag == (openmp_argument or '')


def test_flags_with_add_arg(fake_process: FakeProcess) -> None:
    """
    Tests argument passthrough from compiler to wrapper with additional
    call-time arguments.
    """
    command = ['wrapper', '-a', '-b', '-c', '-d', '-e', '-f', 'a.f90',
               '-o', 'a.o']
    fake_process.register(command)

    compiler = Compiler('some compiler', Path('scomp'), 'some',
                        r'([\d.]+)', category=Category.C_COMPILER)
    compiler.add_flags(["-a", "-b"])
    wrapper = CompilerWrapper('some wrapper', Path('wrapper'), compiler)
    wrapper.add_flags(["-d", "-e"])

    # Check that the flags are assembled in the right order in the
    # actual compiler call: first the wrapper compiler flag, then
    # the wrapper flag, then additional flags
    wrapper.compile_file(Path("a.f90"), "a.o", add_flags=["-f"],
                         openmp=False)
    assert [call for call in fake_process.calls] == [command]


def test_flags_without_add_arg(fake_process: FakeProcess) -> None:
    """
    Tests argument passthrough from compiler to wrapper.
    """
    command = ['wrapper', '-a', '-b', '-c', '-d', '-e', 'a.f90', '-o', 'a.o']
    fake_process.register(command)

    compiler = Compiler('some compiler', 'scompile', 'some',
                        r'([\d.]+)', Category.C_COMPILER)
    compiler.add_flags(["-a", "-b"])
    wrapper = CompilerWrapper('some wrapper', 'wrapper', compiler)
    wrapper.add_flags(["-d", "-e"])
    # Check that the flags are assembled in the right order in the
    # actual compiler call: first the wrapper compiler flag, then
    # the wrapper flag, then additional flags
    # Test if no add_flags are specified:
    wrapper.compile_file(Path("a.f90"), "a.o", openmp=False)
    assert [call for call in fake_process.calls] == [command]


def test_mpi_gcc():
    '''Tests the MPI enables gcc class.'''
    mpi_gcc = Mpicc(Gcc())
    assert mpi_gcc.name == "mpicc-gcc"
    assert str(mpi_gcc) == "Mpicc(gcc)"
    assert isinstance(mpi_gcc, CompilerWrapper)
    assert mpi_gcc.category == Category.C_COMPILER
    assert mpi_gcc.mpi
    assert mpi_gcc.suite == "gnu"


def test_mpi_gfortran():
    '''Tests the MPI enabled gfortran class.'''
    mpi_gfortran = Mpif90(Gfortran())
    assert mpi_gfortran.name == "mpif90-gfortran"
    assert str(mpi_gfortran) == "Mpif90(gfortran)"
    assert isinstance(mpi_gfortran, CompilerWrapper)
    assert mpi_gfortran.category == Category.FORTRAN_COMPILER
    assert mpi_gfortran.mpi
    assert mpi_gfortran.suite == "gnu"


def test_mpi_icc():
    '''Tests the MPI enabled icc class.'''
    mpi_icc = Mpicc(Icc())
    assert mpi_icc.name == "mpicc-icc"
    assert str(mpi_icc) == "Mpicc(icc)"
    assert isinstance(mpi_icc, CompilerWrapper)
    assert mpi_icc.category == Category.C_COMPILER
    assert mpi_icc.mpi
    assert mpi_icc.suite == "intel-classic"


def test_mpi_ifort():
    '''Tests the MPI enabled ifort class.'''
    mpi_ifort = Mpif90(Ifort())
    assert mpi_ifort.name == "mpif90-ifort"
    assert str(mpi_ifort) == "Mpif90(ifort)"
    assert isinstance(mpi_ifort, CompilerWrapper)
    assert mpi_ifort.category == Category.FORTRAN_COMPILER
    assert mpi_ifort.mpi
    assert mpi_ifort.suite == "intel-classic"


def test_cray_icc():
    '''Tests the Cray wrapper for icc.'''
    craycc = CrayCcWrapper(Icc())
    assert craycc.name == "craycc-icc"
    assert str(craycc) == "CrayCcWrapper(icc)"
    assert isinstance(craycc, CompilerWrapper)
    assert craycc.category == Category.C_COMPILER
    assert craycc.mpi
    assert craycc.suite == "intel-classic"


def test_cray_ifort():
    '''Tests the Cray wrapper for ifort.'''
    crayftn = CrayFtnWrapper(Ifort())
    assert crayftn.name == "crayftn-ifort"
    assert str(crayftn) == "CrayFtnWrapper(ifort)"
    assert isinstance(crayftn, CompilerWrapper)
    assert crayftn.category == Category.FORTRAN_COMPILER
    assert crayftn.mpi
    assert crayftn.suite == "intel-classic"


def test_cray_gcc():
    '''Tests the Cray wrapper for gcc.'''
    craycc = CrayCcWrapper(Gcc())
    assert craycc.name == "craycc-gcc"
    assert str(craycc) == "CrayCcWrapper(gcc)"
    assert isinstance(craycc, CompilerWrapper)
    assert craycc.category == Category.C_COMPILER
    assert craycc.mpi
    assert craycc.suite == "gnu"


def test_cray_gfortran_wrapper():
    """
    Tests Cray wrapping of GFortran.
    """
    crayftn = CrayFtnWrapper(Gfortran())
    assert crayftn.name == "crayftn-gfortran"
    assert str(crayftn) == "CrayFtnWrapper(gfortran)"
    assert isinstance(crayftn, CompilerWrapper)
    assert crayftn.category == Category.FORTRAN_COMPILER
    assert crayftn.mpi
    assert crayftn.suite == "gnu"
