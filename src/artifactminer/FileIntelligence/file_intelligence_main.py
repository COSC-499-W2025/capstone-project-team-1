#The main goal of this file is to achieve full file analysis given a path to a file
# This would mean being able to analyze a PDF for example for any essential information 
# that could be used in a resume. Primarily done using already made AI analysis functions, but
# also using basic string matching in order to comply with non-AI file analysis.


from pypdf import PdfReader

from artifactminer.RepositoryIntelligence.repo_intelligence_AI import user_allows_llm, getLLMResponse

from artifactminer.api.schemas import FileValues
 
#CRAWLER INTEGRATION
async def get_crawler_pdf_contents(file_values : list[FileValues]) -> str:
    

    if file_values is None:
        return "no response, file value is null."
    if len(file_values) < 0: 
        return "no response, file value is empty."
    
    str_response = "No pdf file found." #update this message based on file type...
    for file_data in file_values:
        if file_data[2] == ".pdf":
            str_response = await analyze_pdf(file_path=file_data[0]) #get relative path

    return str_response


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