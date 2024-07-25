# ##############################################################################
#  (c) Crown copyright Met Office. All rights reserved.
#  For further details please refer to the file COPYRIGHT
#  which you should have received as part of this distribution
# ##############################################################################
import subprocess
from pathlib import Path

from fab.artefacts import ArtefactSet
from fab.build_config import BuildConfig
from fab.steps.analyse import analyse
from fab.steps.compile_fortran import compile_fortran
from fab.steps.find_source_files import find_source_files
from fab.steps.grab.folder import grab_folder
from fab.steps.link import link_exe
from fab.steps.preprocess import preprocess_fortran
from fab.tools import ToolBox


import pytest


def build(fab_workspace, fpp_flags=None):
    with BuildConfig(fab_workspace=fab_workspace, tool_box=ToolBox(),
                     project_label='foo', multiprocessing=False) as config:
        grab_folder(config, Path(__file__).parent / 'project-source')
        find_source_files(config)
        preprocess_fortran(config, common_flags=fpp_flags)
        analyse(config, root_symbol=['stay_or_go_now'])
        with pytest.warns(UserWarning, match="Removing managed flag"):
            compile_fortran(config, common_flags=['-c'])
        link_exe(config, flags=['-lgfortran'])

    return config


def test_FortranPreProcess(tmp_path):

    # stay
    stay_config = build(fab_workspace=tmp_path,
                        fpp_flags=['-P', '-DSHOULD_I_STAY=yes'])

    stay_exe = list(stay_config.artefact_store[ArtefactSet.EXECUTABLES])[0]
    stay_res = subprocess.run(str(stay_exe), capture_output=True)
    assert stay_res.stdout.decode().strip() == 'I should stay'

    # go
    go_config = build(fab_workspace=tmp_path, fpp_flags=['-P'])

    go_exe = list(go_config.artefact_store[ArtefactSet.EXECUTABLES])[0]
    go_res = subprocess.run(str(go_exe), capture_output=True)
    assert go_res.stdout.decode().strip() == 'I should go now'
