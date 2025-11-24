import hashlib
import os

from .store_file_dict import StoreFileDict

'''
This system will take a file from .
'''
dict = StoreFileDict()

def chunk_reader(fobj, chunk_size=1024):
    """Generator that reads a file in chunks of bytes"""
    while True:
        chunk = fobj.read(chunk_size)
        if not chunk:
            return
        yield chunk

def is_file_duplicate(fileName, dirPath, hash=hashlib.sha1):
    hashobj = hash()
    fullPath = os.path.join(dirPath, fileName)
    for chunck in chunk_reader(open(fullPath, 'rb')):
        hashobj.update(chunck)
    file_id = (hashobj.digest(), os.path.getsize(fullPath))
    duplicate = dict.get_dict(file_id)
    if duplicate:
        return True, None
    
    return False, file_id

    
    