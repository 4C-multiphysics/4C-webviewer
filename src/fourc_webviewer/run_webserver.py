"""Utility to run the webserver on a defined port."""

from fourc_webviewer.fourc_webserver import FourCWebServer
from fourc_webviewer_default_files import DEFAULT_INPUT_FILE

# specify server port for the app to run on
SERVER_PORT = 12345


def run_webviewer(fourc_yaml_file=None):
    """Runs the webviewer by creating a dedicated webserver object, starting it
    and cleaning up afterwards."""

    # use the default input file
    if fourc_yaml_file is None:
        fourc_yaml_file = DEFAULT_INPUT_FILE

    fourc_webserver = FourCWebServer(fourc_yaml_file)

    # start the server after everything is set up
    fourc_webserver.server.start(port=SERVER_PORT)

    # run cleanup
    fourc_webserver.cleanup()
