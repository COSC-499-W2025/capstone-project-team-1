from src.artifactminer.directorycrawler.directory_walk import crawl_directory
from src.artifactminer.directorycrawler.zip_file_handler import process_zip
#include



#data needed for demonstration
EMAIL = "" 
USERCONFIG_EXCLUDEFILE = ""
USERCONFIG_INCLUDEFILE = ""
ZIPPATH = ""



crawl_directory()
process_zip(ZIPPATH)


