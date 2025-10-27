import os
from pathlib import Path

#change this for a path that you choose
CURRENTPATH = "/Users/nathanhelm/Code/Projects/capstone/capstone-project-team-1/tests/directorycrawler/mocks/mockdirectory"

from .store_file_dict import StoreFileDict

readableFileTypes = []

ignoredFileNames = [".DS_Store"] #file name not file extension
ignoredExtensions = [".tmp", ".log", ".bak", ".gitignore"]

store_file_dictionary = StoreFileDict()
#storing files from mock folder to dictionary
def simple_directory_crawl(): 
    if os.path.exists(CURRENTPATH) == False:
        print("path does not exist")
        return

    for (root,dirs,files) in os.walk(CURRENTPATH, topdown=True):
        if(files):
            current_folder = os.path.basename(root)
            print("\n======================= GETTING FILES FROM FOLDER ", current_folder , " ======================================")
            for file in files: 
               
                full_path = os.path.join(root, file)
                if is_file_ignored(file) == False: #check whether filename is valid
                    print("file name: ", file ," is ignored")
                    continue
                if is_file_readable(full_path) == False:
                    print("file name: ", file, " is not readble")
                    continue
                print_files(file) #print files
                store_file_dictionary.add_to_dict(file, full_path) #key = filename, path = filepath
                
def is_file_readable(full_path: str) -> bool:
    #1- check if the file exists
    if not os.path.isfile(full_path):
        return False
    #2- checks that the path exists
    if not os.access(full_path, os.R_OK):
        return False
    #3- returns the size of a file in bytes
    if os.path.getsize(full_path) == 0:
        return False
    
    return True 

def is_file_ignored(file_name: str) -> bool:

    if file_name in ignoredFileNames:
        return False
    # Skip ignored extensions
    _, ext = os.path.splitext(file_name)
    if ext.lower() in ignoredExtensions:
        return False
    
    # Might add this filter for later.
    # If readableFileTypes is not empty, enforce filter
    #if readableFileTypes and ext.lower() not in readableFileTypes:
    #   return False
    return True




def print_files(file):

    print("\n>", file)


simple_directory_crawl()