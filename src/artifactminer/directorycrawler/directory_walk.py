import os

#change this for a path that you choose
CURRENTPATH = "/Users/nathanhelm/Code/Projects/capstone/capstone-project-team-1/tests/directorycrawlertest/mocks/mockdirectory_zip.zip"

from .store_file_dict import StoreFileDict

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
                print_files(file) #print files
                full_path = os.path.join(root, file)
                if file != ".DS_Store": #continue the trend of checking filename later
                    store_file_dictionary.add_to_dict(file, full_path) #key = filename, path = filepath
                


def print_files(file):

    print("\n>", file)


simple_directory_crawl()