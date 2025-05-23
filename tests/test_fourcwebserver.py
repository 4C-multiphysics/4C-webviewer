"""Test FourC webserver."""

import pytest
from fourcipp.fourc_input import FourCInput

from fourc_webviewer.fourc_webserver import DEFAULT_INPUT_FILE, FourCWebServer


@pytest.fixture(name="fourc_webserver")
def fixture_fourc_webserver():
    """FourC webserver fixture."""
    return FourCWebServer()


@pytest.mark.parametrize(
    "key, reference_value",
    [
        ("render_count", {"change_selected_material": 0, "change_fourc_yaml_file": 0}),
        ("fourc_yaml_content", FourCInput.from_4C_yaml(DEFAULT_INPUT_FILE)),
        ("fourc_yaml_name", DEFAULT_INPUT_FILE.name),
    ],
)
def test_webserver_server_variables(fourc_webserver, key, reference_value):
    """Test if server variables are initialised correctly."""
    assert fourc_webserver._server_vars[key] == reference_value
