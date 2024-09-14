from flask import Flask, send_from_directory, abort, request, jsonify
import os

app = Flask(__name__)

# Directory where files are stored
FILE_STORAGE_DIR = os.getenv("FILE_STORAGE_DIR", "/path/to/storage")

# Ensure the file storage directory exists
os.makedirs(FILE_STORAGE_DIR, exist_ok=True)

@app.route('/files/<filename>', methods=['GET'])
def serve_file(filename):
    # Sanitize filename to prevent directory traversal
    safe_filename = os.path.basename(filename)
    file_path = os.path.join(FILE_STORAGE_DIR, safe_filename)
    
    # Check if file exists
    if not os.path.isfile(file_path):
        abort(404)  # File not found

    return send_from_directory(directory=FILE_STORAGE_DIR, filename=safe_filename)

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    # Sanitize filename to prevent directory traversal
    safe_filename = os.path.basename(file.filename)
    file_path = os.path.join(FILE_STORAGE_DIR, safe_filename)
    
    # Save the file
    file.save(file_path)
    
    return jsonify({'message': 'File uploaded successfully'}), 201

if __name__ == '__main__':
    app.run(debug=True)
