import hashlib
import os

from .store_file_dict import store_file_dict

'''
This system will take a file from .
'''
dict = store_file_dict

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
    
    with open(fullPath, 'rb') as f:
        for chunk in chunk_reader(f):
            hashobj.update(chunk)

    file_hash = hashobj.hexdigest()
    
    isDup = file_hash in dict.get_dict()
    
    return isDup, file_hash 

    
    