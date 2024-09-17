from pymongo import MongoClient
from bson.objectid import ObjectId
import os
import logging
from datetime import datetime
from conts import FILE_STORAGE_DIR
from collection_formats import User, Assignment, Feedback, CourseMaterial

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Establish connection to MongoDB
MONGO_URI = os.getenv("MONGO_URI", "mongodb://mongo:27017/lms_db")
client = MongoClient(MONGO_URI)

# Select database and collections
db = client.lms_db
users_collection = db.users
assignments_collection = db.assignments
course_materials_collection = db.course_materials
feedback_collection = db.feedback

def save_file(file_data, filename):
    """Save the file data to a specified directory."""
    logger.info(f"Saving file: {filename} to {FILE_STORAGE_DIR}")
    file_path = os.path.join(FILE_STORAGE_DIR, filename)
    with open(file_path, 'wb') as f:
        f.write(file_data)
    return file_path

def register_user(username, password, role, name):
    existing_user = users_collection.find_one({"username": username})
    if existing_user:
        logger.info(f"User already exists: {username}")
        return False
    user = User(username=username, password=password, role=role, name=name)
    users_collection.insert_one(user.to_dict())
    logger.info(f"User registered successfully: {username}")
    return True

def find_user(username):
    logger.info(f"Finding user for username: {username}")
    return users_collection.find_one({"username": username})

# Assignments
def add_assignment(student_name, teacher_name, filename, file_path, file_id, grade=None, feedback_text=None):
    assignment = Assignment(
        student_name=student_name,
        teacher_name=teacher_name,
        filename=filename,
        file_path=file_path,
        file_id=file_id,
        submission_date=datetime.now(),
        grade=grade,
        feedback=feedback_text,
    )
    assignments_collection.insert_one(assignment.to_dict())
    logger.info(f"Assignment added for student: {student_name}")

def get_assignments(student_name=None, teacher_name=None):
    query = {}
    if student_name:
        logger.info(f"Fetching assignments for student: {student_name}")
        query["student_name"] = student_name
    elif teacher_name:
        logger.info(f"Fetching assignments for teacher: {teacher_name}")
        query["teacher_name"] = teacher_name
    
    return list(assignments_collection.find(query,
                                     {
                                        "_id": 1,
                                        "student_name": 1,  # Add this field
                                        "teacher_name": 1,  # Add this field
                                        "filename": 1,
                                        "file_path": 1,
                                        "file_id": 1,
                                        "submission_date": 1,
                                        "grade": 1,
                                        "feedback": 1
                                    }))

def update_assignment(assignment_id, grade=None, feedback_text=None):
    update_fields = {}
    if grade is not None:
        update_fields["grade"] = grade
    if feedback_text is not None:
        update_fields["feedback"] = feedback_text
    if update_fields:
        assignments_collection.update_one({"_id": ObjectId(assignment_id)}, {"$set": update_fields})
        logger.info(f"Assignment updated: {assignment_id}")

def add_student_feedback(student_name=None, teacher_name=None, feedback_text=None):
    if not student_name and not teacher_name:
        logger.warning("Feedback must be associated with either a student or a teacher.")
        return None

    feedback = Feedback(
        student_name=student_name,
        teacher_name=teacher_name,
        feedback_text=feedback_text,
        date=datetime.now()
    )
    feedback_doc_id = feedback_collection.insert_one(feedback.to_dict()).inserted_id
    logger.info(f"Feedback added: {feedback_text}")
    return feedback_doc_id

def get_student_feedback(student_name=None, teacher_name=None):
    query = {}
    if student_name:
        query["student_name"] = student_name
        logger.info(f"Fetching feedback for student: {student_name}")
    elif teacher_name:
        query["teacher_name"] = teacher_name
        logger.info(f"Fetching feedback for teacher: {teacher_name}")
    else:
        logger.warning("No valid role specified for fetching feedback.")
        return []

    return list(feedback_collection.find(query, {"_id": 0, "feedback_text": 1, "date": 1}))

def add_course_material(course_name, filename, file_data, file_id, teacher_id, teacher_name):
    file_path = save_file(file_data, filename)
    course_material = CourseMaterial(
        course_name=course_name,
        filename=filename,
        file_path=file_path,
        file_id = file_id,
        teacher_id=teacher_id,
        teacher_name=teacher_name
    )
    course_material_doc_id = course_materials_collection.insert_one(course_material.to_dict()).inserted_id
    logger.info(f"Course material added for course: {course_name}")
    return course_material_doc_id

def get_course_materials_by_teacher(teacher_name):
    logger.info(f"Fetching course materials for teacher: {teacher_name}")
    return list(course_materials_collection.find({"teacher_name": teacher_name}, {"_id": 0}))

def get_course_materials_by_course(course_name):
    logger.info(f"Fetching course materials for course: {course_name}")
    return list(course_materials_collection.find({"course_name": course_name}, {"_id": 0}))
