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
from dataclasses import dataclass
from socket import gethostname
from argparse import Namespace
from typing import Any, List, Tuple, Union
from lxml.etree import _Element
import libvirt
from libvircpt.exceptions import (
    domainNotFound,
    connectionFailed,
)
from libvircpt import xml
from libvircpt import disktype


@dataclass
class DomainDisk:
    """Domain disk object"""

    target: str
    format: str
    filename: str
    path: str
    size: int


def libvirt_ignore(
    _ignore: None, _err: Tuple[int, int, str, int, str, str, None, int, int]
) -> None:
    """this is required so libvirt.py does not report errors to stderr
    which it does by default. Error messages are fetched accordingly
    using exceptions.
    """


libvirt.registerErrorHandler(f=libvirt_ignore, ctx=None)

log = logging.getLogger("virt")


class client:
    """Libvirt related functions"""

    def __init__(self, uri: Namespace) -> None:
        self.remoteHost: str = ""
        self._conn = self._connect(uri)
        self._domObj = None
        self.libvirtVersion = self._conn.getLibVersion()

    @staticmethod
    def _connectAuth(uri: str, user: str, password: str) -> libvirt.virConnect:
        """Use openAuth if connection string includes authfile or
        username/password are set"""

        def _cred(credentials, user_data) -> None:
            for credential in credentials:
                if credential[0] == libvirt.VIR_CRED_AUTHNAME:
                    credential[4] = user_data[0]
                elif credential[0] == libvirt.VIR_CRED_PASSPHRASE:
                    credential[4] = user_data[1]

        log.debug("Username: %s", user)
        log.debug("Password: %s", password)

        try:
            flags: List[Any] = [libvirt.VIR_CRED_AUTHNAME, libvirt.VIR_CRED_PASSPHRASE]
            auth: List[Any] = [flags]
            if user is not None and password is not None:
                user_data = [user, password]
                auth.append(_cred)
                auth.append(user_data)

            return libvirt.openAuth(uri, auth, 0)
        except libvirt.libvirtError as e:
            raise connectionFailed(e) from e

    @staticmethod
    def _connectOpen(uri: str) -> libvirt.virConnect:
        """Open connection with regular libvirt URI for local authentication"""
        try:
            return libvirt.open(uri)
        except libvirt.libvirtError as e:
            raise connectionFailed(e) from e

    @staticmethod
    def _reqAuth(uri: str) -> bool:
        """If authentication file is passed or qemu+ssh is used,
        no user and password are required."""
        return "authfile" in uri

    def _useAuth(self, args: Namespace) -> bool:
        """Check if we want to use advanced auth method"""
        if args.uri.startswith("qemu+"):
            return True
        if self._reqAuth(args.uri):
            return True
        if args.user or args.password:
            return True

        return False

    def _connect(self, args: Namespace) -> libvirt.virConnect:
        """return libvirt connection handle"""
        log.debug("Libvirt URI: [%s]", args.uri)
        localHostname = gethostname()
        log.debug("Hostname: [%s]", localHostname)

        if self._useAuth(args):
            log.debug(
                "Login information specified, connect libvirtd using openAuth function."
            )
            if not self._reqAuth(args.uri) and (not args.user or not args.password):
                raise connectionFailed(
                    "Username (--user) and password (--password) required."
                )
            return self._connectOpen(args.uri)

        log.debug("Connect libvirt using open function.")

        return self._connectOpen(args.uri)

    def getDomain(self, name: str) -> libvirt.virDomain:
        """Lookup domain"""
        try:
            return self._conn.lookupByName(name)
        except libvirt.libvirtError as e:
            raise domainNotFound(e) from e

    @staticmethod
    def getDomainConfig(domObj: libvirt.virDomain) -> str:
        """Return Virtual Machine configuration as XML"""
        return domObj.XMLDesc(0)

    def _getDiskPathByVolume(self, disk: _Element) -> Union[str, None]:
        """If virtual machine disk is configured via type='volume'
        get path to disk via appropriate libvirt functions,
        pool and volume setting are mandatory as by xml schema definition"""
        vol = disk.xpath("source")[0].get("volume")
        pool = disk.xpath("source")[0].get("pool")

        try:
            diskPool = self._conn.storagePoolLookupByName(pool)
            diskPath = diskPool.storageVolLookupByName(vol).path()
        except libvirt.libvirtError as errmsg:
            log.error("Failed to detect vm disk by volumes: [%s]", errmsg)
            return None

        return diskPath

    def getDomainDisksFromCheckpoint(self, cptConfig: str) -> List[DomainDisk]:
        """Parse checkpoint for disk devices included in checkpoint xml,
        skip devices which have been excluded"""
        tree = xml.asTree(cptConfig)
        devices = []
        for disk in tree.xpath("disks/disk"):
            if disk.get("checkpoint") == "no":
                continue
            dev = disk.get("name")
            devices.append(DomainDisk(dev, "", "", "", 0))

        return devices

    def getDomainDisks(self, args: Namespace, vmConfig: str) -> List[DomainDisk]:
        """Parse virtual machine configuration for disk devices, filter
        all non supported devices
        """
        tree = xml.asTree(vmConfig)
        devices = []

        excludeList = None
        if args.exclude is not None:
            excludeList = args.exclude.split(",")

        for disk in tree.xpath("devices/disk"):
            dev = disk.xpath("target")[0].get("dev")
            device = disk.get("device")
            diskFormat = disk.xpath("driver")[0].get("type")

            if excludeList is not None and dev in excludeList:
                log.warning("Excluding disk [%s] from operation as requested", dev)
                continue

            # skip cdrom/floppy and raw devices which do not support
            # creating checkpoints
            if (
                disktype.Optical(device, dev)
                or disktype.Block(disk, dev)
                or disktype.Lun(device, dev)
                or disktype.Raw(diskFormat, dev)
            ):
                continue

            diskPath = None
            diskType = disk.get("type")
            if diskType == "volume":
                log.debug("Disk [%s]: volume notation", dev)
                diskPath = self._getDiskPathByVolume(disk)
            elif diskType == "file":
                log.debug("Disk [%s]: file notation", dev)
                diskPath = disk.xpath("source")[0].get("file")
            elif diskType == "block":
                if args.raw is False:
                    log.warning(
                        "Skipping direct attached block device [%s], use option --raw to include.",
                        dev,
                    )
                    continue
                diskPath = disk.xpath("source")[0].get("dev")
            else:
                log.error("Unable to detect disk volume type for disk [%s]", dev)
                continue

            if diskPath is None:
                log.error("Unable to detect disk source for disk [%s]", dev)
                continue

            diskFileName = diskPath

            if args.include is not None and dev != args.include:
                log.info(
                    "Skipping disk: [%s] as requested: does not match disk [%s]",
                    dev,
                    args.include,
                )
                continue

            devices.append(DomainDisk(dev, diskFormat, diskFileName, diskPath, 0))

        log.debug("Device list: %s ", devices)
        return devices

    @staticmethod
    def stopExport(domObj: libvirt.virDomain) -> bool:
        """Cancel the export task using job abort"""
        try:
            domObj.abortJob()
            return True
        except libvirt.libvirtError as err:
            log.warning("Failed to stop block job: [%s]", err)
            return False

    @staticmethod
    def blockJobActive(domObj: libvirt.virDomain, disks: List[DomainDisk]) -> bool:
        """Check if there is already an active block job for this virtual
        machine, which might block"""
        for disk in disks:
            blockInfo = domObj.blockJobInfo(disk.target)
            if (
                blockInfo
                and blockInfo["type"] == libvirt.VIR_DOMAIN_BLOCK_JOB_TYPE_BACKUP
            ):
                log.debug("Running block jobs for disk [%s]", disk.target)
                log.debug(blockInfo)
                return True
        return False
