from concurrent import futures
from conts import FILE_STORAGE_DIR
from file_server import app as flask_app  # Import Flask app and routes
from lms_server import LMSServer
from raft import raft_service  # Import the RaftNode class
from threading import Thread

import grpc
import lms_pb2_grpc
import logging
import os

# Ensure the file storage directory exists
os.makedirs(FILE_STORAGE_DIR, exist_ok=True)

# Configuration: List of peer nodes for Raft (Replace with actual host:port)


# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def run_flask_app():
    """Run the Flask app."""
    flask_app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)

def serve_grpc():
    """Run the gRPC server with both LMS and Raft services."""
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    
    # Initialize the LMS server and Raft node
    lms_service = LMSServer()  # LMS logic


    # Add LMS and Raft services to the gRPC server
    lms_pb2_grpc.add_LMSServicer_to_server(lms_service, server)
    lms_pb2_grpc.add_RaftServiceServicer_to_server(raft_service, server)  # Add Raft service

    # Expose the gRPC server on port 5000 internally (or other as needed)
    server.add_insecure_port(f'[::]:5000')
    server.start()
    logger.info(f"LMS and Raft services running on port 5000")
    server.wait_for_termination()

def serve():
    """Start Flask and gRPC servers together."""
    # Run Flask app in a separate thread
    # flask_thread = Thread(target=run_flask_app)
    # flask_thread.daemon = True
    # flask_thread.start()

    # Start the gRPC server (LMS + Raft services)
    serve_grpc()

if __name__ == '__main__':
    # Assign a unique node ID to each Raft node (e.g., 1, 2, 3)
    serve()
