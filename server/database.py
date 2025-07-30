from pymongo import MongoClient
from bson.objectid import ObjectId
import os
import logging
from datetime import datetime
from conts import FILE_STORAGE_DIR
from collection_formats import User, Assignment, Feedback, CourseMaterial, Query

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
queries_collection = db.queries

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
        feedback_text=feedback_text,
    )
    assignments_collection.insert_one(assignment.to_dict())
    logger.info(f"Assignment added for student: {student_name}")

def get_assignments(student_name=None, teacher_name=None):
    query = {}
    if student_name:
        logger.info(f"Fetching assignments for student: {student_name}, query: {query}")
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
                                        "feedback_text": 1
                                    }))


def update_assignment(assignment_id, grade=None, feedback_text=None):
    update_fields = {}
    
    if grade and grade.strip():  # Only update if grade is not empty or just whitespace
        update_fields['grade'] = grade
    
    if feedback_text:
        update_fields['feedback_text'] = feedback_text
    
    # logger.info(f"Updating assignment: {assignment_id} with fields: {update_fields}")
    
    # Perform the database update
    result = assignments_collection.update_one(
        {"_id": ObjectId(assignment_id)}, 
        {"$set": update_fields}
    )
    
    return result

def add_student_feedback(student_name=None, teacher_name=None, feedback_text=None):
    if not student_name and not teacher_name:
        logger.warning("Feedback must be associated with either a student or a teacher.")
        return None

    feedback = Feedback(
        student_name=student_name,
        teacher_name=teacher_name,
        feedback_text=feedback_text,
        submission_date=datetime.now()
    )
    feedback_doc_id = feedback_collection.insert_one(feedback.to_dict()).inserted_id
    logger.info(f"Feedback added: {feedback_text}")
    return feedback_doc_id

def get_student_feedback(student_name=None, teacher_name=None):
    query = {}
    if student_name:
        query["student_name"] = student_name
        logger.info(f"Fetching feedback for student: {student_name}, query: {query}")
    elif teacher_name:
        query["teacher_name"] = teacher_name
        logger.info(f"Fetching feedback for teacher: {teacher_name}")
    # else:
    #     logger.warning("No valid role specified for fetching feedback.")
    #     return []

    return list(feedback_collection.find(query, {"_id": 1,
                                                 "feedback_text": 1,
                                                 "submission_date": 1,
                                                 "student_name": 1,
                                                 "teacher_name": 1
                                                 }))

def add_course_material(filename, file_path, file_id, teacher_name, course_name=None):
    course_material = CourseMaterial(
        course_name=course_name,
        filename=filename,
        file_path=file_path,
        file_id = file_id,
        teacher_name=teacher_name,
        upload_date=datetime.now()
    )
    course_materials_collection.insert_one(course_material.to_dict())
    logger.info(f"Course material added by teacher: {teacher_name}")

# def get_course_materials_by_teacher(teacher_name):
#     logger.info(f"Fetching course materials for teacher: {teacher_name}")
#     return list(course_materials_collection.find({"teacher_name": teacher_name}, {"_id": 0}))

# def get_course_materials_by_course(course_name):
#     logger.info(f"Fetching course materials for course: {course_name}")
#     return list(course_materials_collection.find({"course_name": course_name}, {"_id": 0}))

def get_course_materials():
    query = {}
    logger.info(f"Fetching course materials:")
    
    return list(course_materials_collection.find(query,
                                     {
                                        "_id": 1,
                                        "teacher_name": 1,  # Add this field
                                        "filename": 1,
                                        "file_path": 1,
                                        "file_id": 1,
                                        "upload_date": 1,
                                        "course_name":1
                                    }))

def get_student_name_from_token(token):
    # Assuming you have a way to map token to the student's username
    user = users_collection.find_one({"token": token})
    return user["username"] if user else None

def get_teacher_name_from_token(token):
    # Assuming you have a way to map token to the student's username
    user = users_collection.find_one({"token": token})
    return user["username"] if user else None

def get_all_students():
    """
    Fetches all registered students from the MongoDB collection.
    Returns a list of dictionaries with 'username' and 'name'.
    """
    try:
        # Query to find all students
        students_cursor = users_collection.find({"role": "student"}, {"_id": 0, "username": 1, "name": 1})
        
        # Convert cursor to a list of dictionaries
        students = list(students_cursor)
        
        if not students:
            logger.info("No students found in MongoDB")
        
        return students

    except Exception as e:
        logger.info(f"Error fetching students from MongoDB: {e}")
        return []
    
def get_all_teachers():
    """
    Fetches all registered teachers from the MongoDB collection.
    Returns a list of dictionaries with 'username' and 'name'.
    """
    try:
        # Query to find all students
        teachers_cursor = users_collection.find({"role": "teacher"}, {"_id": 0, "username": 1, "name": 1})
        
        # Convert cursor to a list of dictionaries
        teachers = list(teachers_cursor)
        
        if not teachers:
            logger.info("No teachers found in MongoDB")
        
        return teachers

    except Exception as e:
        logger.info(f"Error fetching teachers from MongoDB: {e}")
        return []

def get_last_10_queries():
    """
    Fetches the last 10 queries from the MongoDB collection.
    Returns a list of dictionaries with 'query' and 'timestamp'.
    """
    try:
        # Query to find the last 10 queries
        queries_cursor = queries_collection.find().sort("timestamp", -1).limit(10)
        
        # Convert cursor to a list of dictionaries
        queries = list(queries_cursor)
        
        if not queries:
            logger.info("No queries found in MongoDB")
        
        return queries

    except Exception as e:
        logger.info(f"Error fetching queries from MongoDB: {e}")
        return []

def get_queries_by_teacher():
    """
    Fetches queries by teacher from the MongoDB collection.
    Returns a list of dictionaries with 'query' and 'timestamp'.
    """
    try:
        # Query to find queries by teacher
        queries_cursor = queries_collection.find({"query_type": "teacher"})
        
        # Convert cursor to a list of dictionaries
        queries = list(queries_cursor)
        
        if not queries:
            logger.info("No queries found in MongoDB")
        
        return queries

    except Exception as e:
        logger.info(f"Error fetching queries from MongoDB: {e}")
        return []

def create_query(student_name, teacher_name, query_text, query_type, context_file_path)->str:
    """
    Creates a new query in the MongoDB collection.
    Returns the ID of the inserted document.
    """
    try:
        query = Query(
            student_name=student_name,
            teacher_name=teacher_name,
            query_text=query_text,
            query_type=query_type,
            date=datetime.now(),
            context_file_path=context_file_path
        )
        query_doc_id = queries_collection.insert_one(query.to_dict()).inserted_id
        logger.info(f"Query created: {query_text}")
        return str(query_doc_id)

    except Exception as e:
        logger.info(f"Error creating query in MongoDB: {e}")

def update_query(query_id, answer_text):
    update_fields = {}

    if answer_text:
        update_fields['status'] = "answered"
        
    if answer_text:
        update_fields['answer_text'] = answer_text
    
    logger.info(f"Updating query: {query_id} with fields: {update_fields}")
    
    # Perform the database update
    result = queries_collection.update_one(
        {"_id": ObjectId(query_id)}, 
        {"$set": update_fields}
    )
    
    return result
