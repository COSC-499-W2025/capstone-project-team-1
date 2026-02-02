#The main goal of this file is to achieve full file analysis given a path to a file
# This would mean being able to analyze a PDF for example for any essential information 
# that could be used in a resume. Primarily done using already made AI analysis functions, but
# also using basic string matching in order to comply with non-AI file analysis.

# We would call the 
from pathlib import Path
from pypdf import PdfReader
from artifactminer.RepositoryIntelligence.repo_intelligence_AI import user_allows_llm, getLLMResponse
from artifactminer.api.crawler import get_crawler_contents

from artifactminer.api.schemas import CrawlerFiles, FileValues


#CRAWLER INTEGRATION
async def get_crawler_pdf_contents(zip_id : int) -> list[FileValues]:
    
    response = None
    fileValues = None
    try:
        response = await get_crawler_contents(zip_id=zip_id)
    except:
        print("something went wrong getting zip contents")
        response = CrawlerFiles(zip_id, list[FileValues])
        fileValues = response.crawl_path_and_file_name_and_ext

    if fileValues is None:
        return None
    if len(fileValues) < 0: 
        return None
    
    fileValues = response.crawl_path_and_file_name_and_ext

    for file_data in fileValues:
        if file_data.file_ext == ".pdf":
            analyze_pdf(file_path=file_data.file_path) #get relative path

    return fileValues

"""
Evan's previous code: 
async def analyze_file(file_path):
    # Placeholder for file analysis logic
    # This could involve AI-based analysis or simple string matching
    get_extension = file_path.split('.')[-1].lower()
    if(get_extension == "pdf"):
        print(f"Analyzing file: {file_path}")
        return await analyze_pdf(file_path)

    return None
"""

async def analyze_pdf(file_path):
    """
    Analyze a PDF file, detecting if it's a resume and extracting relevant information.
    
    Args:
        file_path: Path to the PDF file to analyze
        
    Returns:
        Analysis results as a string or dict
    """
    print(f"Performing PDF analysis on: {file_path}")
    
    # Extract text from the PDF
    text = extract_text_from_pdf(file_path)
    
    # Check if this PDF appears to be a resume
    resume_keywords = ["experience", "education", "skills", "projects", "work history"]
    is_resume = any(keyword in text.lower() for keyword in resume_keywords)
    
    if is_resume:
        print(f"Detected resume in: {file_path}")
    
    if user_allows_llm():
        # Customize prompt based on whether it's a resume
        if is_resume:
            prompt = (
                "Analyze the following resume PDF and extract key information. "
                "Focus on: work experience, education, technical skills, projects, and achievements. "
                "Format the output in a structured way suitable for portfolio analysis:\n\n"
            )
        else:
            prompt = "Analyze the following PDF file and extract key information relevant for a resume:\n\n"
        
        prompt += text
        response = await getLLMResponse(prompt)
        return response
    else:
        print("User has not consented to LLM usage. Performing basic analysis.")
        
        # Basic non-LLM analysis
        if is_resume:
            return {
                "type": "resume",
                "file_path": file_path,
                "detected_keywords": [kw for kw in resume_keywords if kw in text.lower()],
                "text_preview": text[:500] + "..." if len(text) > 500 else text
            }
   
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