import grpc
import lms_pb2_grpc
import logging
import lms_pb2
from flask import session
# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

channel = None
stub = None

def setup_grpc_client():
    global channel, stub
    channel = grpc.insecure_channel('lms_server:50051')
    stub = lms_pb2_grpc.LMSStub(channel)
    logger.info("Client connected to LMS Server")

def handle_grpc_error(e):
    logger.error(f"gRPC error: {e.code()} - {e.details()}")
    return "An error occurred. Please try again later.", 500

def fetch_teachers_via_grpc():
    """Fetches a list of teachers from the gRPC service."""
    try:
        # Send a request to the gRPC server to get the list of teachers
        teacher_response = stub.GetTeachers(lms_pb2.GetTeachersRequest(token=session['token']))

        teachers = [{'username': teacher.username, 'name': teacher.name} for teacher in teacher_response.teachers]
        
        if not teachers:
            logger.info("No teachers returned from gRPC.")
        else:
            logger.info(f"Teachers fetched via gRPC: {teachers}")

        return teachers

    except grpc.RpcError as e:
        logger.error(f"Error in gRPC call to fetch teachers: {e}")
        raise

def fetch_students_via_grpc():
    """Fetches a list of students from the gRPC service."""
    try:
        # Send a request to the gRPC server to get the list of students
        student_response = stub.GetStudents(lms_pb2.GetStudentsRequest(token=session['token']))

        students = [{'username': student.username, 'name': student.name} for student in student_response.students]
        
        if not students:
            logger.info("No students returned from gRPC.")
        else:
            logger.info(f"Students fetched via gRPC: {students}")

        return students

    except grpc.RpcError as e:
        logger.error(f"Error in gRPC call to fetch students: {e}")
        raise

