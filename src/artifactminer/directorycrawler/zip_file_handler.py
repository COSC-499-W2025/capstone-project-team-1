import zipfile

def process_zip(zip_path: str, verbose: bool = False):
    if not zipfile.is_zipfile(zip_path):
        raise ValueError("Selected file is not a valid zipfile.")
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
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
    except zipfile.BadZipFile as ziperror:
        raise ziperror
    except zipfile.LargeZipFile as ziperror:
        raise ziperror

def extract_directory_tree(zip_path: str)  -> list[str]:
    if not zipfile.is_zipfile(zip_path):
        raise ValueError("Selected file is not a valid zipfile.")
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            if zip_ref.testzip() != None:
                print("Zip contains malformed file: "+zip_ref.testzip())
                return
            zipPath = list(zipfile.Path(zip_ref).iterdir())[0]
            results = []
            for i in zipPath.iterdir():
                if i.is_dir(): 
                    results.append(i.name+"/")
        return results
    except zipfile.BadZipFile as ziperror:
        raise ziperror
    except zipfile.LargeZipFile as ziperror:
        raise ziperror

def extract_selected_to_temp(zip_path: str, selected_paths: list[str], temp_dir: str) -> dict[str, str]:
    if not zipfile.is_zipfile(zip_path):
        raise ValueError("Selected file is not a valid zipfile.")
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            if zip_ref.testzip() != None:
                print("Zip contains malformed file: "+zip_ref.testzip())
                return
            results = {}
            top = list(zipfile.Path(zip_ref).iterdir())[0].name
            for i in selected_paths:
                print(top+"/"+i)
                results[i] = zip_ref.extract(top+"/"+i, temp_dir)
        return results
    except zipfile.BadZipFile as ziperror:
        raise ziperror
    except zipfile.LargeZipFile as ziperror:
        raise ziperror