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
from lxml.etree import _Element

log = logging.getLogger()


def Optical(device: list, dev: str) -> bool:
    """Check if device is cdrom or floppy"""
    if device in ("cdrom", "floppy"):
        log.info("Excluding attached [%s] device: [%s].", device, dev)
        return True

    return False


def Lun(device: list, dev: str) -> bool:
    """Check if device is direct attached LUN"""
    if device == "lun":
        log.warning(
            "Excluding direct attached lun [%s].",
            dev,
        )
        return True

    return False


def Block(disk: _Element, dev: str) -> bool:
    """Check if device is direct attached block type device"""
    if disk.xpath("target")[0].get("type") == "block":
        log.warning(
            "Excluding unsupported block device [%s].",
            dev,
        )
        return True

    return False


def Raw(diskFormat: str, dev: str) -> bool:
    """Check if disk has RAW disk format"""
    if diskFormat == "raw":
        log.warning(
            "Excluding unsupported raw disk [%s].",
            dev,
        )
        return True

    return False
