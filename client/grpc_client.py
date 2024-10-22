from flask import session
from lms_pb2 import Empty
from lms_pb2_grpc import RaftServiceStub

import grpc
import lms_pb2
import lms_pb2_grpc
import logging
import time
# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class GRPCClient:
    def __init__(self):
        self.peer_nodes = ["lms_server_1:5000", "lms_server_2:5000", "lms_server_3:5000"]
        self.leader_address = None
        self.find_leader_address()
        self.channel = None
        self.stub = None
        self.setup_grpc_client()

    def setup_grpc_client(self):
        self.channel = grpc.insecure_channel(self.leader_address)
        self.stub = lms_pb2_grpc.LMSStub(self.channel)
        logger.info("Client connected to LMS Server Leader")

    def find_leader_address(self):
        """Ask any peer for the current leader's address using Raft's GetLeader RPC."""
        self.leader_address = None
        backoff = 1  # Start with a 1 second backoff
        max_backoff = 32  # Maximum backoff time

        while self.leader_address is None:
            logger.info("Searching for leader...")
            for peer in self.peer_nodes:
                try:
                    channel = grpc.insecure_channel(peer)
                    raft_stub = RaftServiceStub(channel)
                    response = raft_stub.GetLeader(Empty())
                    if response.leader_address:
                        logger.info(f"Current leader found: {response.leader_address}")
                        self.leader_address = response.leader_address
                        return True
                    else:
                        logger.info(f"{peer} is not the leader.")
                except grpc.RpcError as e:
                    logger.warning(f"Failed to contact peer {peer}: {e}")
                    continue  # Try the next peer

            logger.error("Leader not found. Retrying with backoff...")
            time.sleep(backoff)
            backoff = min(max_backoff, backoff * 1.3)  # Exponential backoff

    def handle_grpc_error(self,e):
        """Handles leader redirection when a gRPC error indicates the node is not the leader."""
        # Refer to https://grpc.io/docs/guides/status-codes/ for gRPC error codes
        if e.code() == grpc.StatusCode.UNAVAILABLE:
            # This could indicate that the node is down or unavailable
            logger.error(f"gRPC error: {e.code()} - {e.details()}. The node might be down.")
            if self.find_leader_address():
                self.setup_grpc_client()
        elif e.code() == grpc.StatusCode.FAILED_PRECONDITION:
            # Custom error for a node indicating it's not the leader
            logger.info(f"Node is not the leader. Re-fetching the current leader.")
            if self.find_leader_address():
                self.setup_grpc_client()
        else:
            # Other gRPC errors
            logger.error(f"Unhandled gRPC error: {e.code()} - {e.details()}")
            raise e  # Rethrow if it's not related to leader redirection



    def fetch_teachers_via_grpc(self):
        """Fetches a list of teachers from the gRPC service."""
        try:
            # Send a request to the gRPC server to get the list of teachers
            teacher_response = self.stub.GetTeachers(lms_pb2.GetTeachersRequest(token=session['token']))

            teachers = [{'username': teacher.username, 'name': teacher.name} for teacher in teacher_response.teachers]
            
            if not teachers:
                logger.info("No teachers returned from gRPC.")
            else:
                logger.info(f"Teachers fetched via gRPC: {teachers}")

            return teachers

        except grpc.RpcError as e:
            logger.error(f"Error in gRPC call to fetch teachers: {e}")
            self.handle_grpc_error(e)
            

    def fetch_students_via_grpc(self):
        """Fetches a list of students from the gRPC service."""
        try:
            # Send a request to the gRPC server to get the list of students
            student_response = self.stub.GetStudents(lms_pb2.GetStudentsRequest(token=session['token']))

            students = [{'username': student.username, 'name': student.name} for student in student_response.students]
            
            if not students:
                logger.info("No students returned from gRPC.")
            else:
                logger.info(f"Students fetched via gRPC: {students}")

            return students

        except grpc.RpcError as e:
            logger.error(f"Error in gRPC call to fetch students: {e}")
            self.handle_grpc_error(e)


# Initialize the gRPC client
grpc_client = GRPCClient()