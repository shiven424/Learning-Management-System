from flask import Flask, request, send_from_directory, abort, jsonify
import os
from threading import Thread
import grpc
from concurrent import futures
import lms_pb2_grpc
from lms_server import LMSServer
from conts import FILE_STORAGE_DIR

# Flask app initialization
app = Flask(__name__)

@app.route('/files/<filename>', methods=['GET'])
def serve_file(filename):
    file_path = os.path.join(FILE_STORAGE_DIR, filename)
    
    if not os.path.isfile(file_path):
        abort(404)  # File not found
    
    return send_from_directory(directory=FILE_STORAGE_DIR, filename=filename)

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    # Ensure the directory exists
    if not os.path.exists(FILE_STORAGE_DIR):
        os.makedirs(FILE_STORAGE_DIR)
    
    file_path = os.path.join(FILE_STORAGE_DIR, file.filename)
    file.save(file_path)
    
    return jsonify({'message': 'File uploaded successfully'})

def run_flask_app():
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)

def serve_grpc():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    lms_pb2_grpc.add_LMSServicer_to_server(LMSServer(), server)
    server.add_insecure_port('[::]:50051')
    server.start()
    print("LMS Server running on port 50051...")
    server.wait_for_termination()

def serve():
    # Start Flask app in a separate thread as a daemon
    flask_thread = Thread(target=run_flask_app)
    flask_thread.daemon = True
    flask_thread.start()

    # Start gRPC server
    serve_grpc()

if __name__ == '__main__':
    serve()
