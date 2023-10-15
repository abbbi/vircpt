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
import os
import string
import random
import logging
from dataclasses import dataclass
from socket import gethostname
from argparse import Namespace
from typing import Any, Dict, List, Tuple, Union
from lxml.etree import _Element
from lxml import etree as ElementTree
import libvirt
from libvircpt.exceptions import (
    domainNotFound,
    connectionFailed,
    startBackupFailed,
)
from libvircpt import fs
from libvircpt import xml
from libvircpt import disktype


@dataclass
class DomainDisk:
    """Domain disk object"""

    target: str
    format: str
    filename: str
    path: str


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

    @staticmethod
    def _isSsh(uri: str) -> bool:
        """If authentication file is passed or qemu+ssh is used,
        no user and password are required."""
        return uri.startswith("qemu+ssh")

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
            if (
                not self._reqAuth(args.uri)
                and not self._isSsh(args.uri)
                and (not args.user or not args.password)
            ):
                raise connectionFailed(
                    "Username (--user) and password (--password) required."
                )
            if not self._isSsh(args.uri):
                conn = self._connectAuth(args.uri, args.user, args.password)
            else:
                conn = self._connectOpen(args.uri)

            remoteHostname = conn.getHostname()
            log.debug("Hostname returned by libvirt API: [%s]", remoteHostname)
            if localHostname != remoteHostname:
                log.info(
                    "Connected to remote host: [%s], local host: [%s]",
                    conn.getHostname(),
                    gethostname(),
                )
                self.remoteHost = remoteHostname

            return conn

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
                log.warning("Excluding disk [%s] from backup as requested", dev)
                continue

            # skip cdrom/floppy devices
            if disktype.Optical(device, dev):
                continue

            # include other direct attached devices if --raw option is enabled
            if args.raw is False and (
                disktype.Block(disk, dev)
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

            diskFileName = os.path.basename(diskPath)

            if args.include is not None and dev != args.include:
                log.info(
                    "Skipping disk: [%s] as requested: does not match disk [%s]",
                    dev,
                    args.include,
                )
                continue

            devices.append(
                DomainDisk(dev, diskFormat, diskFileName, diskPath)
            )

        log.debug("Device list: %s ", devices)
        return devices

    def _createBackupXml(self, args: Namespace, diskList) -> str:
        """Create XML file for starting an backup task using libvirt API."""
        top = ElementTree.Element("domainbackup", {"mode": "pull"})
        if self.remoteHost == "":
            ElementTree.SubElement(
                top, "server", {"transport": "unix", "socket": f"{args.socketfile}"}
            )
        else:
            listen = self.remoteHost
            tls = "no"
            if args.tls:
                tls = "yes"
            if args.nbd_ip != "":
                listen = args.nbd_ip
            ElementTree.SubElement(
                top,
                "server",
                {"tls": f"{tls}", "name": f"{listen}", "port": f"{args.nbd_port}"},
            )

        disks = ElementTree.SubElement(top, "disks")

        for disk in diskList:
            scratchId = "".join(
                random.choices(string.ascii_uppercase + string.digits, k=5)
            )
            scratchFile = f"{args.scratchdir}/backup.{scratchId}.{disk.target}"
            log.debug("Using scratch file: %s", scratchFile)
            dE = ElementTree.SubElement(disks, "disk", {"name": disk.target})
            ElementTree.SubElement(dE, "scratch", {"file": f"{scratchFile}"})

        return xml.indent(top)

    def startExport(
        self,
        args: Namespace,
        domObj: libvirt.virDomain,
        diskList: List[Any],
    ) -> None:
        """Export checkpoint data via NBD"""
        backupXml = self._createBackupXml(args, diskList)
        checkpointXml = None
        freezed = False

        try:
            log.debug("Starting backup job via libvirt API.")
            domObj.backupBegin(backupXml, checkpointXml)
            log.debug("Started backup job via libvirt API.")
        except libvirt.libvirtError as errmsg:
            raise startBackupFailed(f"Failed to start backup: [{errmsg}]") from errmsg
        except Exception as e:
            log.exception(e)
            raise startBackupFailed(
                f"Unknown exception during backup start: [{e}]"
            ) from e
        finally:
            # check if filesystem is freezed and thaw
            # in case creating checkpoint fails.
            if freezed is True:
                fs.thaw(domObj)

    @staticmethod
    def stopExport(domObj: libvirt.virDomain) -> bool:
        """Cancel the export task using job abort"""
        try:
            domObj.abortJob()
            return True
        except libvirt.libvirtError as err:
            log.warning("Failed to stop backup job: [%s]", err)
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
