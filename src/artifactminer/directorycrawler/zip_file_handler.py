import zipfile

ZIPFILEPATH = "/Users/nathanhelm/Code/Projects/capstone/capstone-project-team-1/tests/directorycrawlertest/mocks/mockdirectory_zip.zip"
EXTRACTPATH = "" #TODO

with zipfile.ZipFile(ZIPFILEPATH, 'r') as zip_ref:
    
    print("unzipped files to be processed to os walk:")
    zip_ref.printdir()
    #later perform send content of zip using function below:
    #zipf.extractall("unzipped_folder")

    

