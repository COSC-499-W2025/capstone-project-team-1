class FileValues:
    def __init__(self, fileName, filePath):
        self.fileName = fileName
        self.filePath = filePath

    def get_file_name(self):
        return self.fileName
    def get_file_absolutePath(self):
        return self.filePath
    
