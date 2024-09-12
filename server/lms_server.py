import logging
import lms_pb2
import lms_pb2_grpc
from authentication import authenticate, generate_token, invalidate_token
from database import register_user, add_assignment, get_assignments, add_grade, get_grades, add_feedback, get_feedback

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class LMSServer(lms_pb2_grpc.LMSServicer):
    def __init__(self):
        self.sessions = {}
        logger.info("LMS Server initialized")

    def Register(self, request, context):
        logger.info(f"Received registration request for user: {request.username} as {request.role}")
        if register_user(request.username, request.password, request.role):
            logger.info(f"Registration successful for user: {request.username}")
            return lms_pb2.StatusResponse(status="Registration successful")
        else:
            logger.warning(f"Registration failed for user: {request.username} - User already exists")
            return lms_pb2.StatusResponse(status="User already exists")

    def Login(self, request, context):
        logger.info(f"Login attempt by user: {request.username}")
        user = authenticate(request.username, request.password)
        if user:
            token = generate_token(user['username'])
            self.sessions[token] = user['username']
            logger.info(f"Login successful for user: {request.username}, Token: {token}")
            return lms_pb2.LoginResponse(status="Success", token=token)
        else:
            logger.warning(f"Login failed for user: {request.username}")
            return lms_pb2.LoginResponse(status="Failed", token="")

    def Logout(self, request, context):
        token = request.token
        logger.info(f"Logout request with token: {token}")
        if invalidate_token(token, self.sessions):
            logger.info(f"Logout successful for token: {token}")
            return lms_pb2.StatusResponse(status="Logged out successfully")
        else:
            logger.warning(f"Logout failed - Invalid token: {token}")
            return lms_pb2.StatusResponse(status="Invalid token")

    def Post(self, request, context):
        logger.info(f"Received post request of type: {request.type} by token: {request.token}")
        if request.type == "assignment":
            add_assignment(request.data)
            logger.info("Assignment submitted successfully")
        elif request.type == "grade":
            add_grade(request.data)
            logger.info("Grade submitted successfully")
        elif request.type == "feedback":
            add_feedback(request.data)
            logger.info("Feedback submitted successfully")
        else:
            logger.warning(f"Invalid post type: {request.type}")
        return lms_pb2.StatusResponse(status="Post successful")

    def Get(self, request, context):
        logger.info(f"Received get request of type: {request.type} by token: {request.token}")
        if request.type == "assignments":
            items = [lms_pb2.DataItem(typeId=str(i), data=d['data']) for i, d in enumerate(get_assignments())]
            logger.info("Assignments retrieved successfully")
        elif request.type == "grades":
            items = [lms_pb2.DataItem(typeId=str(i), data=d['data']) for i, d in enumerate(get_grades())]
            logger.info("Grades retrieved successfully")
        elif request.type == "feedback":
            items = [lms_pb2.DataItem(typeId=str(i), data=d['data']) for i, d in enumerate(get_feedback())]
            logger.info("Feedback retrieved successfully")
        else:
            items = []
            logger.warning(f"Invalid get type: {request.type}")
        return lms_pb2.GetResponse(status="Success", items=items)
