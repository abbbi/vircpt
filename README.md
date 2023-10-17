<!-- START doctoc generated TOC please keep comment here to allow auto update -->
<!-- DON'T EDIT THIS SECTION, INSTEAD RE-RUN doctoc TO UPDATE -->
**Table of Contents**

- [vircpt](#vircpt)
- [About](#about)
- [Examples](#examples)
  - [Creating an checkpoint](#creating-an-checkpoint)
  - [List checkpoints](#list-checkpoints)
  - [Start NBD export for a specific checkpoint](#start-nbd-export-for-a-specific-checkpoint)
  - [Query export information for a specific checkpoint](#query-export-information-for-a-specific-checkpoint)
  - [Release an export](#release-an-export)
  - [Removing checkpoints](#removing-checkpoints)
- [Filesystem Consistency](#filesystem-consistency)
- [Use Cases](#use-cases)
  - [Creating full backups from existent checkpoints](#creating-full-backups-from-existent-checkpoints)
  - [Boot the system from a checkpoint](#boot-the-system-from-a-checkpoint)
  - [Agentless clamav or other anti virus engines](#agentless-clamav-or-other-anti-virus-engines)
- [Requirements](#requirements)
- [TODO / Ideas](#todo--ideas)

<!-- END doctoc generated TOC please keep comment here to allow auto update -->

# vircpt

Libvirt checkpoint swiss army knife.

# About

`vircpt` can be used to manage libvirt virtual domain checkpoints, as in:

 * create checkpoints
 * delete checkpoints
 * list checkpoints
 * export checkpoints using the internal QEMU NBD server
 
Check the [Use Cases](#use-cases) for more examples why this may
be useful to you.

# Examples

## Creating an checkpoint

Create an checkpoint named "foo":

```
# vircpt -d vm1 create --name foo
INFO lib common - printVersion: Version: 0.1 Arguments: ./vircpt -d vm1 create --name foo
INFO root vircpt - main: Libvirt library version: [9000000]
INFO root disktype - Optical: Skipping attached [cdrom] device: [sdb].
INFO root disktype - Optical: Skipping attached [floppy] device: [fda].
WARNING fs fs - freeze: Guest agent is not responding: QEMU guest agent is not connected
INFO root vircpt - main: Finished successfully
```

## List checkpoints

In order to view existing checkpoints, use:

```
# vircpt -d vm1 list
INFO lib common - printVersion: Version: 0.1 Arguments: ./vircpt -d vm1 list
INFO root vircpt - main: Libvirt library version: [9000000]
INFO root disktype - Optical: Skipping attached [cdrom] device: [sdb].
INFO root disktype - Optical: Skipping attached [floppy] device: [fda].
INFO root vircpt - main: List of existing checkpoints:
INFO root checkpoint - show:  + foo
INFO root vircpt - main: Finished successfully
```

## Start NBD export for a specific checkpoint

To access the virtual machine disk image and checkpoint data, use the export
parameter:

```
# vircpt -d vm1 export --name foo
INFO lib common - printVersion: Version: 0.1 Arguments: ./vircpt -d vm1 export --name foo
INFO root vircpt - main: Libvirt library version: [9000000]
INFO root disktype - Optical: Skipping attached [cdrom] device: [sdb].
INFO root disktype - Optical: Skipping attached [floppy] device: [fda].
INFO root vircpt - main: Socket for exported checkpoint: [/var/tmp/vircpt.207990]
INFO root vircpt - main: -----------------------------------
INFO root vircpt - main: Useful commands:
INFO root vircpt - main: -----------------------------------
INFO root vircpt - main: [nbdinfo 'nbd+unix:///?socket=/var/tmp/vircpt.207990' --list]
INFO root vircpt - main: Disk: sda
INFO root vircpt - showcmd:  [qemu-img create -F raw -b nbd+unix:///sda?socket=/var/tmp/vircpt.207990 -f qcow2 /tmp/image_sda.qcow2]
INFO root vircpt - showcmd:  [qemu-nbd -c /dev/nbd0 /tmp/image_sda.qcow2]  && [virsh attach-disk tgtvm --source /dev/nbd0 --target vdX]
INFO root vircpt - showcmd:  [qemu-nbd -c /dev/nbd0 'nbd+unix:///sda?socket=/var/tmp/vircpt.207990' -r] && [fdisk -l /dev/nbd0]
INFO root vircpt - showcmd:  [nbdcopy 'nbd+unix:///sda?socket=/var/tmp/vircpt.207990' -p backup-sda.img]
INFO root vircpt - showcmd:  [qemu-img create -f qcow2 backup-sda.qcow2 1048576B && nbdcopy -p 'nbd+unix:///sda?socket=/var/tmp/vircpt.207990' -- [ qemu-nbd -f qcow2 backup-sda.qcow2 ]]
INFO root vircpt - main: -----------------------------------
INFO root vircpt - main: Finished successfully
```

The output will create some useful commands for operating on the created
NBD socket endpoint, such as:

 * Query info about exported devices using nbdinfo.
 * Create an overlay image with NBD socket backend (for direct boot)
 * Setup and NBD Device for the overlay image, which can then be attached
 to another virtual machine

Its also possible to show detailed information about the NBD export
via `--showinfo` option.

nbdinfo example:

```
# nbdinfo 'nbd+unix:///?socket=/var/tmp/vircpt.207990' --list
protocol: newstyle-fixed without TLS, using structured packets
export="sda":
        export-size: 52428800 (50M)
        uri: nbd+unix:///sda?socket=/var/tmp/vircpt.207990
        contexts:
                base:allocation
                qemu:dirty-bitmap:foo-sda
        is_rotational: false
[..]
```

In order to query the bitmap information about changed blocks since the
checkpoint was created, an NBD client which supports the NBD meta context
option is required.

## Query export information for a specific checkpoint

In order to show the bitmap block mappings use:

```
# vircpt -d vm4 nbdmap --name TEST -f /var/tmp/vircpt.115025
INFO lib common - printVersion: Version: 0.1 Arguments: ./vircpt -d vm4 nbdmap --name TEST -f /var/tmp/vircpt.115025
INFO root vircpt - main: Libvirt library version: [9000000]
WARNING root disktype - Raw: Excluding unsupported raw disk [sdb].
INFO root vircpt - main: Checkpoint/bitmap mapping:
INFO root vircpt - main: Disk: [sda]:[/tmp/tmp.ReIIt657Nw/vm4-sda.qcow2]
[
  {
    "offset": 0,
    "length": 1048576,
    "type": 0,
    "description": "clean"
  }
]
```

## Release an export

To release an export:

```
# vircpt  -d vm1 release
```

## Removing checkpoints

Remove checkpoints via:

```
# vircpt -d vm1 delete --name foo
```

# Filesystem Consistency

If reachable, `vircpt` will attempt to freeze the domains file systems via Qemu
agent during checkpoint creation for file system consistency.


# Use Cases
## Creating full backups from existent checkpoints

In combination with other tools `vircpt` can be used to create backups.

1) create a new checkpoint:

```
# vircpt -d vm4 create --name backupcheckpoint
```

2) export the checkpoint via NBD:

```
# vircpt -d vm4 export --name backupcheckpoint
[..]
INFO root vircpt - showcmd: Socket for exported checkpoint: [/var/tmp/vircpt.12780]
[..]
```

3) backup the first disk (sda) data via `nbdcopy` into a full raw device:

```
# nbdcopy 'nbd+unix:///sda?socket=/var/tmp/vircpt.12377' -p backup-sda.img
```

As alternative, backup the first disk into an thin provisioned qcow2 image
(size of the image depends on your setup, see the export
command output for example):

```
# qemu-img create -f qcow2 backup-sda.qcow2 2097152B && nbdcopy -p 'nbd+unix:///sda?socket=/var/tmp/vircpt.12377' -- [ qemu-nbd -f qcow2 backup-sda.qcow2 ]
```

## Boot the system from a checkpoint

An exported checkpoint can also be booted, this is useful for things like:

 * Examining the virtual machine at a given state
 * Testing system updates without having to clone the complete virtual machine
 * Restoring files
 
Using an overlay image with the read only NBD backend, this will consume way
less disk space than a complete virtual machine clone.

1) Create an export for a created checkpoint (`bootme`):

```
# vircpt -d vm4 export --name bootme
[..]
INFO root vircpt - showcmd: Socket for exported checkpoint: [/var/tmp/vircpt.12780]
[..]
```

1) Map the checkpoint to an qcow overlay image:

```
# qemu-img create -F raw -b nbd+unix:///sda?socket=/var/tmp/vircpt.12780 -f qcow2 /tmp/image_sda.qcow2
```

2) Boot the image using qemu (or as alternative, create a new libvirt virtual
   machine config and attach the created overlay image):

```
# qemu-system-<arch> -hda /tmp/image_sda.qcow2 -m 2500 --enable-kvm
```

## Agentless clamav or other anti virus engines

You can attach or mount the created NBD export and execute anti virus
engines without having to install the engine in the virtual machine
itself.

# Requirements

 * libvirt / qemu versions with checkpoint support
 * virtual machine must have qcow v3 versioned images with persistent bitmap
   support.
 * libnbd executables (nbdinfo, nbdcopy)
 * python modules: python3-rich, python3-lxml

# TODO / Ideas

Add "hotadd" option which allows to attach the data from the NBD export
to other virtual machines, for:

 * backup operations
 * antivirus scan via clamav?
