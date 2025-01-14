# ##############################################################################
#  (c) Crown copyright Met Office. All rights reserved.
#  For further details please refer to the file COPYRIGHT
#  which you should have received as part of this distribution
# ##############################################################################
from pathlib import Path

from fab.build_config import BuildConfig
from fab.steps.preprocess import preprocess_fortran
from fab.tool_box import ToolBox


class Test_preprocess_fortran:
    def test_little_f90(self, tmp_path: Path, monkeypatch):
        """
        Ensures little f90 files are copied.
        """
        config = BuildConfig('proj', ToolBox(), fab_workspace=tmp_path)
        config.source_root.mkdir(parents=True)
        little_f90 = Path(config.source_root / 'little.f90')
        little_f90.write_text("#define BEEF")

        with config:
            preprocess_fortran(config, lambda s: [little_f90])

        assert (config.build_output / 'little.f90').read_text() \
            == "#define BEEF"  # No preprocessing.

    def test_big_F90(self, tmp_path: Path, monkeypatch):
        """
        Ensures big F90 files are preprocessed.
        """
        config = BuildConfig('proj', ToolBox(), fab_workspace=tmp_path)
        big_f90 = Path(config.source_root / 'big.F90')

        def my_preprocess(*args, **kwargs):
            assert args[1] == big_f90
            assert kwargs == {}
        monkeypatch.setattr('fab.steps.preprocess.Preprocessor.preprocess',
                            my_preprocess)
        with config:
            preprocess_fortran(config, lambda s: [big_f90])
