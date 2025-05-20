"""Utility to run the webserver on a defined port."""

from fourc_webviewer_default_files import (
    DEFAULT_INPUT_FILE,
)

# specify server port for the app to run on
SERVER_PORT = 12345


def run_webviewer(no_webserver, fourc_yaml_file=None):
    """Runs the webviewer by creating a dedicated webserver object, starting it
    and cleaning up afterwards."""

    if fourc_yaml_file is None:
        fourc_yaml_file = str(DEFAULT_INPUT_FILE)

    # create fourc webserver object
    fourc_webserver = FourCWebServer(
        page_title="4C Webviewer", fourc_yaml_file=fourc_yaml_file
    )

    # start the server after everything is set up
    if not no_webserver:
        fourc_webserver.server.start(port=SERVER_PORT)

    # run cleanup
    fourc_webserver.cleanup()
