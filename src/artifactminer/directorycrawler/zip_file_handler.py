import zipfile

def process_zip(filePath: str, verbose: bool = False):
    if not zipfile.is_zipfile(filePath):
        print("Selected file is not a valid zipfile.") # we should presumably be using a more sophisticated method of error handling?
        return
    try:
        with zipfile.ZipFile(filePath, 'r') as zip_ref:
            if zip_ref.testzip() != None:
                print("Zip contains malformed file: "+zip_ref.testzip())
                return
            
            zipped_files = zip_ref.infolist()
            if verbose:
                for file in zipped_files:
                    if not file.is_dir():
                        print(file.filename)
            return (zip_ref, zipped_files) # returns the contents of the zip and basic metadata on each file contained within the zip.
            # zipped files can be later opened by calling zip_ref.open(zipped_file[N].filename where N is the index of file to be opened.  
    
    except zipfile.BadZipFile:
        print("Selected zipfile is improper.")
        return
    except zipfile.LargeZipFile:
        print("Selected zipfile is too large.")
    

