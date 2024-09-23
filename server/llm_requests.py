import requests
import logging
from PyPDF2 import PdfReader
from conts import LLM_ENDPOINT
from pathlib import Path

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def read_pdf(file_path):
    """Reads text from a PDF file."""
    try:
        text = ""
        if not Path(file_path).exists():
            logger.error(f"File not found: {file_path}")
        with open(file_path, "rb") as file:
            reader = PdfReader(file)
            for page in reader.pages:
                text += page.extract_text() or ""
        return text
    except Exception as e:
        logger.error(f"Error reading PDF file: {e}")
        return ""

def get_llm_answer(query_text, pdf_file_path):
    """Gets an answer from the LLM using the query and context from the PDF."""
    # Read text from the PDF
    context_text = read_pdf(pdf_file_path)
    if not context_text:
        context_text = "null"  # Provide context null if PDF reading fails

    # Prepare the request payload
    payload = {
        "model": "gemma2:2b",
        "prompt": f"context: {context_text} question: {query_text}",
        "options": {
            "num_predict": 200, # Size of answer
            "temperature": 0.3  # Lower means less creative
        },
        "stream": False # Give whole answer at once
    }

    # Attempt to make the request, retrying on failure
    for attempt in range(2):
        try:
            response = requests.post(LLM_ENDPOINT, json=payload)  # Update the URL as necessary
            response.raise_for_status()  # Raise an error for bad responses
            return response.json()["response"]  # Return the JSON response
        except requests.exceptions.RequestException as e:
            logger.error(f"Attempt {attempt + 1} failed: {e}")
            if attempt == 1:
                logger.error("All attempts to contact LLM failed.")
                return None  # Return None if all attempts fail

# Example usage
# answer = get_llm_answer("What is the main topic?", "path/to/your/file.pdf")
# print(answer)

