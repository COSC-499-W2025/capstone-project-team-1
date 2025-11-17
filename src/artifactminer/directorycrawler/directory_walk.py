import os
import re
from pathlib import Path
'''
in mock folder there are 4 readable filetypes

'''

#change this for a path that you choose
root = Path(__file__).resolve() #get current file path
project = root.parents[3] #gets project folder (../../../)
MOCKNAME = "mockdirectory"
CURRENTPATH = mock_dir = project / "tests" / "directorycrawler" / "mocks" / MOCKNAME #get mock directory path

from .store_file_dict import StoreFileDict
from .check_file_duplicate import is_file_duplicate

readableFileTypes = [] #TODO

ignoredFileNames = [] #file name not file extension
ignoredExtensions = [ #current list of file types that shouldn't be read. unless user config says otherwise...
    ".gitignore",".log", ".toml", ".exe", ".dll", ".bin", ".o", ".so",
    ".tar", ".tar.gz", ".rar", ".7z",".bmp", ".tiff",
    ".mp3", ".wav", ".flac", ".ogg", ".mp4", ".mkv", ".avi",
    ".sqlite", ".db", ".mdb", ".cache", ".pyc", ".class", ".jar",
    ".DS_Store", ".tmp", ".swp", ".swo", ".lock", ".bak"
    ]

#USER INFORMATION: 
userExcludeFileName = []    #["excluded_file.py"] #user's file that will be excluded
userKeepFileName = []    #["include_file.log"] #even though its 'log' the user has specifically asked us to use it

userExcludeFileExtension = [] #user file extension that will be excluded
userIncludeFileExtension = [] #user file extension that will be included 

userIncludeAllFiles = False 

store_file_dictionary = StoreFileDict()
#storing files from mock folder to dictionary
def crawl_directory(): 
    if os.path.exists(CURRENTPATH) == False:
        print("path does not exist")
        return

    for (root,dirs,files) in os.walk(CURRENTPATH, topdown=True):
        if(files):
            current_folder = os.path.basename(root)
            print("\n======================= GETTING FILES FROM FOLDER ", current_folder , " ======================================")
            for file in files: 
               
                full_path = os.path.join(root, file)
                if file in userExcludeFileName or get_extension(file) in userExcludeFileExtension: #user 
                    print("the file the user has excluded: ", file)
                    continue
                if file not in userKeepFileName and get_extension(file) not in userIncludeFileExtension: #if file in user file name skip other functions
                    if is_file_readable(full_path) == False: #check whether filename is even readible
                        print("file name: ", file, " is not readable")
                        continue
                    if is_file_ignored(file) == False: #check whether filename is valid
                        print("file name: ", file ," is ignored")
                        continue
                else:
                    print("the file the user has included: ", file)
                print_files(file) #print files

                if(is_file_duplicate(file, dirs)):
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
    #If readableFileTypes is not empty, enforce filter
    if readableFileTypes and ext.lower() not in readableFileTypes:
        return False
    return True
def get_extension(fileName) -> str:
    temp = fileName.rfind('.')
    if(temp != -1):
        return fileName[temp:]
    else:
        return "none"

def is_extension(fileName) -> bool:
    if fileName.startswith("*."):
        return True
    return False
def is_valid_filename(filename: str) -> bool: #is the typed out file even a file? 
    # Disallow empty or too-long filenames
    if not filename or len(filename) > 255:
        return False
    invalid_chars = r'[<>:"/\\|?*\x00-\x1F]' #chatgbt generated
    if re.search(invalid_chars, filename):
        return False
    # Disallow reserved Windows names (case-insensitive) TODO  --> check if OS is windows only
    reserved_names = {
        "CON", "PRN", "AUX", "NUL",
        *(f"COM{i}" for i in range(1, 10)),
        *(f"LPT{i}" for i in range(1, 10)),
    }
    if os.path.splitext(filename)[0].upper() in reserved_names:
        return False

    return True 

def update_path():
    global CURRENTPATH
    CURRENTPATH = mock_dir = project / "tests" / "directorycrawler" / "mocks" / MOCKNAME #get mock directory path

#USER FUNCTIONS============================
def user_keep_file(fileName):
    userKeepFileName.append(fileName)

def user_exclude_file(fileName):
    userExcludeFileName.append(fileName)

def user_keep_extension(exName):
    userIncludeFileExtension.append(exName)

def user_exclude_extension(exName):
    userExcludeFileExtension.append(exName)
#==========================================
def print_files(file):
    print("\n>",file)

#crawl_directory()