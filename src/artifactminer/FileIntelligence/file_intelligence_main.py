#The main goal of this file is to achieve full file analysis given a path to a file
# This would mean being able to analyze a PDF for example for any essential information 
# that could be used in a resume. Primarily done using already made AI analysis functions, but
# also using basic string matching in order to comply with non-AI file analysis.


from git import List, Tuple
from pypdf import PdfReader

from artifactminer.RepositoryIntelligence.repo_intelligence_AI import user_allows_llm, getLLMResponse
#CRAWLER INTEGRATION
async def get_crawler_file_contents(file_values : List[Tuple[str, str, str]]) -> str:
    

    if file_values is None:
        return "no response, file value is null."
    if len(file_values) == 0: 
        return "no response, file value is empty."
    
    str_response = "No pdf file found." #update this message based on file type...
    for file_data in file_values:
        if file_data[2] == ".pdf":
            str_response = await analyze_pdf(file_path=file_data[1]) #get relative path
        if file_data[2] == ".md":
            str_response = await analyze_markdown(file_path=file_data[1])

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


async def analyze_markdown(file_path):
    """
    Analyze a Markdown file, detecting if it's a resume and extracting relevant information.

    Args:
        file_path: Path to the Markdown file to analyze

    Returns:
        Analysis results as a string
    """
    print(f"Performing Markdown analysis on: {file_path}")

    # Extract raw text from Markdown
    text = extract_text_from_markdown(file_path)

    if not text:
        return f"No content found in Markdown file at {file_path}."

    # Detect resume-style content
    resume_keywords = ["experience", "education", "skills", "projects", "work history"]
    lower_text = text.lower()
    is_resume = any(keyword in lower_text for keyword in resume_keywords)

    # Detect markdown headers
    markdown_headers = [
        line.strip("# ").strip()
        for line in text.splitlines()
        if line.strip().startswith("#")
    ]

    resume_header_matches = any(
        header.lower() in resume_keywords for header in markdown_headers
    )

    if resume_header_matches:
        is_resume = True

    if is_resume:
        print(f"Detected resume-style Markdown in: {file_path}")

    # LLM path
    if user_allows_llm():
        if is_resume:
            prompt = (
                "Analyze the following resume written in Markdown and extract key information. "
                "Focus on: work experience, education, technical skills, projects, and achievements. "
                "Preserve section hierarchy when possible. "
                "Format the output in a structured way suitable for portfolio analysis:\n\n"
            )
        else:
            prompt = (
                "Analyze the following Markdown file and extract structured key information. "
                "Respect headings, bullet lists, and code blocks in your interpretation:\n\n"
            )

        prompt += text
        response = await getLLMResponse(prompt)
        return response

    # Non-LLM basic analysis (string format)
    print("User has not consented to LLM usage. Performing basic Markdown analysis.")

    preview = text[:500] + "..." if len(text) > 500 else text

    if is_resume:
        detected_keywords = [kw for kw in resume_keywords if kw in lower_text]

        return (
            f"Basic Resume Markdown Analysis\n"
            f"File: {file_path}\n"
            f"Detected Keywords: {', '.join(detected_keywords) if detected_keywords else 'None'}\n"
            f"Detected Headers: {', '.join(markdown_headers) if markdown_headers else 'None'}\n"
            f"Preview:\n{preview}"
        )

    return (
        f"Basic Markdown Analysis\n"
        f"File: {file_path}\n"
        f"Headers Found: {', '.join(markdown_headers) if markdown_headers else 'None'}\n"
        f"Line Count: {len(text.splitlines())}\n"
        f"Preview:\n{preview}"
    )


def extract_text_from_markdown(file_path):
    """
    Extract raw text from a Markdown file.
    """
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            return file.read()
    except Exception as e:
        print(f"Error extracting text from Markdown: {e}")
        return ""
