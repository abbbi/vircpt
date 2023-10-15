<!-- START doctoc generated TOC please keep comment here to allow auto update -->
<!-- DON'T EDIT THIS SECTION, INSTEAD RE-RUN doctoc TO UPDATE -->
**Table of Contents**

- [vircpt](#vircpt)
- [About](#about)
- [Examples](#examples)
  - [Creating an checkpoint](#creating-an-checkpoint)
  - [List checkpoints](#list-checkpoints)
  - [Start NBD export for a specific checkpoint](#start-nbd-export-for-a-specific-checkpoint)
  - [Release an export](#release-an-export)
  - [Removing checkpoints](#removing-checkpoints)
- [Filesystem Consistency](#filesystem-consistency)
- [TODO / Ideas](#todo--ideas)

<!-- END doctoc generated TOC please keep comment here to allow auto update -->

# vircpt

Libvirt checkpoint swiss army knife.

# About

`vircpt` can be used to manage libvirt virtual domain checkpoints, as in:

 * create checkpoints
 * delete checkpoints
 * list checkpoints
 * export checkpoints via NBD server backend

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

To access the virtual machine checkpoint data, use the export
parameter:

```
# vircpt -d vm1 export --name foo
INFO lib common - printVersion: Version: 0.1 Arguments: ./vircpt -d vm1 export --name export
INFO root vircpt - main: Libvirt library version: [9000000]
INFO root disktype - Optical: Skipping attached [cdrom] device: [sdb].
INFO root disktype - Optical: Skipping attached [floppy] device: [fda].
INFO root vircpt - main: Socket for exported checkpoint: [/var/tmp/vircpt.207990]
INFO root vircpt - main: -----------------------------------
INFO root vircpt - main: Useful commands:
INFO root vircpt - main: -----------------------------------
INFO root vircpt - main: [nbdinfo 'nbd+unix:///?socket=/var/tmp/vircpt.207990' --list]
INFO root vircpt - main: Disk: sda
INFO root vircpt - main:  [qemu-img create -F raw -b nbd+unix:///sda?socket=/var/tmp/vircpt.207990 -f qcow2 /tmp/image_sda.qcow2]
INFO root vircpt - main:  [qemu-nbd -c /dev/nbd0 /tmp/image_sda.qcow2]  && [virsh attach-disk tgtvm --source /dev/nbd0  --target vdX]
INFO root vircpt - main:  [qemu-nbd -c /dev/nbd0 'nbd+unix:///sda?socket=/var/tmp/vircpt.207990' -r] && [fdisk -l /dev/nbd0]
INFO root vircpt - main: -----------------------------------
INFO root vircpt - main: Finished successfully
```

The output will create some useful commands for operating on the created
NBD socket endpoint, such as:

 * Query info about exported devices
 * Create an overlay image with NBD socket backend (for direct boot)
 * Setup and NBD Device for the overlay image, which can then be attached
 to another virtual machine

This will create an unix socket endpoint which can then be accessed via other
qemu utilities or mapped to an qcow2 image via backing store option:

```
# nbdinfo 'nbd+unix:///?socket=/var/tmp/vircpt.199988' --list
protocol: newstyle-fixed without TLS, using structured packets
export="sda":
        export-size: 52428800 (50M)
        uri: nbd+unix:///sda?socket=/var/tmp/vircpt.199988
        contexts:
                base:allocation
                qemu:dirty-bitmap:backup-sda
        is_rotational: false
[..]
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

If reachable, `vircpt` will attempt to freeze the domains file systems
via Qemu agent.


# TODO / Ideas

Add "hotadd" option which allows to attach the data from the NBD export
to other virtual machines, for:

 * backup operations
 * antivirus scan via clamav?
