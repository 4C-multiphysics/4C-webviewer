"""Test FourC webserver."""

from pathlib import Path

import pytest
from fourcipp.fourc_input import FourCInput

from fourc_webviewer.fourc_webserver import FourCWebServer

# list of test files to be verified
TEST_FILES = [
    Path(__file__).parent
    / "files"
    / "mat_transviso_viscoplast_refJC_log_substep.4C.yaml",
    Path(__file__).parent / "files" / "tutorial_solid_exo.4C.yaml",
    Path(__file__).parent / "files" / "tutorial_solid_vtu.4C.yaml",
    Path(__file__).parent / "files" / "constr3D_shrinking_new_struct.4C.yaml",
    Path(__file__).parent / "files" / "poro_3D_hex8_new_struct.4C.yaml",
    Path(__file__).parent
    / "files"
    / "poro_3D_hex8_new_struct_no_result_description.4C.yaml",
]

# server variables which should be fully initialized
SERVER_VARS_TO_CHECK = [
    ("render_count", {"change_selected_material": 0, "change_fourc_yaml_file": 0}),
    ("fourc_yaml_content", FourCInput.from_4C_yaml),
    ("fourc_yaml_name", lambda f: f.name),
]


@pytest.mark.parametrize("fourc_yaml_file", TEST_FILES)
@pytest.mark.parametrize("key, expected", SERVER_VARS_TO_CHECK)
def test_webserver_variables(fourc_yaml_file, key, expected):
    """Test that server variables are correctly initialized for different input
    files."""
    webserver = FourCWebServer(fourc_yaml_file=fourc_yaml_file)

    # handle expected value if it's a callable
    expected_value = expected(fourc_yaml_file) if callable(expected) else expected

    assert webserver._server_vars[key] == expected_value


@pytest.mark.parametrize("fourc_yaml_file", TEST_FILES)
def test_webvserver_vtu_conversion(fourc_yaml_file):
    """Test that the geometric mesh can be output to a suitable vtu file for
    different input files."""
    webserver = FourCWebServer(fourc_yaml_file=fourc_yaml_file)

    # check if path is not None or empty -> this means that a geometry vtu file was exported based on the given yaml file
    vtu_path = webserver.state.vtu_path
    assert vtu_path, "vtu_path should not be empty"

    # check whether stem matches expectation
    assert Path(vtu_path).stem == fourc_yaml_file.stem
