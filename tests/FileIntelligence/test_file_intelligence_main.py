#test basic PDF analysis functionality
import os
from artifactminer.FileIntelligence.file_intelligence_main import analyze_file
from artifactminer.RepositoryIntelligence.repo_intelligence_AI import set_user_consent
def test_analyze_pdf():
    set_user_consent("full")  # Ensure user consent is given for LLM usage
    # Assuming there's a sample PDF file in the test directory
    test_pdf_path = os.path.join(os.path.dirname(__file__), r'tests\FileIntelligence\Sample.pdf')
    
    result = analyze_file(test_pdf_path)
    assert result is not None
    print("PDF analysis result:", result)
