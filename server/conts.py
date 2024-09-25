import os
from pathlib import Path
FILE_STORAGE_DIR =  Path("documents")
FILE_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
LLM_URL = os.getenv("OLLAMA_URI", "http://localhost:11434")
LLM_ENDPOINT =LLM_URL + "/api/generate"