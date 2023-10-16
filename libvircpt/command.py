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

import logging
import subprocess
from typing import List

from libvircpt.processinfo import processInfo

log = logging.getLogger(__name__)


def run(cmdLine: List[str]) -> processInfo:
    """Execute passed command"""
    log.debug("CMD: %s", " ".join(cmdLine))
    with subprocess.Popen(
        cmdLine,
        close_fds=False,
        stderr=subprocess.PIPE,
        stdout=subprocess.PIPE,
    ) as p:
        p.wait()
        log.debug("Return code: %s", p.returncode)
        if p.returncode != 0:
            log.error("CMD: %s", " ".join(cmdLine))
        err = str(p.stderr)
        out = str(p.stdout)
        process = processInfo(p.pid, err, out)
        log.debug("Executed [%s] process: [%s]", cmdLine[0], process)

    return process
