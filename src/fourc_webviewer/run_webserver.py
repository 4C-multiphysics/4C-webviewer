"""Utility to run the webserver on a defined port."""

from fourc_webviewer.fourc_webserver import FourCWebServer
from fourc_webviewer_default_files import DEFAULT_INPUT_FILE


def run_webviewer(port, fourc_yaml_file=None, server=None):
    """Runs the webviewer by creating a dedicated webserver object, starting it
    and cleaning up afterwards.

    Args:
        port (int): Port number to start the server on.
        fourc_yaml_file (str|Path, optional): Path to the input fourc yaml file. If None, the default input file is used.
        server (bool, optional): If True, runs in server mode without opening a browser. Useful for SSH port forwarding.
    """

    # use the default input file
    if fourc_yaml_file is None:
        fourc_yaml_file = DEFAULT_INPUT_FILE

    fourc_webserver = FourCWebServer(fourc_yaml_file)

    # start the server after everything is set up
    if not (1 <= port <= 65535):
        raise ValueError("Port must be between 1 and 65535")

    open_browser = not bool(server)
    fourc_webserver.server.start(port=port, open_browser=open_browser)

    # run cleanup
    fourc_webserver.cleanup()
