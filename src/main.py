import subprocess
import os
import logging
import sys
from shutil import which
import ctypes
import web


def initialise_logging() -> None:
    """Setup logging library
    """
    FORMAT_STRING = 'level=%(levelname)s datetime=%(asctime)s %(message)s'
    logging.basicConfig(encoding='utf-8',
                        level=logging.DEBUG,
                        format=FORMAT_STRING)

    log = logging.getLogger('waitress')
    log.disabled = True


def checkForBinary() -> None:
    """Check that speedtest is installed
    """
    if which("speedtest") is None:
        logging.error("Speedtest CLI binary not found. Please install it by" +
                      " going to the official website.\n" +
                      "https://www.speedtest.net/apps/cli")
        sys.exit(1)
    speedtestVersionDialog = (subprocess.run(['speedtest', '--version'],
                              capture_output=True, text=True))
    if "Speedtest by Ookla" not in speedtestVersionDialog.stdout:
        logging.error("Speedtest CLI that is installed is not the official" +
                      " one. Please install it by going to the official" +
                      " website.\nhttps://www.speedtest.net/apps/cli")
        sys.exit(1)


def checkAdmin() -> None:
    """Aborts the program if it is not run with elevated privalges
    """
    isAdmin = False
    try:
        isAdmin = os.getuid() == 0
    except AttributeError:
        isAdmin = ctypes.windll.shell32.IsUserAnAdmin() != 0

    if not isAdmin:
        logging.error("You must run this exporter as admin.")
        sys.exit(1)


if __name__ == '__main__':
    checkAdmin()
    checkForBinary()
    initialise_logging()
    web.run_app()
