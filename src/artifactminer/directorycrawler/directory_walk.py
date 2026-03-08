import copy
import os
import re
from pathlib import Path
from .store_file_dict import StoreFileDict
from .check_file_duplicate import is_file_duplicate

root = Path(__file__).resolve()
project = root.parents[3] #gets project folder (../../../)

MOCKNAME = "mockdirectory"
CURRENTPATH = mock_dir = project / "tests" / "directorycrawler" / "mocks" / MOCKNAME

ignoredFileNames = []
READABLE_EXTENSIONS = {
     # --- Documents / PDFs ---
    ".pdf",
    ".xps",
    ".djvu",
    ".epub",
    ".mobi",
    ".azw",
    ".azw3",
    ".cbz",
    ".cbr",

    # --- Microsoft Office ---
    ".doc",
    ".docx",
    ".dot",
    ".dotx",
    ".xls",
    ".xlsx",
    ".xlsm",
    ".xltx",
    ".ppt",
    ".pptx",
    ".pps",
    ".ppsx",
    ".vsd",
    ".vsdx",
    ".msg",
    ".one",
    ".onepkg",

    # --- OpenOffice / LibreOffice ---
    ".odt",
    ".ods",
    ".odp",
    ".odg",
    ".odf",
    ".odb",

    # --- Images (raster) ---
    ".png",
    ".jpg",
    ".jpeg",
    ".jpe",
    ".gif",
    ".bmp",
    ".tiff",
    ".tif",
    ".webp",
    ".avif",
    ".heic",
    ".heif",
    ".ico",
    ".cur",
    ".psd",
    ".xcf",
    ".kra",
    ".ora",
    ".raw",
    ".nef",
    ".cr2",
    ".arw",
    ".dng",

    # --- Images (vector) ---
    ".ai",
    ".eps",
    ".cdr",
    ".sketch",
    ".fig",
    ".xd",

    # --- Audio ---
    ".mp3",
    ".wav",
    ".ogg",
    ".oga",
    ".flac",
    ".aac",
    ".m4a",
    ".wma",
    ".aiff",
    ".alac",
    ".opus",
    ".amr",
    ".mid",
    ".midi",

    # --- Video ---
    ".mp4",
    ".m4v",
    ".mov",
    ".avi",
    ".mkv",
    ".webm",
    ".wmv",
    ".flv",
    ".f4v",
    ".mpeg",
    ".mpg",
    ".3gp",
    ".3g2",
    ".ogv",
    ".rm",
    ".rmvb",
    ".vob",

    # --- Archives / compression ---
    ".zip",
    ".tar",
    ".gz",
    ".tgz",
    ".bz2",
    ".xz",
    ".lz",
    ".lzma",
    ".7z",
    ".rar",
    ".zst",
    ".cab",
    ".iso",
    ".img",
    ".dmg",
    ".pkg",
    ".deb",
    ".rpm",
    ".apk",
    ".ipa",
    ".appimage",

    # --- Fonts ---
    ".ttf",
    ".otf",
    ".woff",
    ".woff2",
    ".eot",
    ".pfb",
    ".pfm",

    # --- 3D / CAD / modeling ---
    ".obj",
    ".fbx",
    ".stl",
    ".dae",
    ".3ds",
    ".blend",
    ".usd",
    ".usdz",
    ".gltf",
    ".glb",
    ".step",
    ".stp",
    ".iges",
    ".igs",
    ".dwg",
    ".dxf",
    ".skp",

    # --- Scientific / binary data ---
    ".h5",
    ".hdf5",
    ".hdf",
    ".npz",
    ".npy",
    ".pickle",
    ".pkl",
    ".feather",
    ".arrow",
    ".orc",
    ".sav",
    ".dta",

    # --- Databases ---
    ".db",
    ".sqlite",
    ".sqlite3",
    ".mdb",
    ".accdb",
    ".frm",
    ".ibd",
    ".dbf",

    # --- Executables / binaries (detect only) ---
    ".exe",
    ".dll",
    ".so",
    ".dylib",
    ".bin",
    ".elf",
    ".o",
    ".a",
    ".lib",
    ".class",
    ".jar",
    ".war",
    ".ear",

    # --- Virtual machines / containers ---
    ".vmdk",
    ".vdi",
    ".qcow",
    ".qcow2",
    ".ova",
    ".ovf",

    # --- Game assets ---
    ".pak",
    ".wad",
    ".unitypackage",
    ".assetbundle",
    ".uasset",
    ".umap",
    ".sav",
    ".rom",

    # --- Design / publishing ---
    ".indd",
    ".idml",
    ".qxp",
    ".afdesign",
    ".afphoto",
    ".afpub",

    # --- Email / messaging ---
    ".eml",
    ".pst",
    ".ost",
    ".mbox",

    # --- Misc binary ---
    ".dat",
    ".blob",
    ".cache",
    ".idx",
    ".pak",
    ".img",
    ".bak",
    ".tmp",

      # --- Core programming languages ---
    ".py", ".pyw", ".pyi",
    ".js", ".mjs", ".cjs",
    ".ts", ".tsx",
    ".java", ".kt", ".kts",
    ".c", ".h",
    ".cpp", ".hpp", ".cc", ".hh", ".cxx", ".hxx",
    ".cs",
    ".go",
    ".rs",
    ".swift",
    ".scala",
    ".rb",
    ".php",
    ".lua",
    ".r",
    ".jl",
    ".dart",
    ".groovy",
    ".nim",
    ".zig",
    ".vala",
    ".cr",
    ".d",
    ".f90", ".f95", ".for",
    ".pas", ".p",
    ".ada", ".adb", ".ads",
    ".lisp", ".cl", ".el",
    ".scm",
    ".hs",
    ".ml", ".mli",
    ".ex", ".exs",
    ".erl", ".hrl",
    ".vb",
    ".vbs",
    ".asm", ".s",

    # --- Shell & scripting ---
    ".sh", ".bash", ".zsh", ".fish",
    ".ps1", ".psm1",
    ".bat", ".cmd",
    ".awk",
    ".sed",
    ".tcl",

    # --- Web / frontend ---
    ".html", ".htm",
    ".xhtml",
    ".css",
    ".scss", ".sass", ".less",
    ".svg",
    ".vue",
    ".svelte",
    ".astro",
    ".jsx",

    # --- Data / serialization ---
    ".json",
    ".json5",
    ".geojson",
    ".ndjson",
    ".yaml", ".yml",
    ".toml",
    ".ini",
    ".cfg",
    ".conf",
    ".properties",
    ".env",
    ".csv",
    ".tsv",
    ".psv",
    ".xml",
    ".xsd",
    ".xsl",
    ".rdf",
    ".ttl",
    ".n3",
    ".sql",
    ".ddl",

    # --- Documentation / markup ---
    ".md",
    ".markdown",
    ".mdx",
    ".rst",
    ".txt",
    ".tex",
    ".latex",
    ".adoc",
    ".asciidoc",
    ".org",
    ".wiki",
    ".pod",
    ".man",

    # --- Notebooks ---
    ".ipynb",
    ".rmd",
    ".qmd",
    ".nbs",

    # --- Build systems ---
    ".make",
    "Makefile",
    ".mk",
    ".gradle",
    ".pom",
    ".bazel",
    ".bzl",
    ".buck",
    ".ninja",
    ".cmake",
    "CMakeLists.txt",

    # --- CI / CD ---
    ".yml.j2",
    ".yaml.j2",
    ".gitlab-ci.yml",
    ".github",
    ".circleci",
    ".travis.yml",
    ".jenkinsfile",
    "Jenkinsfile",

    # --- Containers / infra ---
    "Dockerfile",
    ".dockerignore",
    ".compose",
    ".tf",
    ".tfvars",
    ".hcl",
    ".nomad",
    ".vault",
    ".helm",
    ".chart",
    ".k8s",
    ".kube",
    ".yaml.tpl",

    # --- Package managers ---
    "package.json",
    "package-lock.json",
    "pnpm-lock.yaml",
    "yarn.lock",
    "Pipfile",
    "Pipfile.lock",
    "poetry.lock",
    "pyproject.toml",
    "requirements.txt",
    "setup.py",
    "setup.cfg",
    "Cargo.toml",
    "Cargo.lock",
    "go.mod",
    "go.sum",
    "composer.json",
    "composer.lock",
    "Gemfile",
    "Gemfile.lock",

    # --- Linting / formatting ---
    ".editorconfig",
    ".eslintrc",
    ".prettierrc",
    ".stylelintrc",
    ".flake8",
    ".pylintrc",
    ".ruff.toml",
    ".clang-format",
    ".clang-tidy",
    ".black",
    ".isort.cfg",

    # --- IDE / tooling ---
    ".vscode",
    ".idea",
    ".iml",
    ".project",
    ".classpath",

    # --- Game / graphics / shaders ---
    ".shader",
    ".glsl",
    ".hlsl",
    ".cg",
    ".unity",
    ".prefab",
    ".scene",
    ".godot",
    ".tres",
    ".tscn",

    # --- Scientific / data analysis ---
    ".mat",
    ".sas",
    ".stata",
    ".do",
    ".spss",
    ".arff",
    ".netcdf",
    ".nc",
    ".parquet",
    ".avro",
    # --- Misc readable formats ---
    ".diff",
    ".patch",
    ".rej",
    ".lock",
    ".example",
    ".template",
    ".tmpl",
    ".j2",
    ".mustache",
    ".handlebars",
    ".hbs",
    ".liquid",
    ".ejs",
    ".njk",
    ".haml",
    ".pug",

    # --- Security / policies ---
    ".pem",
    ".crt",
    ".cer",
    ".csr",
    ".key",
    ".asc",
    ".gpg",
    ".sig",

    # --- API / specs ---
    ".openapi",
    ".swagger",
    ".raml",
    ".apib",
    ".proto",
    ".thrift",
    ".graphql",

    # --- Misc code-adjacent ---
    ".rego",
    ".cue",
    ".vcl",
    ".sol",
    ".vy",
    ".move",
    ".circom",
    ".zk",
}

#USER INFORMATION:
userExcludeFileName = []
userKeepFileName = []
userExcludeFileExtension = []
userIncludeFileExtension = []
userIncludeAllFiles = False 

store_file_dictionary = StoreFileDict()

def crawl_directory(refresh_dict=True) -> tuple[dict, list[str]]:
    """Crawl directory for files and return file dict and directory list."""
    listforalldirs = []
    if not os.path.exists(CURRENTPATH):
        print("path does not exist")
        return {}, []

    for (root,dirs,files) in os.walk(CURRENTPATH, topdown=True):
        for single_directory in dirs:
            # Include full relative path for each directory
            full_dir_path = os.path.join(root, single_directory)
            rel_dir_path = os.path.relpath(full_dir_path, CURRENTPATH)
            listforalldirs.append(rel_dir_path)
        if files:
            current_folder = os.path.basename(root)
            print(
                f"\n======================= GETTING FILES FROM FOLDER {current_folder} ======================================"
            )
            for file in files:
                full_path = os.path.join(root, file)
                if file in userExcludeFileName or get_extension(file) in userExcludeFileExtension:
                    print("the file the user has excluded: ", file)
                    continue
                if file not in userKeepFileName and get_extension(file) not in userIncludeFileExtension:
                    if not is_file_readable(full_path):
                        print("file name: ", file, " is not readable")
                        continue
                    if not is_file_ignored(file):
                        print("file name: ", file, " is ignored")
                        continue
                else:
                    print("the file the user has included: ", file)

                print_files(file)
                isDuplicate, fileId = is_file_duplicate(file, root)
                extension = "extension error"
                if get_extension(full_path) not in "none":
                    extension = get_extension(full_path)
                if not isDuplicate:
                    store_file_dictionary.add_to_dict(fileId, (file, full_path, extension))

    values = copy.deepcopy(store_file_dictionary.get_dict())
    if refresh_dict:
        store_file_dictionary.remove_all_dict()


    return values, listforalldirs


def crawl_multiple_directories(paths: list[str | Path]) -> tuple[dict, list[str]]:
    """
    Crawl multiple directories and merge the results.
    
    Used for incremental portfolio uploads where multiple ZIPs contribute
    to the same portfolio analysis.
    
    Args:
        paths: List of directory paths to crawl
        
    Returns:
        Tuple of (merged file dict, merged directory list)
    """
    merged_dirs = []
    if not paths:
        return {}, []

    for path in paths:
        global CURRENTPATH
        CURRENTPATH = path
        crawl_payload = crawl_directory(False)
        all_dirs = crawl_payload[1]
        for dir in all_dirs:
            merged_dirs.append(dir)

    all_file_values = copy.deepcopy(store_file_dictionary.get_dict())
    store_file_dictionary.remove_all_dict()
    return all_file_values, merged_dirs 


def is_file_readable(full_path: str) -> bool:
    if not os.path.isfile(full_path):
        return False
    if not os.access(full_path, os.R_OK):
        return False
    if os.path.getsize(full_path) == 0:
        return False
    return True 

def is_file_ignored(file_name: str) -> bool:
    if file_name in ignoredFileNames:
        return False
    if file_name.startswith(".") and file_name.lower() not in READABLE_EXTENSIONS:
        return False
    _, ext = os.path.splitext(file_name)
    if ext.lower() not in READABLE_EXTENSIONS:
        return False
    return True
def get_extension(fileName) -> str:
    temp = fileName.rfind('.')
    if temp != -1:
        return fileName[temp:]
    return "none"
def is_extension(fileName) -> bool:
    if fileName.startswith("*."):
        return True
    return False
def is_valid_filename(filename: str) -> bool:
    if not filename or len(filename) > 255:
        return False
    invalid_chars = r'[<>:"/\\|?*\x00-\x1F]'
    if re.search(invalid_chars, filename):
        return False
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

def user_keep_file(fileName):
    userKeepFileName.append(fileName)


def user_exclude_file(fileName):
    userExcludeFileName.append(fileName)


def user_keep_extension(exName):
    userIncludeFileExtension.append(exName)


def user_exclude_extension(exName):
    userExcludeFileExtension.append(exName)


def print_files(file):
    print(f"\n> {file}")

def print_values_in_dict():
    print("here are the files in the dictionary: \n")
    print(store_file_dictionary.get_values())

