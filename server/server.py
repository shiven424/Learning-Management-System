import os
import logging
from threading import Thread
import grpc
from concurrent import futures
import lms_pb2_grpc
from lms_server import LMSServer
from file_server import app as flask_app, serve_file, upload_file  # Import Flask app and routes
from conts import FILE_STORAGE_DIR

# Ensure the file storage directory exists
os.makedirs(FILE_STORAGE_DIR, exist_ok=True)

def run_flask_app():
    """Run the Flask app."""
    flask_app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)

def serve_grpc():
    """Run the gRPC server."""
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    lms_pb2_grpc.add_LMSServicer_to_server(LMSServer(), server)
    server.add_insecure_port('[::]:50051')
    server.start()
    print("LMS Server running on port 50051...")
    server.wait_for_termination()

def serve():
    """Start Flask and gRPC servers."""
    # Start Flask app in a separate thread as a daemon
    flask_thread = Thread(target=run_flask_app)
    flask_thread.daemon = True
    flask_thread.start()

    # Start gRPC server
    serve_grpc()

if __name__ == '__main__':
    serve()
