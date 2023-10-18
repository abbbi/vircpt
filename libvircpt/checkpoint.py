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
import random
import string
import logging
from argparse import Namespace
from typing import Any, List
from lxml import etree as ElementTree
import libvirt
from libvircpt import xml

log = logging.getLogger()


def exists(
    domObj: libvirt.virDomain, checkpointName: str
) -> libvirt.virDomainCheckpoint:
    """Check if an checkpoint exists"""
    return domObj.checkpointLookupByName(checkpointName)


def getXml(cptObj: libvirt.virDomainCheckpoint) -> str:
    """Get Checkpoint XML including size, if possible. Flag
    is not supported amongst all libvirt versions."""
    try:
        return cptObj.getXMLDesc(libvirt.VIR_DOMAIN_CHECKPOINT_XML_SIZE)
    except libvirt.libvirtError as e:
        log.warning("Failed to get checkpoint info with size information: [%s]", e)
        return cptObj.getXMLDesc()


def delete(cptObj: libvirt.virDomainCheckpoint) -> bool:
    """Delete checkpoint"""
    checkpointName = cptObj.getName()
    log.debug("Attempt to remove checkpoint: [%s]", checkpointName)
    try:
        cptObj.delete()
        log.debug("Removed checkpoint: [%s]", checkpointName)
        return True
    except libvirt.libvirtError as errmsg:
        log.error("Error during checkpoint removal: [%s]", errmsg)
        return False


def _createCheckpointXml(diskList: List[Any], checkpointName: str) -> str:
    """Create valid checkpoint XML file which is passed to libvirt API"""
    top = ElementTree.Element("domaincheckpoint")
    desc = ElementTree.SubElement(top, "description")
    desc.text = "vircpt checkpoint"
    name = ElementTree.SubElement(top, "name")
    name.text = checkpointName
    disks = ElementTree.SubElement(top, "disks")
    for disk in diskList:
        # No persistent checkpoint will be created for raw disks,
        # because it is not supported. Backup will only be crash
        # consistent. If we would like to create a consistent
        # backup, we would have to create an snapshot for these
        # kind of disks, example:
        # virsh checkpoint-create-as vm4 --diskspec sdb
        # error: unsupported configuration:  \
        # checkpoint for disk sdb unsupported for storage type raw
        # See also:
        # https://lists.gnu.org/archive/html/qemu-devel/2021-03/msg07448.html
        if disk.format != "raw":
            ElementTree.SubElement(disks, "disk", {"name": disk.target})

    return xml.indent(top)


def create(args: Namespace, domObj: libvirt.virDomain, diskList):
    """Create checkpoint"""
    domObj.checkpointCreateXML(_createCheckpointXml(diskList, args.name))


def show(domObj: libvirt.virDomain):
    """list checkpoints"""
    cpts = domObj.listAllCheckpoints()
    for cpt in cpts:
        logging.info(" + %s", cpt.getName())


def getParent(args, domObj):
    """Check if current checkpoint has an parent, if so this checkpoint
    is referenced as incremental entry point for the export."""
    parent = args.name
    try:
        return exists(domObj, args.name).getParent().getName()
    except libvirt.libvirtError:
        pass

    return parent


def _createExportXml(args: Namespace, domObj: libvirt.virDomain, diskList) -> str:
    """Create xml required for exporting checkpoint. If an parent checkpoint
    exists, add the required incremental flags to the backupBegin call so the
    exported bitmap contains the changes to the last checkpoint."""
    parent = getParent(args, domObj)
    top = ElementTree.Element("domainbackup", {"mode": "pull"})
    ElementTree.SubElement(
        top, "server", {"transport": "unix", "socket": f"{args.socketfile}"}
    )

    if parent != args.name:
        incremental = ElementTree.SubElement(top, "incremental")
        incremental.text = parent
        logging.info("Export checkpoint based on parent checkpoint: [%s]", parent)
    else:
        parent = args.name

    disks = ElementTree.SubElement(top, "disks")

    for disk in diskList:
        scratchId = "".join(random.choices(string.ascii_uppercase + string.digits, k=5))
        scratchFile = f"{args.scratchdir}/backup.{scratchId}.{disk.target}"
        log.debug("Using scratch file: %s", scratchFile)
        dE = ElementTree.SubElement(
            disks,
            "disk",
            {"name": disk.target, "exportbitmap": args.name, "incremental": parent},
        )
        ElementTree.SubElement(dE, "scratch", {"file": f"{scratchFile}"})

    return xml.indent(top)


def export(
    args: Namespace,
    domObj: libvirt.virDomain,
    diskList: List[Any],
) -> None:
    """Export checkpoint data via NBD"""
    exportXml = _createExportXml(args, domObj, diskList)
    log.debug("Starting checkpoint export via API.")
    domObj.backupBegin(exportXml, None)
    log.debug("Started export via API.")
