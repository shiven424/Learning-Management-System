from flask import Flask, send_from_directory, abort, request, jsonify
import os
import logging

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Directory where files are stored
FILE_STORAGE_DIR = os.getenv("FILE_STORAGE_DIR", "/path/to/storage")

# Ensure the file storage directory exists
os.makedirs(FILE_STORAGE_DIR, exist_ok=True)

@app.route('/files/<filename>', methods=['GET'])
def serve_file(filename):
    logger.debug(f"Request to download file: {filename}")
    # Sanitize filename to prevent directory traversal
    safe_filename = os.path.basename(filename)
    file_path = os.path.join(FILE_STORAGE_DIR, safe_filename)
    
    # Check if file exists
    if not os.path.isfile(file_path):
        abort(404)  # File not found

    return send_from_directory(directory=FILE_STORAGE_DIR, filename=safe_filename)
if __name__ == '__main__':
    app.run(debug=True)
