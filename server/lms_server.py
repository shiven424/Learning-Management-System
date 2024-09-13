import logging
import lms_pb2
import lms_pb2_grpc
from authentication import authenticate, generate_token, invalidate_token
from database import (
    register_user, add_assignment, get_assignments,
    add_grade, get_grades, add_feedback, get_feedback
)

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class LMSServer(lms_pb2_grpc.LMSServicer):
    def __init__(self):
        self.sessions = {}
        logger.info("LMS Server initialized")

    def Register(self, request, context):
        logger.info(f"Received registration request for user: {request.username} as {request.role}")
        try:
            if register_user(request.username, request.password, request.role, request.name):
                logger.info(f"Registration successful for user: {request.username}")
                return lms_pb2.StatusResponse(status="Registration successful")
            else:
                logger.warning(f"Registration failed for user: {request.username} - User already exists")
                return lms_pb2.StatusResponse(status="User already exists")
        except Exception as e:
            logger.error(f"Error during registration: {str(e)}")
            return lms_pb2.StatusResponse(status="Registration failed due to server error")

    def Login(self, request, context):
        logger.info(f"Login attempt by user: {request.username}")
        try:
            user = authenticate(request.username, request.password)
            if user:
                token = generate_token(user['username'])
                self.sessions[token] = {'username': user['username'], 'role': user['role']}
                logger.info(f"Login successful for user: {request.username}, Token: {token}")
                return lms_pb2.LoginResponse(status="Success", token=token)
            else:
                logger.warning(f"Login failed for user: {request.username}")
                return lms_pb2.LoginResponse(status="Failed", token="")
        except Exception as e:
            logger.error(f"Error during login: {str(e)}")
            return lms_pb2.LoginResponse(status="Failed due to server error", token="")

    def Logout(self, request, context):
        token = request.token
        logger.info(f"Logout request with token: {token}")
        if token in self.sessions:
            invalidate_token(token, self.sessions)
            logger.info(f"Logout successful for token: {token}")
            return lms_pb2.StatusResponse(status="Logged out successfully")
        else:
            logger.warning(f"Logout failed - Invalid token: {token}")
            return lms_pb2.StatusResponse(status="Invalid token")

    def Post(self, request, context):
        logger.info(f"Received post request of type: {request.type} by token: {request.token}")
        user_session = self.sessions.get(request.token)
        if not user_session:
            logger.warning("Unauthorized access attempt")
            return lms_pb2.StatusResponse(status="Unauthorized")

        role = user_session['role']

        try:
            if request.type == "assignment" and role == "student":
                add_assignment(
                    student_id=user_session['username'],
                    teacher_id=request.data.teacher_id,  # Ensure this matches actual logic
                    filename=request.data.filename,
                    data=request.data.file_data
                )
                logger.info("Assignment submitted successfully")
                return lms_pb2.StatusResponse(status="Assignment submitted successfully")
            
            elif request.type == "grade" and role == "teacher":
                add_grade(
                    assignment_id=request.data.assignment_id,
                    grade=request.data.grade,
                    comments=request.data.comments
                )
                logger.info("Grade submitted successfully")
                return lms_pb2.StatusResponse(status="Grade submitted successfully")
            
            elif request.type == "feedback" and role == "teacher":
                add_feedback(
                    student_id=request.data.student_id,
                    teacher_id=user_session['username'],
                    assignment_id=request.data.assignment_id,
                    feedback_text=request.data.feedback_text
                )
                logger.info("Feedback submitted successfully")
                return lms_pb2.StatusResponse(status="Feedback submitted successfully")
            
            else:
                logger.warning(f"Invalid post type or insufficient permissions: {request.type}")
                return lms_pb2.StatusResponse(status="Invalid type or permission denied")
        
        except Exception as e:
            logger.error(f"Error during post operation: {str(e)}")
            return lms_pb2.StatusResponse(status="Failed due to server error")

    def Get(self, request, context):
        logger.info(f"Received get request by token: {request.token}")
        user_session = self.sessions.get(request.token)
        
        if not user_session:
            logger.warning("Unauthorized access attempt")
            return lms_pb2.GetResponse(status="Unauthorized", items=[])

        role = user_session['role']
        items = []

        try:
            if request.HasField('assignments') and role == "student":
                assignments_request = request.assignments
                assignments = get_assignments(student_id=user_session['username'])
                items = [lms_pb2.DataItem(typeId=str(i), data=assignment['filename']) for i, assignment in enumerate(assignments)]
                logger.info("Assignments retrieved successfully")
            
            elif request.HasField('grades') and role == "student":
                grades_request = request.grades
                grades = get_grades(student_id=user_session['username'])
                items = [lms_pb2.DataItem(typeId=str(i), data=grade['grade']) for i, grade in enumerate(grades)]
                logger.info("Grades retrieved successfully")
            
            elif request.HasField('feedback') and role in ["student", "teacher"]:
                feedback_request = request.feedback
                if role == "student":
                    feedbacks = get_feedback(student_id=user_session['username'])
                else:
                    feedbacks = get_feedback(teacher_id=user_session['username'])
                items = [lms_pb2.DataItem(typeId=str(i), data=feedback['feedback_text']) for i, feedback in enumerate(feedbacks)]
                logger.info("Feedback retrieved successfully")
            
            else:
                logger.warning(f"Invalid get request type or insufficient permissions")
                return lms_pb2.GetResponse(status="Invalid request or permissions", items=[])

            return lms_pb2.GetResponse(status="Success", items=items)

        except Exception as e:
            logger.error(f"Error during get operation: {str(e)}")
            return lms_pb2.GetResponse(status="Failed due to server error", items=[])
