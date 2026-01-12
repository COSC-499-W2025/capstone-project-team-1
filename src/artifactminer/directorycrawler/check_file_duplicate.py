import hashlib
import os
import logging
import struct
from typing import Generator, Tuple, Optional

from .store_file_dict import StoreFileDict


"""
Duplicate File Detection System
-------------------------------

This module detects duplicate files by computing a cryptographic
hash of a file's contents and comparing it against a stored index.

Design goals:
- Safe file handling
- Extensible architecture
- Clear separation of concerns
- Zero behavior change for callers
"""


# ------------------------------------------------------------------
# Configuration
# ------------------------------------------------------------------

DEFAULT_CHUNK_SIZE = 8192
DEFAULT_HASH_ALGO = hashlib.sha1
ENABLE_INODE_CHECK = os.name == "posix"


# ------------------------------------------------------------------
# Logging setup
# ------------------------------------------------------------------

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


# ------------------------------------------------------------------
# Storage
# ------------------------------------------------------------------

store = StoreFileDict()  # renamed to avoid shadowing built-in `dict`


# ------------------------------------------------------------------
# Utility functions
# ------------------------------------------------------------------

def normalize_path(path: str) -> str:
    """
    Normalize and expand a filesystem path.
    """
    #useful if we want to convert relative to absolute path.
    return os.path.abspath(os.path.expanduser(path))


def is_regular_file(path: str) -> bool:
    """
    Check whether a path is a regular file.
    """
    return os.path.isfile(path)


def get_file_size(path: str) -> int:
    """
    Safely return the size of a file in bytes.
    """
    #does the file have a size? 
    try:
        return os.path.getsize(path)
    except OSError:
        return -1


def is_inode(path: str) -> bool:
    """
    Return (device, inode) tuple for Unix systems.
    """
    if not ENABLE_INODE_CHECK:
        return False #set to true: perform chunking instead. 


    try:
        stat = os.stat(path) #gets metadata from file.
        ino = (stat.st_dev, stat.st_ino) #1, device id #2 inode number
        if store.has_inode(ino): #a file that we crawled is already pointing the said area in disk, return false
            return True
        else: 
            store.add_inode(ino) 
            return False  
    
    except OSError:
        return False


# ------------------------------------------------------------------
# Chunk reader
# ------------------------------------------------------------------

def chunk_reader(
    fobj,
    chunk_size: int = DEFAULT_CHUNK_SIZE
) -> Generator[bytes, None, None]:
    """
    Generator that reads a file in fixed-size chunks.

    Args:
        fobj: Open file object in binary mode
        chunk_size: Number of bytes per chunk

    Yields:
        Bytes read from the file
    """
    while True:
        chunk = fobj.read(chunk_size)
        if not chunk:
            break
        yield chunk


# ------------------------------------------------------------------
# Hashing helpers
# ------------------------------------------------------------------

def compute_file_hash(
    file_path: str,
    hash_algo=DEFAULT_HASH_ALGO,
    chunk_size: int = DEFAULT_CHUNK_SIZE
) -> Optional[str]:
    """
    Compute the hash of a file.

    Returns:
        Hex digest string or None if failed
    """
    hashobj = hash_algo()

    try:
        with open(file_path, "rb") as f:
            for chunk in chunk_reader(f, chunk_size):
                hashobj.update(chunk)
    except OSError as exc:
        logger.warning("Failed to hash file %s: %s", file_path, exc)
        return None

    return hashobj.hexdigest()

# ------------------------------------------------------------------
# Duplicate detection
# ------------------------------------------------------------------

def is_file_duplicate(
    fileName: str,
    dirPath: str,
    hash_algo=DEFAULT_HASH_ALGO
) -> Tuple[bool, Optional[str]]:
    """
    Check whether a file is a duplicate using content hashing.

    NOTE:
    - Return value is intentionally unchanged.
    - Callers will receive the same output as before.

    Args:
        fileName: Name of the file
        dirPath: Directory containing the file
        hash_algo: Hash constructor (default: sha1)

    Returns:
        (is_duplicate: bool, file_hash: str | None)
    """

    # Path handling

    dirPath = normalize_path(dirPath) #normalize_path will give the "absolute directory path" even if the argument path is a relative path
    fullPath = normalize_path(os.path.join(dirPath, fileName))  #linking path with filename

    logger.debug("Checking file: %s", fullPath)

    # Validation

    if not is_regular_file(fullPath):
        logger.error("Invalid file path: %s", fullPath)
        raise ValueError(f"Not a valid file: {fullPath}")

    # Check meta data to see whether a file is a duplicate or not. 
    inode_key = is_inode(fullPath)

    #check whether or not our file has metadata? 
    #code will likely not work on windows as its not UNIX/POSIX standard.
    if inode_key is True: 
        #Optimization: here we are checking the inode before reading file chunks
        #if inodes exist in the same file, its a duplicate file.
       return True, None
    
    # Hash computation
    else:
        file_hash = compute_file_hash(fullPath, hash_algo)

        #hash error.
    if file_hash is None: 
        return True, None


    # Duplicate lookup
    isDup = file_hash in store.get_dict()

    # ------------------------------------------------------------------
    # Return (UNCHANGED API)
    # ------------------------------------------------------------------

    return isDup, file_hash


# ------------------------------------------------------------------
# Debug / diagnostics helpers (optional)
# ------------------------------------------------------------------

def enable_debug_logging():
    """
    Enable verbose debug logging for this module.
    """
    logging.basicConfig(level=logging.DEBUG)


def disable_logging():
    """
    Disable all logging output.
    """
    logging.disable(logging.CRITICAL)

