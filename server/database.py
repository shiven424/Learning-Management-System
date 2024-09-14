from pymongo import MongoClient
from bson.objectid import ObjectId
import os
import logging
from datetime import datetime
from conts import FILE_STORAGE_DIR
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
    file_path = os.path.join(FILE_STORAGE_DIR, filename)
    with open(file_path, 'wb') as f:
        f.write(file_data)
    return file_path

def register_user(username, password, role, name):
    existing_user = users_collection.find_one({"username": username})
    if existing_user:
        logger.info(f"User already exists: {username}")
        return False
    users_collection.insert_one({
        "username": username,
        "password": password,
        "role": role,
        "name": name
    })
    logger.info(f"User registered successfully: {username}")
    return True

def find_user(username):
    logger.info(f"Finding user for username: {username}")
    return users_collection.find_one({"username": username})

def add_assignment(student_id, teacher_id, filename, file_data, grade=None, feedback_text=None):
    file_path = save_file(file_data, filename)
    assignment_doc = {
        "student_id": student_id,
        "teacher_id": teacher_id,
        "filename": filename,
        "file_path": file_path,
        "submission_date": datetime.now(),
        "grade": grade,
        "feedback": feedback_text
    }
    assignments_collection.insert_one(assignment_doc)
    logger.info(f"Assignment added for student: {student_id}")

def get_assignments(student_id=None, teacher_id=None):
    query = {}
    if student_id:
        logger.info(f"Fetching assignments for student: {student_id}")
        query["student_id"] = student_id
    elif teacher_id:
        logger.info(f"Fetching assignments for teacher: {teacher_id}")
        query["teacher_id"] = teacher_id
    
    return list(assignments_collection.find(query, {"_id": 0, "filename": 1, "file_path": 1, "submission_date": 1, "grade": 1, "feedback": 1}))

def update_assignment(assignment_id, grade=None, feedback_text=None):
    update_fields = {}
    if grade is not None:
        update_fields["grade"] = grade
    if feedback_text is not None:
        update_fields["feedback"] = feedback_text
    if update_fields:
        assignments_collection.update_one({"_id": ObjectId(assignment_id)}, {"$set": update_fields})
        logger.info(f"Assignment updated: {assignment_id}")

def add_feedback(student_id=None, teacher_id=None, feedback_text=None):
    if not student_id and not teacher_id:
        logger.warning("Feedback must be associated with either a student or a teacher.")
        return None

    feedback_doc = {
        "student_id": student_id,
        "teacher_id": teacher_id,
        "feedback_text": feedback_text,
        "date": datetime.now()
    }
    feedback_collection.insert_one(feedback_doc)
    logger.info(f"Feedback added: {feedback_text}")
    return feedback_doc.inserted_id

def get_feedback(student_id=None, teacher_id=None):
    query = {}
    if student_id:
        query["student_id"] = student_id
        logger.info(f"Fetching feedback for student: {student_id}")
    elif teacher_id:
        query["teacher_id"] = teacher_id
        logger.info(f"Fetching feedback for teacher: {teacher_id}")
    else:
        logger.warning("No valid role specified for fetching feedback.")
        return []

    return list(feedback_collection.find(query, {"_id": 0, "feedback_text": 1, "date": 1}))

def add_course_material(course_id, course_name, filename, file_data, teacher_id, teacher_name):
    file_path = save_file(file_data, filename)
    course_material_doc = course_materials_collection.insert_one({
        "course_id": course_id,
        "course_name": course_name,
        "filename": filename,
        "file_path": file_path,
        "teacher_id": teacher_id,
        "teacher_name": teacher_name
    })
    logger.info(f"Course material added for course: {course_id}")
    return course_material_doc.inserted_id

def get_course_materials_by_teacher(teacher_name):
    logger.info(f"Fetching course materials for teacher: {teacher_name}")
    return list(course_materials_collection.find({"teacher_name": teacher_name}, {"_id": 0}))

def get_course_materials_by_course(course_name):
    logger.info(f"Fetching course materials for course: {course_name}")
    return list(course_materials_collection.find({"course_name": course_name}, {"_id": 0}))
