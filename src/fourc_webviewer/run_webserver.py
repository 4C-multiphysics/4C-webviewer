"""Utility to run the webserver on a defined port."""

from fourc_webviewer.fourc_webserver import FourCWebServer

# specify server port for the app to run on
SERVER_PORT = 12345


def run_webviewer(fourc_yaml_file=None):
    """Runs the webviewer by creating a dedicated webserver object, starting it
    and cleaning up afterwards."""

    fourc_webserver = FourCWebServer(fourc_yaml_file)

    # start the server after everything is set up
    fourc_webserver.server.start(port=SERVER_PORT)

    # run cleanup
    fourc_webserver.cleanup()
