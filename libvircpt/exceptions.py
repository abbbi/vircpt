"""
    Exceptions
"""


class virtHelperError(Exception):
    """Errors during libvirt helper"""


class domainNotFound(virtHelperError):
    """Can't find domain"""


class connectionFailed(virtHelperError):
    """Can't connect libvirtd domain"""


class startBackupFailed(virtHelperError):
    """Can't start backup operation"""

class NoCheckpointsFound(virtHelperError):
    """foo"""

class CheckpointException(Exception):
    """Base checkpoint Exception"""


class RemoveCheckpointError(CheckpointException):
    """During removal of existing checkpoints after
    an error occurred"""


class BackupException(Exception):
    """Base backup Exception"""


class DiskBackupFailed(BackupException):
    """Backup of one disk failed"""


class DiskBackupWriterException(BackupException):
    """Opening the target file writer
    failed"""


class RestoreException(Exception):
    """Base restore Exception"""


class UntilCheckpointReached(RestoreException):
    """Base restore Exception"""


class RestoreError(RestoreException):
    """Base restore error Exception"""
