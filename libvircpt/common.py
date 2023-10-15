"""
    Copyright (C) 2023  Michael Ablassmeier <abi@grinser.de>

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""
import sys
import logging
import logging.handlers
from argparse import Namespace
from typing import Optional, List, Any

from libvircpt.logcount import logCount

log = logging.getLogger("lib")

logFormat = (
    "%(asctime)s %(levelname)s %(name)s %(module)s - %(funcName)s"
    " [%(threadName)s]: %(message)s"
)
logDateFormat = "[%Y-%m-%d %H:%M:%S]"
defaultCheckpointName = "virtnbdbackup"


def argparse(parser) -> Namespace:
    """Parse arguments"""
    return parser.parse_args()


def printVersion(version) -> None:
    """Print version and passed arguments"""
    log.info("Version: %s Arguments: %s", version, " ".join(sys.argv))


def setLogLevel(verbose: bool) -> int:
    """Set loglevel"""
    level = logging.INFO
    if verbose is True:
        level = logging.DEBUG

    return level


def configLogger(args: Namespace, counter: logCount):
    """Setup logging"""
    handler: List[Any]
    handler = [
        counter,
        logging.StreamHandler(stream=sys.stderr)
    ]
    logging.basicConfig(
        level=setLogLevel(args.verbose),
        format=logFormat,
        datefmt=logDateFormat,
        handlers=handler,
    )
