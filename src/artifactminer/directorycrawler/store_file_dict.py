#static dictionary responsible for storing validated files (FOR CRAWLER ONLY NOT LLM)
#the dictionary will eventually be sent to llm for further analysis
#TODO use json instead? dictionary should be good for now

class StoreFileDict:
    _instance = None  # Singleton instance

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(StoreFileDict, cls).__new__(cls)
            cls._instance.file_dict = {}  # Initialize dictionary
        return cls._instance

    def add_to_dict(self, key, value): #add to dictionary
        self.file_dict[key] = value

    def remove_from_dict(self, key): #remove from dictionary
        if key in self.file_dict:
            del self.file_dict[key]

    def get_dict(self, key): #get value from dictionary
        return self.file_dict[key]

    def get_dict_len(self):
        return len(self.file_dict)
    
    def remove_all_dict(self):
        self.file_dict.clear()





 