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
INFO lib common - printVersion [MainThread]: Version: 0.1 Arguments: ./vircpt -d vm1 create --name foo
INFO root vircpt - main [MainThread]: Libvirt library version: [9000000]
INFO root disktype - Optical [MainThread]: Skipping attached [cdrom] device: [sdb].
INFO root disktype - Optical [MainThread]: Skipping attached [floppy] device: [fda].
WARNING fs fs - freeze [MainThread]: Guest agent is not responding: QEMU guest agent is not connected
INFO root vircpt - main [MainThread]: Finished successfully
```

## List checkpoints

In order to view existing checkpoints, use:

```
# vircpt -d vm1 list
INFO lib common - printVersion [MainThread]: Version: 0.1 Arguments: ./vircpt -d vm1 list
INFO root vircpt - main [MainThread]: Libvirt library version: [9000000]
INFO root disktype - Optical [MainThread]: Skipping attached [cdrom] device: [sdb].
INFO root disktype - Optical [MainThread]: Skipping attached [floppy] device: [fda].
INFO root vircpt - main [MainThread]: List of existing checkpoints:
INFO root checkpoint - show [MainThread]:  + foo
INFO root vircpt - main [MainThread]: Finished successfully
```

## Start NBD export for a specific checkpoint

To access the virtual machine checkpoint data, use the export
parameter:

```
# vircpt -d vm1 export --name foo
INFO lib common - printVersion [MainThread]: Version: 0.1 Arguments: ./vircpt -d vm1 export --name foo
INFO root vircpt - main [MainThread]: Libvirt library version: [9000000]
INFO root disktype - Optical [MainThread]: Skipping attached [cdrom] device: [sdb].
INFO root disktype - Optical [MainThread]: Skipping attached [floppy] device: [fda].
INFO root vircpt - main [MainThread]: Socket for exported checkpoint: [/var/tmp/vircpt.199988]
INFO root vircpt - main [MainThread]: [nbdinfo 'nbd+unix:///?socket=/var/tmp/vircpt.199988' --list]
INFO root vircpt - main [MainThread]: Finished successfully
```

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
