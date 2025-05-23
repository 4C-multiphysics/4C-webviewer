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
        "--no_webserver",
        action="store_true",
        help="Don't start the webserver with its GUI?",
    )
    parser.add_argument(
        "--fourc_yaml_file", type=str, help="input file path to visualize"
    )
    parser.set_defaults(no_webserver=False)

    args = parser.parse_args()

    # return arguments as dict
    return vars(args)
