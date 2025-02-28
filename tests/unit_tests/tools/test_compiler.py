##############################################################################
# (c) Crown copyright Met Office. All rights reserved.
# For further details please refer to the file COPYRIGHT
# which you should have received as part of this distribution
##############################################################################
"""
Tests Compiler tools.
"""
from logging import Logger
from pathlib import Path
from textwrap import dedent
from typing import Dict, Optional, Tuple

from pytest import mark, raises, warns
from pytest_subprocess.fake_process import FakeProcess

from tests.conftest import call_list
from fab.tools.category import Category
from fab.tools.compiler import (Compiler, CompilerSuiteTool,
                                CCompiler, FortranCompiler,
                                Craycc, Crayftn,
                                Gcc, Gfortran,
                                Icc, Ifort,
                                Icx, Ifx,
                                Nvc, Nvfortran)


class TestCompiler:
    """
    Tests base compiler tool.
    """

    def test_hash(self, fake_process: FakeProcess) -> None:
        """
        Tests hashing.
        """
        fake_process.register(['testc', '--version'], stdout='5.6.7')
        fake_process.register(['testc', '--version'], stdout="8.9")
        fake_process.register(['testc', '--version'], stdout="5.6.7")

        cc_one = Compiler('test compiler', Path('testc'), 'test',
                          version_regex=r'([\d.]+)',
                          category=Category.FORTRAN_COMPILER)
        first_hash = cc_one.get_hash()
        assert first_hash == 2356013058

        # Version numbers are cached so must create new object
        #
        cc_two = Compiler('test compiler', Path('testc'), 'test',
                          version_regex=r'([\d.]+)',
                          category=Category.FORTRAN_COMPILER)
        second_hash = cc_two.get_hash()
        assert second_hash != first_hash

        # A change in the name must change the hash, again:
        #
        cc_three = Compiler('new compiler', Path('testc'), 'test',
                            version_regex=r'([\d.]+)',
                            category=Category.FORTRAN_COMPILER)
        third_hash = cc_three.get_hash()
        assert third_hash not in (first_hash, second_hash)

        assert call_list(fake_process) == [
            ['testc', '--version'],
            ['testc', '--version'],
            ['testc', '--version']
        ]

    @mark.parametrize(
        ['argument', 'expected'],
        [
            ({}, False),
            ({'openmp_flag': '-omp'}, True)
        ]
    )
    @mark.parametrize('control', [False, True])
    def test_openmp_control(self,
                            argument: Dict[str, Optional[str]],
                            expected: str, control: bool,
                            fake_process: FakeProcess) -> None:
        """
        Tests the OpenMP argument.
        """
        if control:
            command = ['sfortran', '-c', argument.get('openmp_flag') or '',
                       'a.f90', '-o', 'a.o']
        else:
            command = ['sfortran', '-c', 'a.f90', '-o', 'a.o']
        fake_process.register(command)

        fc = Compiler("some fortran", "sfortran", "some",
                      version_regex=r'',
                      category=Category.FORTRAN_COMPILER,
                      mpi=False,
                      **argument)

        fc.compile_file(Path("a.f90"), Path("a.o"), openmp=control)

        assert call_list(fake_process) \
               == [command]


class TestCCompiler:
    """
    Tests base C compiler tool.
    """

    def test_construction(self) -> None:
        """
        Tests Construction.
        """
        cc = Compiler("some c", "scc", "some",
                      version_regex=r"([\d.]+)", category=Category.C_COMPILER,
                      openmp_flag="-omp")
        assert cc.category == Category.C_COMPILER
        assert cc._compile_flag == "-c"
        assert cc.output_flag == "-o"
        assert cc.flags == []
        assert cc.suite == "some"
        assert not cc.mpi
        assert cc.openmp_flag == "-omp"

    def test_openmp_construction(self) -> None:
        """
        Tests OpenMP support.
        """
        cc = CCompiler("some c", "scc", "some",
                       openmp_flag="-omp", version_regex=r'([\d.]+)')
        assert cc.openmp_flag == "-omp"
        assert cc.openmp

        cc = CCompiler("some c", "scc", "some",
                       openmp_flag=None, version_regex=r'([\d.]+)')
        assert cc.openmp_flag == ""
        assert not cc.openmp

        cc = CCompiler("some c", "scc", "some",
                       version_regex=r'([\d.]+)')
        assert cc.openmp_flag == ""
        assert not cc.openmp


class TestFortranCompiler:
    """
    Tests base Fortran compiler tool.
    """

    def test_construction(self) -> None:
        """
        Tests basic Fortran compiler construction.
        """
        fc = FortranCompiler("some fortran", "sfortran", "some",
                             openmp_flag="-omp", version_regex=r"([\d.]+)",
                             module_folder_flag="-mod-dir")
        assert fc._compile_flag == "-c"
        assert fc.output_flag == "-o"
        assert fc.category == Category.FORTRAN_COMPILER
        assert fc.suite == "some"
        assert fc.flags == []
        assert not fc.mpi
        assert fc.openmp_flag == "-omp"

    @mark.parametrize(
        ['argument', 'expected'],
        [
            ({}, False),
            ({'openmp_flag': None}, False),
            ({'openmp_flag': '-omp'}, True)
        ]
    )
    def test_openmp_construction(self,
                                 argument: Dict[str, Optional[str]],
                                 expected: str) -> None:
        fc = FortranCompiler("some fortran", "sfortran", "some",
                             module_folder_flag="-mod-dir",
                             version_regex=r'([\d.]+)',
                             mpi=False,
                             **argument)
        assert fc.openmp is expected
        if expected:
            assert fc.openmp_flag == argument['openmp_flag']
        else:
            assert fc.openmp_flag == ''

    @mark.parametrize(
        ['argument', 'expected'],
        [
            ({}, False),
            ({'syntax_only_flag': None}, False),
            ({'syntax_only_flag': '-syntax'}, True)
        ]
    )
    def test_syntax_only(self,
                         argument: Dict[str, Optional[str]],
                         expected: bool):
        """
        Tests "syntax only" functionality.
        """
        fc = FortranCompiler("some fortran", "sfortran", "some",
                             version_regex=r'([\d.]+)])',
                             openmp_flag="-omp",
                             module_folder_flag="-mod-dir",
                             mpi=False,
                             **argument)
        assert fc.has_syntax_only is expected

    def test_module_dir_args(self, fake_process: FakeProcess) -> None:
        """
        Tests handling of module directory argument.
        """
        command = ['tfortran', '-c', '-O3', '-mod-dir', '/module_out', 'a.f90', '-o', 'a.o']
        fake_process.register(command)

        fc = FortranCompiler("test fortran", "tfortran", suite="test",
                             version_regex=r'([\d.]+)',
                             module_folder_flag='-mod-dir')
        fc.set_module_output_path(Path("/module_out"))

        with warns(UserWarning, match="Removing managed flag"):
            fc.compile_file(Path("a.f90"), Path("a.o"), openmp=False,
                            add_flags=["-mod-dir/b", "-O3"])
        assert call_list(fake_process) == [command]

    def test_openmp_args(self, fake_process: FakeProcess) -> None:
        command = ['tfortran', '-c', '-omp', '-omp', 'a.f90', '-o', 'a.o']
        fake_process.register(command)

        fc = FortranCompiler("test fortran", "tfortran", suite="test",
                             version_regex=r'([\d.]+)', openmp_flag='-omp')
        with warns(UserWarning,
                   match="explicitly provided. OpenMP should be enabled in "
                         "the BuildConfiguration"):
            fc.compile_file(Path("a.f90"), Path("a.o"), add_flags=["-omp"],
                            openmp=True)
        assert call_list(fake_process) == [command]

    @mark.parametrize(['version_string', 'version'],
                      [('6.1.0', (6, 1, 0)),
                       ('5.6', (5, 6)),
                       ('19.0.0.117', (19, 0, 0, 117))])
    def test_get_version_string(self, version_string: str, version: Tuple[int],
                                fake_process: FakeProcess) -> None:
        """
        Tests version number retrieval.
        """
        full_string = f'Some {version_string} Fortran compiler'
        recorder = fake_process.register(['sfortran', '--version'],
                                         stdout=full_string)
        compiler = FortranCompiler('some fortran', 'sfortran', 'some',
                                   r'^Some ([\d.]+) Fortran')
        assert compiler.get_version_string() == version_string
        assert compiler.get_version() == version
        assert [call.args for call in recorder.calls] == [['sfortran',
                                                           '--version']]

    def test_get_version_1_part_version(self,
                                        fake_process: FakeProcess) -> None:
        """
        Tests an invalid single value version string.
        """
        version_string = "Some 666 Fortran compiler"
        recorder = fake_process.register(['sfortran', '--version'],
                                         stdout=version_string)
        compiler = FortranCompiler('some fortran', 'sfortran', 'some',
                                   r'^Some ([\d.]+) Fortran')
        with raises(RuntimeError) as err:
            compiler.get_version()
        assert [call.args for call in recorder.calls] == [['sfortran',
                                                           '--version']]
        assert str(err.value).startswith(
            "Unexpected version output format for compiler"
        )

    @mark.parametrize("version_string",
                      ["Some 5.15f.2 Fortran compiler",
                       "Some .0.5.1 Fortran compiler",
                       "Some 0.5.1. Fortran compiler",
                       "Some 0.5..1 Fortran compiler",
                       "Doesn't match at all"])
    def test_get_version_bad_format(self, version_string,
                                    fake_process: FakeProcess) -> None:
        """
        Tests version strings not matching the RegEx.
        """
        recorder = fake_process.register(['sfortran', '--version'],
                                         stdout=version_string)
        compiler = FortranCompiler('some fortran', 'sfortran', 'some',
                                   r'Some ([\d.]+) Fortran')
        with raises(RuntimeError) as err:
            compiler.get_version()
        assert [call.args for call in recorder.calls] == [['sfortran',
                                                           '--version']]
        assert str(err.value).startswith(
            "Unexpected version output format for compiler"
        )

    def test_get_version_command_failure(self,
                                         fake_process: FakeProcess) -> None:
        """
        Tests version retrieval failure.
        """
        fake_process.register(['sfortran', '--version'],
                              returncode=1)
        compiler = FortranCompiler('some fortran', 'sfortran', 'some',
                                   r'Some ([\d.]+) Fortran')
        with raises(RuntimeError) as err:
            compiler.get_version()
        assert str(err.value).startswith(
            "Error asking for version of compiler"
        )

    def test_get_version_caching(self, fake_process: FakeProcess) -> None:
        """
        Tests caching of version data.
        """
        fake_process.keep_last_process(True)
        recorder = fake_process.register(['sfortran', '--version'],
                                         stdout="1.2.3")
        compiler = FortranCompiler('some fortran', 'sfortran', 'some',
                                   r'([\d.]+)')
        assert compiler.get_version() == (1, 2, 3)
        assert compiler.get_version() == (1, 2, 3)
        assert [call.args for call in recorder.calls] == [['sfortran',
                                                           '--version']]

    def test_get_version_bad_result_caching(
            self, fake_process: FakeProcess
    ) -> None:
        """
        Tests failure to get version is not cached.
        """
        fake_process.register(['sfortran', '--version'],
                              returncode=1)
        fake_process.register(['sfortran', '--version'],
                              stdout='4.5.6')
        compiler = FortranCompiler('some fortran', 'sfortran', 'some',
                                   r'([\d.]+)')
        with raises(RuntimeError):
            compiler.get_version()

        assert compiler.get_version() == (4, 5, 6)
        assert call_list(fake_process) \
               == [['sfortran', '--version'], ['sfortran', '--version']]

    def test_module_directory(self, fake_process: FakeProcess) -> None:
        """
        Tests module directory handling.
        """
        command = ['sfortran', '-c', '-mod-dir', '/module_out',
                   'a.f90', '-o', 'a.o']
        fake_process.register(command)
        fc = FortranCompiler("some fortran", "sfortran", suite="some",
                             version_regex=r'([\d.]+)',
                             module_folder_flag="-mod-dir")
        fc.set_module_output_path(Path("/module_out"))
        # ToDo: Warning - private member access.
        assert fc._module_output_path == "/module_out"
        fc.compile_file(Path("a.f90"), Path("a.o"), openmp=False)
        assert call_list(fake_process) \
               == [command]


class TestGcc:
    """
    Tests GCC tool.
    """

    def test_check_available(self, fake_process: FakeProcess) -> None:
        """
        Tests availability check.
        """
        recorder = fake_process.register(['gcc', '--version'],
                                         stdout='gcc (dummy) 1.2.3')
        cc = Gcc()
        assert cc.check_available()
        assert [call.args for call in recorder.calls] == [['gcc', '--version']]

    def test_check_available_error(self, fake_process: FakeProcess) -> None:
        """
        Tests not available.
        """
        recorder = fake_process.register(['gcc', '--version'],
                                         returncode=1, stderr="Not found")
        cc = Gcc()
        assert not cc.check_available()
        assert [call.args for call in recorder.calls] == [['gcc', '--version']]

    def test_hash_error(self, fake_process: FakeProcess) -> None:
        """
        Tests hashing of missing version information
        """
        recorder = fake_process.register(['gcc', '--version'], returncode=1)
        cc = Gcc()

        with raises(RuntimeError) as err:
            cc.get_hash()
        assert [call.args for call in recorder.calls] == [['gcc', '--version']]
        assert "Error asking for version of compiler" in str(err.value)

    def test_hash_invalid_version(self, fake_process: FakeProcess) -> None:
        """
        Tests hahing bad version information.
        """
        recorder = fake_process.register(['gcc', '--version'],
                                         stdout="foo v1")
        cc = Gcc()
        with raises(RuntimeError) as err:
            cc.get_hash()
        assert [call.args for call in recorder.calls] == [['gcc', '--version']]
        assert str(err.value).startswith(
            "Unexpected version output format for compiler 'gcc'"
        )

    def test_with_env_cflags(self, monkeypatch) -> None:
        """
        Tests CFLAGS are honoured and FFLAGS are not.
        """
        monkeypatch.setenv('CFLAGS', '-c-one -c-two')
        monkeypatch.setenv('FFLAGS', '-f-one -f-two')
        cc = Gcc()
        assert cc.flags == ["-c-one", "-c-two"]

    def test_gcc(self):
        """
        Tests the default constructor.
        """
        gcc = Gcc()
        assert gcc.name == "gcc"
        assert isinstance(gcc, CCompiler)
        assert gcc.category == Category.C_COMPILER
        assert not gcc.mpi

    def test_get_version(self, fake_process: FakeProcess) -> None:
        """
        Tests the version retrieval and parsing.
        """
        version_string = dedent("""
            gcc (GCC) 8.5.0 20210514 (Red Hat 8.5.0-20)
            Copyright (C) 2018 Free Software Foundation, Inc.
            """)
        recorder = fake_process.register(['gcc', '--version'],
                                         stdout=version_string)
        gcc = Gcc()
        assert gcc.get_version() == (8, 5, 0)
        assert [call.args for call in recorder.calls] == [['gcc', '--version']]

    def test_get_version_with_icc_string(self,
                                         fake_process: FakeProcess) -> None:
        """
        Test ostensible GCC which returns ICC's version string.
        """
        version_string = dedent("""
            icc (ICC) 2021.10.0 20230609
            Copyright (C) 1985-2023 Intel Corporation.  All rights reserved.
            """)
        recorder = fake_process.register(['gcc', '--version'],
                                         stdout=version_string)
        gcc = Gcc()
        with raises(RuntimeError) as err:
            gcc.get_version()
        assert [call.args for call in recorder.calls] == [['gcc', '--version']]
        assert str(err.value).startswith(
            "Unexpected version output format for compiler"
        )


class TestGFortran:
    """
    Tests the Fortran component of the Gnu Compiler Collection.
    """

    def test_constructor(self):
        """
        Tests the default constructor
        """
        gfortran = Gfortran()
        assert gfortran.name == "gfortran"
        assert isinstance(gfortran, FortranCompiler)
        assert gfortran.category == Category.FORTRAN_COMPILER
        assert not gfortran.mpi

    # Possibly overkill to cover so many gfortran versions but I had to go
    # check them so might as well add them.
    # Note: different sources, e.g conda, change the output slightly...
    @mark.parametrize(
        ['version_string', 'version'],
        [
            [
                dedent("""
    GNU Fortran (GCC) 4.8.5 20150623 (Red Hat 4.8.5-44)
    Copyright (C) 2015 Free Software Foundation, Inc.

    GNU Fortran comes with NO WARRANTY, to the extent permitted by law.
    You may redistribute copies of GNU Fortran
    under the terms of the GNU General Public License.
    For more information about these matters, see the file named COPYING
    """), (4, 8, 5)
            ],
            [
                dedent("""
    GNU Fortran (GCC) 6.1.0
    Copyright (C) 2016 Free Software Foundation, Inc.
    This is free software; see the source for copying conditions.  There is NO
    warranty; not even for MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
    """), (6, 1, 0)
            ],
            [
                dedent("""
    GNU Fortran (conda-forge gcc 8.5.0-16) 8.5.0
    Copyright (C) 2018 Free Software Foundation, Inc.
    This is free software; see the source for copying conditions.  There is NO
    warranty; not even for MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
    """), (8, 5, 0)
            ],
            [
                dedent("""
    GNU Fortran (conda-forge gcc 10.4.0-16) 10.4.0
    Copyright (C) 2020 Free Software Foundation, Inc.
    This is free software; see the source for copying conditions.  There is NO
    warranty; not even for MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
    """), (10, 4, 0)
            ],
            [
                dedent("""
    GNU Fortran (conda-forge gcc 12.1.0-16) 12.1.0
    Copyright (C) 2022 Free Software Foundation, Inc.
    This is free software; see the source for copying conditions.  There is NO
    warranty; not even for MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
    """), (12, 1, 0)
            ]
        ]
    )
    def test_get_version(self, version_string: str, version: Tuple[int],
                         fake_process: FakeProcess) -> None:
        """
        Tests version retrieval and parsing.
        """
        recorder = fake_process.register(['gfortran', '--version'],
                                         stdout=version_string)
        gfortran = Gfortran()
        assert gfortran.get_version() == version
        assert [call.args for call in recorder.calls] == [['gfortran',
                                                           '--version']]

    def test_get_version_with_ifort_string(self,
                                           fake_process: FakeProcess) -> None:
        """
        Test ostensible GFortran which returns IFort's version string.
        """
        version_string = dedent("""
            ifort (IFORT) 14.0.3 20140422
            Copyright (C) 1985-2014 Intel Corporation.  All rights reserved.
            """)
        recorder = fake_process.register(['gfortran', '--version'],
                                         stdout=version_string)
        gfortran = Gfortran()
        with raises(RuntimeError) as err:
            gfortran.get_version()
        assert [call.args for call in recorder.calls] == [['gfortran',
                                                           '--version']]
        assert str(err.value).startswith(
            "Unexpected version output format for compiler"
        )

    def test_with_env_fflags(self, monkeypatch) -> None:
        """
        Tests FFLAGS are honoured and CFLAGS are not.
        """
        monkeypatch.setenv('CFLAGS', '-c-one -c-two')
        monkeypatch.setenv('FFLAGS', '-f-one -f-two')
        fc = Gfortran()
        assert fc.flags == ["-f-one", "-f-two"]


class TestIcc:
    """
    Tests the old Intel C compiler tool.
    """

    def test_icc(self):
        """
        Tests the default constructor.
        """
        icc = Icc()
        assert icc.name == "icc"
        assert isinstance(icc, CCompiler)
        assert icc.category == Category.C_COMPILER
        assert not icc.mpi

    def test_get_version(self, fake_process: FakeProcess) -> None:
        """
        Tests the retrieval and parsing of tool version.
        """
        version_string = dedent("""
            icc (ICC) 2021.10.0 20230609
            Copyright (C) 1985-2023 Intel Corporation.  All rights reserved.
            """)
        recorder = fake_process.register(['icc', '-V'], stdout=version_string)
        icc = Icc()
        assert icc.get_version() == (2021, 10, 0)
        assert [call.args for call in recorder.calls] == [['icc', '-V']]

    def test_get_version_with_gcc_string(self,
                                         fake_process: FakeProcess) -> None:
        """
        Tests an ostensible ICC which returns GCC's version string.
        """
        version_string = dedent("""
            gcc (GCC) 8.5.0 20210514 (Red Hat 8.5.0-20)
            Copyright (C) 2018 Free Software Foundation, Inc.
            """)
        recorder = fake_process.register(['icc', '-V'], stdout=version_string)
        icc = Icc()
        with raises(RuntimeError) as err:
            icc.get_version()
        assert [call.args for call in recorder.calls] == [['icc', '-V']]
        assert str(err.value).startswith(
            "Unexpected version output format for compiler"
        )


class TestIFort:
    """
    Test the old Intel Fortran compiler tool.
    """

    def test_constructor(self) -> None:
        """
        Tests the default constructor.
        """
        ifort = Ifort()
        assert ifort.name == "ifort"
        assert isinstance(ifort, FortranCompiler)
        assert ifort.category == Category.FORTRAN_COMPILER
        assert not ifort.mpi

    @mark.parametrize(
        ['version_string', 'version'],
        [
            [
                dedent("""
    ifort (IFORT) 14.0.3 20140422
    Copyright (C) 1985-2014 Intel Corporation.  All rights reserved.
    """), (14, 0, 3)
            ],
            [
                dedent("""
    ifort (IFORT) 15.0.2 20150121
    Copyright (C) 1985-2015 Intel Corporation.  All rights reserved.
    """), (15, 0, 2)
            ],
            [
                dedent("""
    ifort (IFORT) 17.0.7 20180403
    Copyright (C) 1985-2018 Intel Corporation.  All rights reserved.
    """), (17, 0, 7)
            ],
            [
                dedent("""
    ifort (IFORT) 19.0.0.117 20180804
    Copyright (C) 1985-2018 Intel Corporation.  All rights reserved.
    """), (19, 0, 0, 117)
            ]
        ]
    )
    def test_get_version(self, version_string: str, version: Tuple[int],
                         fake_process: FakeProcess) -> None:
        """
        Tests version detection and parsing.
        """
        recorder = fake_process.register(['ifort', '-V'],
                                         stdout=version_string)
        ifort = Ifort()
        assert ifort.get_version() == version
        assert [call.args for call in recorder.calls] == [['ifort', '-V']]

    def test_get_version_with_icc_string(self,
                                         fake_process: FakeProcess) -> None:
        """
        Tests ostensible Ifort which returns Icc's version string.
        """
        version_string = dedent("""
            icc (ICC) 2021.10.0 20230609
            Copyright (C) 1985-2023 Intel Corporation.  All rights reserved.
            """)
        recorder = fake_process.register(['ifort', '-V'],
                                         stdout=version_string)
        ifort = Ifort()
        with raises(RuntimeError) as err:
            ifort.get_version()
        assert [call.args for call in recorder.calls] == [['ifort', '-V']]
        assert str(err.value).startswith(
            "Unexpected version output format for compiler"
        )

    @mark.parametrize("version", ["5.15f.2",
                                  ".0.5.1",
                                  "0.5.1.",
                                  "0.5..1"])
    def test_get_version_invalid(self, version: str,
                                 fake_process: FakeProcess) -> None:
        """
        Tests version strings which don't match the pattern.
        """
        version_string = dedent(f"""
            ifort (IFORT) {version} 20140422
            Copyright (C) 1985-2014 Intel Corporation.  All rights reserved.
            """)
        fake_process.register(['ifort', '-V'],
                              stdout=version_string)
        ifort = Ifort()
        with raises(RuntimeError) as err:
            ifort.get_version()
        assert str(err.value).startswith(
            "Unexpected version output format for compiler"
        )


class TestIcx:
    """
    Tests the Icx C compiler tool.
    """

    def test_icx(self) -> None:
        """
        Tests default constructor.
        """
        icx = Icx()
        assert icx.name == "icx"
        assert isinstance(icx, CCompiler)
        assert icx.category == Category.C_COMPILER
        assert not icx.mpi

    def test_get_version(self, fake_process: FakeProcess) -> None:
        """
        Tests version retrieval and parsing.
        """
        version_string = dedent("""
Intel(R) oneAPI DPC++/C++ Compiler 2023.0.0 (2023.0.0.20221201)
Target: x86_64-unknown-linux-gnu
Thread model: posix
InstalledDir: /opt/intel/oneapi/compiler/2023.0.0/linux/bin-llvm
Configuration file: /opt/intel/oneapi/compiler/2023.0.0/linux/bin-llvm/../bin/icx.cfg
""")
        recorder = fake_process.register(['icx', '--version'],
                                         stdout=version_string)
        icx = Icx()
        assert icx.get_version() == (2023, 0, 0)
        assert [call.args for call in recorder.calls] == [['icx', '--version']]

    def test_get_version_with_icc_string(self,
                                         fake_process: FakeProcess) -> None:
        """
        Tests ostensible IFX which returns ICC version.
        """
        version_string = dedent("""
            icc (ICC) 2021.10.0 20230609
            Copyright (C) 1985-2023 Intel Corporation.  All rights reserved.
            """)
        recorder = fake_process.register(['icx', '--version'], stdout=version_string)
        icx = Icx()
        with raises(RuntimeError) as err:
            icx.get_version()
        assert [call.args for call in recorder.calls] == [['icx', '--version']]
        assert str(err.value).startswith(
            "Unexpected version output format for compiler"
        )


class TestIfx:
    """
    Tests Ifx Fortran tool.
    """

    def test_constructor(self) -> None:
        """
        Tests default constructor.
        """
        ifx = Ifx()
        assert ifx.name == "ifx"
        assert isinstance(ifx, FortranCompiler)
        assert ifx.category == Category.FORTRAN_COMPILER
        assert not ifx.mpi

    def test_get_version(self, fake_process: FakeProcess) -> None:
        """
        Tests version interpretation.
        """
        version_string = dedent("""
    ifx (IFORT) 2023.0.0 20221201
    Copyright (C) 1985-2022 Intel Corporation. All rights reserved.
    """)
        recorder = fake_process.register(['ifx', '--version'],
                                         stdout=version_string)
        ifx = Ifx()
        assert ifx.get_version() == (2023, 0, 0)
        assert [call.args for call in recorder.calls] == [['ifx', '--version']]

    def test_get_version_with_ifort_string(self,
                                           fake_process: FakeProcess) -> None:
        """
        Test ostensible Ifx compiler which returns Ifort version.
        """
        version_string = dedent("""
            ifort (IFORT) 19.0.0.117 20180804
            Copyright (C) 1985-2018 Intel Corporation.  All rights reserved.
            """)
        recorder = fake_process.register(['ifx', '--version'],
                                         stdout=version_string)
        ifx = Ifx()
        with raises(RuntimeError) as err:
            ifx.get_version()
        assert str(err.value).startswith(
            "Unexpected version output format for compiler"
        )
        assert [call.args for call in recorder.calls] == [['ifx', '--version']]


class TestNvC:
    """
    Tests the nVidia C tool.
    """

    def test_constructor(self) -> None:
        """
        Tests the default constructor.
        """
        nvc = Nvc()
        assert nvc.name == "nvc"
        assert isinstance(nvc, CCompiler)
        assert nvc.category == Category.C_COMPILER
        assert not nvc.mpi

    def test_get_version(self, fake_process: FakeProcess) -> None:
        '''Test nvc 23.5.0 version detection.'''
        version_string = dedent("""
nvc 23.5-0 64-bit target on x86-64 Linux -tp icelake-server
NVIDIA Compilers and Tools
Copyright (c) 2022, NVIDIA CORPORATION & AFFILIATES.  All rights reserved.
""")
        recorder = fake_process.register(['nvc', '-V'], stdout=version_string)
        nvc = Nvc()
        assert nvc.get_version() == (23, 5, 0)
        assert [call.args for call in recorder.calls] == [['nvc', '-V']]

    def test_get_version_with_icc_string(self, fake_process: FakeProcess) -> None:
        """
        Tests an ostensible nVidia compiler which returns ICC version
        information.
        """
        version_string = dedent("""
            icc (ICC) 2021.10.0 20230609
            Copyright (C) 1985-2023 Intel Corporation.  All rights reserved.
            """)
        fake_process.register(['nvc', '-V'], stdout=version_string)
        nvc = Nvc()
        with raises(RuntimeError) as err:
            nvc.get_version()
        assert str(err.value).startswith(
            "Unexpected version output format for compiler"
        )


class TestNvFortran:
    """
    Tests nVidia Fortran tool.
    """

    def test_nvfortran(self):
        """
        Tests default constructor.
        """
        nvfortran = Nvfortran()
        assert nvfortran.name == "nvfortran"
        assert isinstance(nvfortran, FortranCompiler)
        assert nvfortran.category == Category.FORTRAN_COMPILER
        assert not nvfortran.mpi

    def test_get_version(self, fake_process: FakeProcess) -> None:
        """
        Tests version detection.
        """
        version_string = dedent("""
    nvfortran 23.5-0 64-bit target on x86-64 Linux -tp icelake-server
    NVIDIA Compilers and Tools
    Copyright (c) 2022, NVIDIA CORPORATION & AFFILIATES.  All rights reserved.
    """)
        recorder = fake_process.register(['nvfortran', '-V'],
                                         stdout=version_string)
        nvfortran = Nvfortran()
        assert nvfortran.get_version() == (23, 5, 0)
        assert [call.args for call in recorder.calls] == [['nvfortran', '-V']]

    def test_get_version_with_ifort_string(self,
                                           fake_process: FakeProcess) -> None:
        """
        Tests ostensible nVidia Fortran compiler returning IFort version string.
        """
        version_string = dedent("""
            ifort (IFORT) 19.0.0.117 20180804
            Copyright (C) 1985-2018 Intel Corporation.  All rights reserved.
            """)
        recorder = fake_process.register(['nvfortran', '-V'],
                                         stdout=version_string)
        nvfortran = Nvfortran()
        with raises(RuntimeError) as err:
            nvfortran.get_version()
        assert [call.args for call in recorder.calls] == [['nvfortran', '-V']]
        assert str(err.value).startswith(
            "Unexpected version output format for compiler"
        )


class TestCrayC:
    """
    Tests Cray C tool.
    """

    def test_default_constructor(self) -> None:
        """
        Tests constructing a Craycc object without arguments.
        """
        craycc = Craycc()
        assert craycc.name == "craycc-cc"
        assert isinstance(craycc, CCompiler)
        assert craycc.category == Category.C_COMPILER
        assert craycc.mpi

    @mark.parametrize(['version_string', 'version'], [
        ["Cray C : Version 8.7.0  Tue Jul 23, 2024  07:39:46", (8, 7, 0)],
        [
            """
Cray clang version 15.0.1  (66f7391d6a03cf932f321b9f6b1d8612ef5f362c)

Target: x86_64-unknown-linux-gnu

Thread model: posix

InstalledDir: /opt/cray/pe/cce/15.0.1/cce-clang/x86_64/share/../bin

Found candidate GCC installation: /opt/gcc/10.3.0/snos/lib/gcc/x86_64-suse-linux/10.3.0

Selected GCC installation: /opt/gcc/10.3.0/snos/lib/gcc/x86_64-suse-linux/10.3.0

Candidate multilib: .;@m64

Selected multilib: .;@m64

OFFICIAL
""",
            (15, 0, 1)
        ]
    ])
    def test_get_version(self, version_string: str, version: Tuple[int],
                         fake_process: FakeProcess) -> None:
        """
        Tests version detection.
        """
        recorder = fake_process.register(['cc', '-V'], stdout=version_string)
        craycc = Craycc()
        assert craycc.get_version() == version
        assert [call.args for call in recorder.calls] == [['cc', '-V']]

    def test_get_version_with_icc_string(self, fake_process: FakeProcess) -> None:
        """
        Tests austensible Cray C compiler returning ICC version string.
        """
        version_string = dedent("""
            icc (ICC) 2021.10.0 20230609
            Copyright (C) 1985-2023 Intel Corporation.  All rights reserved.
            """)
        recorder = fake_process.register(['cc', '-V'], stdout=version_string)
        craycc = Craycc()
        with raises(RuntimeError) as err:
            craycc.get_version()
        assert [call.args for call in recorder.calls] == [['cc', '-V']]
        assert str(err.value).startswith("Unexpected version output format for compiler")


class TestCrayFortran:
    """
    Tests Cray Fortran tool.
    """

    def test_default_construction(self) -> None:
        """
        Tests object constructs correctly.
        """
        crayftn = Crayftn()
        assert crayftn.name == "crayftn-ftn"
        assert isinstance(crayftn, FortranCompiler)
        assert crayftn.category == Category.FORTRAN_COMPILER
        assert crayftn.mpi

    @mark.parametrize(['version_string', 'version'], [
        ["Cray Fortran : Version 8.7.0  Tue Jul 23, 2024  07:39:25",
         (8, 7, 0)],
        ["Cray Fortran : Version 15.0.1  Tue Jul 23, 2024  07:39:25",
         (15, 0, 1)]
    ])
    def test_get_version(self, version_string: str, version: Tuple[int],
                         fake_process: FakeProcess) -> None:
        """
        Tests various valid version strings.
        """
        recorder = fake_process.register(['ftn', '-V'], stdout=version_string)
        crayftn = Crayftn()
        assert crayftn.get_version() == version
        assert [call.args for call in recorder.calls] == [['ftn', '-V']]

    def test_get_version_with_ifort_string(self, fake_process: FakeProcess):
        """
        Tests that Ifort version string is rejected.
        """
        ifort_version = dedent("""
            ifort (IFORT) 19.0.0.117 20180804
            Copyright (C) 1985-2018 Intel Corporation.  All rights reserved.
        """)
        recorder = fake_process.register(['ftn', '-V'],
                                         stdout=ifort_version)
        crayftn = Crayftn()
        with raises(RuntimeError) as err:
            crayftn.get_version()
        assert [call.args for call in recorder.calls] == [['ftn', '-V']]
        assert str(err.value).startswith(
            "Unexpected version output format for compiler"
        )


class TestCompileSuiteTool:
    def test_suite_tool(self) -> None:
        '''Test the constructor.'''
        tool = CompilerSuiteTool("gnu", "gfortran", "gnu",
                                 Category.FORTRAN_COMPILER)
        assert str(tool) == "CompilerSuiteTool - gnu: gfortran"
        assert tool.exec_name == "gfortran"
        assert tool.name == "gnu"
        assert tool.suite == "gnu"
        assert tool.category == Category.FORTRAN_COMPILER
        assert isinstance(tool.logger, Logger)
