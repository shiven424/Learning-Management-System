import logging
import lms_pb2
import lms_pb2_grpc
from authentication import authenticate, generate_token, invalidate_token
from database import (
    register_user, add_assignment, update_assignment,
     add_student_feedback,
    get_assignments, get_assignment_feedback, get_student_feedback,
    get_course_materials_by_course, get_course_materials_by_teacher, add_course_material
)
from schema import User, Assignment, Feedback, CourseMaterial  # Import dataclasses
from datetime import datetime
# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class LMSServer(lms_pb2_grpc.LMSServicer):
    def __init__(self):
        self.sessions = {}
        logger.info("LMS Server initialized")

    # --- Helper Functions ---
    def _handle_post_assignment(self, request, user_session):
        """Handles student assignment submission."""
        assignment_data = request.assignment
        assignment = Assignment(
            student_name=user_session['username'],
            teacher_name=assignment_data.teacher_id,
            filename=assignment_data.filename,
            file_path=assignment_data.file_path,
            submission_date=datetime.datetime.now()
        )
        add_assignment(assignment.to_dict())
        logger.info("Assignment submitted successfully")
        return lms_pb2.StatusResponse(status="Assignment submitted successfully")

    
    def _handle_update_assignment(self, request, user_session):
        """Handles updating an assignment grade for a student."""
        assignment_data = request.assignment
        update_assignment(
                assignment_id=assignment_data.assignment_id,
                grade=assignment_data.grade,
                feedback_text=assignment_data.feedback
            )
        
        logger.info("Assignment grade updated successfully")
        return lms_pb2.StatusResponse(status="Assignment grade updated successfully")

    def _handle_post_student_feedback(self, request, user_session):
        """Handles teacher student feedback submission."""
        feedback_data = request.student_feedback
        add_student_feedback(
            student_id=feedback_data.student_name,
            teacher_id=user_session['username'],
            feedback_text=feedback_data.feedback_text
        )
        logger.info("Student feedback submitted successfully")
        return lms_pb2.StatusResponse(status="Student feedback submitted successfully")

    def _handle_post_course_materials(self, request, user_session):
        """Handles teacher course materials submission."""
        course_materials_data = request.course_materials
        course_material = CourseMaterial(
            course_name=course_materials_data.course_name,
            filename=course_materials_data.filename,
            file_path=course_materials_data.file_path,
            teacher_id=user_session['username'],
            teacher_name=user_session['username']
        )
        add_course_material(course_material.to_dict())
        logger.info("Course materials submitted successfully")
        return lms_pb2.StatusResponse(status="Course materials submitted successfully")


# GET REQUESTS
    def _handle_get_assignments(self, role, user_session):
        """Handles retrieving assignments for both students and teachers."""
        if role == "student":
            assignments = get_assignments(student_id=user_session['username'])
        elif role == "teacher":
            assignments = get_assignments(teacher_id=user_session['username'])

        items = [lms_pb2.DataItem(
            assignment_id=str(assignment.get('_id', '')),
            typeId=str(i),
            filename=assignment.get('filename', ''),
            data=assignment.get('file_path', '')  # Send file path instead of file data
        ) for i, assignment in enumerate(assignments)]
        return lms_pb2.GetResponse(status="Success", items=items)

    # def _handle_get_grades(self, user_session):
    #     """Handles retrieving grades for students."""
    #     grades = get_grades(student_id=user_session['username'])
    #     items = [lms_pb2.DataItem(typeId=str(i), data=grade['grade']) for i, grade in enumerate(grades)]
    #     return lms_pb2.GetResponse(status="Success", items=items)

    def _handle_get_feedback(self, role, request):
        """Handles retrieving assignment or student feedback."""
        if request.WhichOneof('data_type') == 'assignment_feedback':
            feedbacks = get_assignment_feedback(assignment_id=request.assignment_feedback.assignment_id)
        else:
            if role == "student":
                feedbacks = get_student_feedback(student_id=request.token)
            else:
                feedbacks = get_student_feedback(teacher_id=request.token)

        items = [lms_pb2.DataItem(typeId=str(i), data=feedback['feedback_text']) for i, feedback in enumerate(feedbacks)]
        return lms_pb2.GetResponse(status="Success", items=items)

    def _handle_get_course_material(self, role, request, user_session):
        """Handles retrieving course materials."""
        if role == "teacher":
            course_materials = get_course_materials_by_teacher(teacher_name=user_session['username'])
        else:
            course_materials = get_course_materials_by_course(course_name=request.course_material.course_name)

        items = [lms_pb2.DataItem(typeId=str(i), data=material['file_path']) for i, material in enumerate(course_materials)]
        return lms_pb2.GetResponse(status="Success", items=items)

    # --- Main Functions ---
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
                return lms_pb2.LoginResponse(status="Success", token=token, role=user['role'])
            else:
                logger.warning(f"Login failed for user: {request.username}")
                return lms_pb2.LoginResponse(status="Failed", token="", role="")
        except Exception as e:
            logger.error(f"Error during login: {str(e)}")
            return lms_pb2.LoginResponse(status="Failed due to server error", token="", role="")

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
        logger.info(f"Received post request by token: {request.token}")
        user_session = self.sessions.get(request.token)
        if not user_session:
            logger.warning("Unauthorized access attempt")
            return lms_pb2.StatusResponse(status="Unauthorized")

        role = user_session['role']

        try:
            # Delegate post handling based on data type and role
            if request.WhichOneof('data_type') == 'assignment' and role == "student":
                return self._handle_post_assignment(request, user_session)
            elif request.WhichOneof('data_type') in ['assignment_feedback','assignment_grade'] and role == "teacher":
                return self._handle_update_assignment(request, user_session)
            elif request.WhichOneof('data_type') == 'student_feedback' and role == "teacher":
                return self._handle_post_student_feedback(request, user_session)
            elif request.WhichOneof('data_type') == 'course_material' and role == "teacher":
                return self._handle_post_course_material(request, user_session)
            else:
                logger.warning(f"Invalid post type or insufficient permissions: {request.WhichOneof('data_type')}")
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

        try:
            # Delegate get handling based on data type and role
            if request.WhichOneof('data_type') == 'assignments':
                return self._handle_get_assignments(role, user_session)
            elif request.WhichOneof('data_type') =='student_feedback':
                return self._handle_get_feedback(role, request)
            elif request.WhichOneof('data_type') == 'course_material':
                return self._handle_get_course_material(role, request, user_session)
            else:
                logger.warning("Invalid get request type or insufficient permissions")
                return lms_pb2.GetResponse(status="Invalid request or permissions", items=[])

        except Exception as e:
            logger.error(f"Error during get operation: {str(e)}")
            return lms_pb2.GetResponse(status="Failed due to server error", items=[])


