#The main goal of this file is to achieve full file analysis given a path to a file
# This would mean being able to analyze a PDF for example for any essential information 
# that could be used in a resume. Primarily done using already made AI analysis functions, but
# also using basic string matching in order to comply with non-AI file analysis.

# We would call the 
import os
import zipfile
from pypdf import PdfReader
from artifactminer.directorycrawler.directory_walk import *
from artifactminer.RepositoryIntelligence.repo_intelligence_AI import user_allows_llm, getLLMResponse
from pathlib import Path



async def analyze_file(file_path):
    # Placeholder for file analysis logic
    # This could involve AI-based analysis or simple string matching
    get_extension = file_path.split('.')[-1].lower()
    if(get_extension == "pdf"):
        print(f"Analyzing file: {file_path}")
        return await analyze_pdf(file_path)

    return None

async def analyze_pdf(file_path):
    # Placeholder for PDF analysis logic
    print(f"Performing PDF analysis on: {file_path}")
    if(user_allows_llm()):
        prompt = f"Analyze the following PDF file and extract key information relevant for a resume:\n"
        prompt += extract_text_from_pdf(file_path)
        response = await getLLMResponse(prompt)
        return response
    else:
        print("User has not consented to LLM usage. Performing basic analysis.")
        
   
    return f"Basic analysis of PDF file at {file_path} completed."

def extract_text_from_pdf(file_path):
    text = ""
    try:
        with open(file_path, 'rb') as file:
            reader = PdfReader(file)
            for page in reader.pages:
                text += page.extract_text() + "\n"
    except Exception as e:
        print(f"Error extracting text from PDF: {e}")
    return text