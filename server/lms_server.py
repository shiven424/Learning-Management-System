import logging
import lms_pb2
import lms_pb2_grpc
from authentication import authenticate, generate_token, invalidate_token
import uuid
from pathlib import Path
from database import (
    register_user, add_assignment, update_assignment,
     add_student_feedback,
    get_assignments, get_student_feedback,
    get_course_materials_by_course, get_course_materials_by_teacher, add_course_material,
    get_student_name_from_token,get_teacher_name_from_token, get_all_students
)
from collection_formats import User, Assignment, Feedback, CourseMaterial  # Import dataclasses
from datetime import datetime
from conts import FILE_STORAGE_DIR
import os
# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class LMSServer(lms_pb2_grpc.LMSServicer):
    def __init__(self):
        self.sessions = {}
        logger.info("LMS Server initialized")
    
    def save_file(self, file_data, filename):
        """Save the file data to a specified directory."""
        file_path = os.path.join(FILE_STORAGE_DIR, filename)
        with open(file_path, 'wb') as f:
            f.write(file_data)
        return file_path

    # --- Helper Functions ---
    # Post functions
    def _handle_post_assignment(self, request, user_session):
        """Handles student assignment submission."""
        assignment_data = request.assignment
        assignment = add_assignment(
            student_name=user_session['username'],
            teacher_name=assignment_data.teacher_name,
            filename=assignment_data.filename,
            file_path = assignment_data.file_path,
            file_id = assignment_data.file_id
        )
        
        logger.info("Assignment submitted successfully to database")
        return lms_pb2.StatusResponse(status="Assignment submitted successfully")

    
    def _handle_update_assignment(self, request, user_session):
        """Handles updating an assignment grade for a student."""
        assignment_update = request.assignment_update
        update_assignment(  
                assignment_id=assignment_update.assignment_id,
                grade=assignment_update.grade,
                feedback_text=assignment_update.feedback_text
            )
        
        logger.info("Assignment grade updated successfully")
        return lms_pb2.StatusResponse(status="Assignment grade updated successfully")

    def _handle_post_student_feedback(self, request, user_session):
        """Handles teacher student feedback submission."""
        feedback_data = request.student_feedback
        add_student_feedback(
            student_name=feedback_data.student_name,
            teacher_name=user_session['username'],
            feedback_text=feedback_data.feedback_text
        )
        logger.info("Student feedback submitted successfully")
        return lms_pb2.StatusResponse(status="Student feedback submitted successfully")

    def _handle_post_course_materials(self, request, user_session):
        """Handles teacher course materials submission."""
        course_materials_data = request.content
        course_material = CourseMaterial(
            course_name=course_materials_data.course_name,
            filename=course_materials_data.filename,
            file_path=course_materials_data.file_path,
            teacher_name=user_session['username']
        )
        add_course_material(course_material.to_dict())
        logger.info("Course materials submitted successfully")
        return lms_pb2.StatusResponse(status="Course materials submitted successfully")
    
    def _handle_upload_file(self, request, user_session)-> lms_pb2.UploadFileResponse:
        """Handles file upload."""
        file_data = request.data
        file_id = uuid.uuid4()
        filename  = Path(request.filename).stem+ "_" + str(file_id) + Path(request.filename).suffix
        file_path = self.save_file(file_data, filename)
        logger.info(f"File uploaded successfully: {filename}")
        return lms_pb2.UploadFileResponse(status="success", file_path=file_path, file_id=str(file_id))
    
    def _handle_download_file(self, request):
        """Handles file download."""
        logger.info(f"File download requested: {request.file_path}")
        if not os.path.exists(request.file_path):
            logger.info(f"File not found: {request.file_path}")
            return lms_pb2.DownloadFileResponse(status="File not found on server")
        with open(request.file_path, 'rb') as f:
            data = f.read()
        logger.info(f"File downloaded successfully")
        return lms_pb2.DownloadFileResponse(status="success", data=data)


# GET REQUESTS
    def _handle_get_assignments(self, role, user_session):
        """Handles retrieving assignments for both students and teachers."""
        if role == "student":
            assignments = get_assignments(student_name=user_session['username'])
        elif role == "teacher":
            assignments = get_assignments()
        logger.info(f"assignment items: {assignments}")
        assignment_items = [lms_pb2.AssignmentData(
            assignment_id=str(assignment['_id']),
            student_name=assignment["student_name"],
            teacher_name=assignment["teacher_name"],
            filename=assignment["filename"],
            file_path=assignment["file_path"],
            submission_date=str(assignment["submission_date"]),
            grade=assignment.get('grade', ''),
            feedback_text=assignment.get('feedback', ''),
        ) for i, assignment in enumerate(assignments)]
        logger.info(f"Assignments retrieved successfully {assignment_items}")
        return lms_pb2.GetResponse(status="Success", assignment_items=assignment_items)

    def _handle_get_feedback(self, role, request):
        """Handles retrieving assignment or student feedback."""
        if role == "student":
            student_name = get_student_name_from_token(request.token)
            feedbacks = get_student_feedback(student_name=student_name)
        else:
            teacher_name = get_teacher_name_from_token(request.token)
            feedbacks = get_student_feedback(teacher_name=teacher_name)
        # logger.info(f"feedback items: {feedbacks}")
        feedback_items = [lms_pb2.FeedbackData(
            feedback_id=str(feedback.get('_id', '')),
            student_name=feedback.get('student_name', ''),
            teacher_name=feedback.get('teacher_name', ''),
            feedback_text=feedback.get('feedback_text', ''),
            submission_date=str(feedback.get('submission_date', '')),
            ) for i, feedback in enumerate(feedbacks)]
        logger.info(f"Feedbacks retrieved successfully {feedback_items}")
        return lms_pb2.GetResponse(status="Success", feedback_items=feedback_items)

    def _handle_get_course_material(self, role, request, user_session):
        """Handles retrieving course materials."""
        if role == "teacher":
            course_materials = get_course_materials_by_teacher(teacher_name=user_session['username'])
        else:
            course_materials = get_course_materials_by_course(course_name=request.course_material.course_name)

        course_items = [lms_pb2.CourseMaterial(
            material_id=str(material.get('_id', '')),
            teacher_name=material.get('teacher_name', ''),
            course_name=material.get('course_name', ''),
            filename=material.get('filename', ''),
            file_path=material.get('file_path', ''),
            upload_date=str(material.get('upload_date', ''))
            ) for i, material in enumerate(course_materials)]
        return lms_pb2.GetResponse(status="Success", course_items=course_items)
    
    def GetStudents(self, request, context):

        # Fetch students from MongoDB (using the get_all_students() function)
        students = get_all_students()  # Assumed to be defined in database.py
        if not students:
            logger.info("No students found on the server side.")
        else:
            logger.info(f"Fetched students from MongoDB: {students}")
        # Convert students to protobuf format
        student_list = []
        for student in students:
            student_list.append(lms_pb2.Student(username=student['username'], name=student['name']))
        # Return the student list in the response
        return lms_pb2.GetStudentsResponse(students=student_list)

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

    def Upload(self, request, context):
        logger.info(f"Received upload request by token: {request.token}")
        user_session = self.sessions.get(request.token)
        if not user_session:
            logger.warning("Unauthorized access attempt")
            return lms_pb2.StatusResponse(status="Unauthorized")
        else:
            return self._handle_upload_file(request, user_session)
    
    def Download(self, request, context):
        logger.info(f"Received download request by token: {request.token}")
        user_session = self.sessions.get(request.token)
        if not user_session:
            logger.warning("Unauthorized access attempt")
            return lms_pb2.StatusResponse(status="Unauthorized")
        else:
            return self._handle_download_file(request)
            
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
            elif request.WhichOneof('data_type') == 'assignment_update' and role == "teacher":
                return self._handle_update_assignment(request, user_session)
            elif request.WhichOneof('data_type') == 'student_feedback' and (role == "teacher" or role == "student"):
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
            return lms_pb2.GetResponse(status="Unauthorized", assignment_items=[], feedback_items=[], course_items=[])

        role = user_session['role']

        # try:
        # Delegate get handling based on data type and role
        if request.WhichOneof('data_type') == 'assignment':
            return self._handle_get_assignments(role, user_session)
        elif request.WhichOneof('data_type') =='feedback'and (role == "teacher" or role == "student"):
            return self._handle_get_feedback(role, request)
        elif request.WhichOneof('data_type') == 'course_material':
            return self._handle_get_course_material(role, request, user_session)
        else:
            logger.warning(f"Invalid get request type or insufficient permissions: {request.WhichOneof('data_type')}")
            return lms_pb2.GetResponse(status="Invalid request or permissions", assignment_items=[], feedback_items=[], course_items=[])

        # except Exception as e:
        #     logger.error(f"Error during get operation: {str(e)}")
        #     return lms_pb2.GetResponse(status="Failed due to server error", assignment_items=[], feedback_items=[], course_items=[])


