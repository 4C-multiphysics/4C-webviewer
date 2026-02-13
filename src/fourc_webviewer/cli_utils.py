"""CLI utils module."""

import argparse

import fourc_webviewer.run_webserver as webserver


def main():
    """Get the CLI arguments and start the webviewer."""
    arguments = get_arguments()
    webserver.run_webviewer(**arguments)


def get_arguments():
    """Get the CLI arguments.

    Returns:
        dict: Arguments dictionary
    """
    parser = argparse.ArgumentParser(description="4C Webviewer")
    parser.add_argument(
        "--port",
        type=int,
        default=12345,
        help="port to start the app on",
    )
    parser.add_argument(
        "--fourc_yaml_file", type=str, help="input file path to visualize"
    )
    parser.add_argument(
        "--server",
        action="store_true",
        help="start app in server mode without opening the browser (useful for local port forwarding via ssh)",
    )

    args = parser.parse_args()

    # return arguments as dict
    return vars(args)
