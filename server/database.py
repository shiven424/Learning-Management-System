from pymongo import MongoClient
import os
import logging

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
grades_collection = db.grades
feedback_collection = db.feedback

# Functions to handle database operations

def register_user(username, password, role, name):
    """
    Registers a new user with a given role.
    
    Args:
        username (str): Username for the user.
        password (str): Password for the user.
        role (str): Role of the user ('student' or 'teacher').
        name (str): Name of the user.

    Returns:
        bool: True if user is successfully registered, False if username exists.
    """
    existing_user = users_collection.find_one({"username": username})
    if existing_user:
        logger.info(f"User already exists: {username}")
        return False  # User already exists
    users_collection.insert_one({
        "username": username,
        "password": password,  # Hash the password in a real application
        "role": role,
        "name": name
    })
    logger.info(f"User registered successfully: {username}")
    return True

def find_user(username):
    """
    Finds a user by their username.

    Args:
        username (str): The username of the user.

    Returns:
        dict: The user document if found, else None.
    """
    logger.info(f"Finding user for username: {username}")
    return users_collection.find_one({"username": username})

def add_assignment(student_id, teacher_id, filename, data):
    """
    Adds an assignment to the database.

    Args:
        student_id (ObjectId): The identifier of the student.
        teacher_id (ObjectId): The identifier of the teacher.
        filename (str): The filename of the assignment.
        data (bytes): The binary data of the assignment file.
    """
    assignments_collection.insert_one({
        "student_id": student_id,
        "teacher_id": teacher_id,
        "filename": filename,
        "data": data,
        "submission_date": datetime.now(),
        "grade_id": None  # Initially no grade assigned
    })
    logger.info(f"Assignment added for student: {student_id}")

def get_assignments(student_id=None, teacher_id=None):
    """
    Retrieves assignments based on user role.
    
    Args:
        student_id (ObjectId, optional): The identifier of the student.
        teacher_id (ObjectId, optional): The identifier of the teacher.

    Returns:
        list: A list of assignments based on role.
    """
    if student_id:
        logger.info(f"Fetching assignments for student: {student_id}")
        return list(assignments_collection.find({"student_id": student_id}, {"_id": 0, "filename": 1, "data": 1, "submission_date": 1}))
    elif teacher_id:
        logger.info(f"Fetching all assignments for teacher: {teacher_id}")
        return list(assignments_collection.find({"teacher_id": teacher_id}, {"_id": 0, "student_id": 1, "filename": 1, "submission_date": 1}))
    else:
        logger.warning("No valid role specified for fetching assignments.")
        return []

def add_grade(assignment_id, grade, comments):
    """
    Adds a grade for a specific assignment.

    Args:
        assignment_id (ObjectId): The identifier of the assignment.
        grade (str): The grade assigned.
        comments (str): Additional comments.

    Returns:
        ObjectId: The identifier of the grade document created.
    """
    grade_doc = grades_collection.insert_one({
        "assignment_id": assignment_id,
        "grade": grade,
        "comments": comments
    })
    # Update the assignment with the grade reference
    assignments_collection.update_one({"_id": assignment_id}, {"$set": {"grade_id": grade_doc.inserted_id}})
    logger.info(f"Grade added for assignment: {assignment_id}")
    return grade_doc.inserted_id

def get_grades(student_id):
    """
    Retrieves grades for a specific student based on assignments.

    Args:
        student_id (ObjectId): The identifier of the student.

    Returns:
        list: A list of grades for the student's assignments.
    """
    assignments = assignments_collection.find({"student_id": student_id})
    grades = []
    for assignment in assignments:
        if assignment.get("grade_id"):
            grade = grades_collection.find_one({"_id": assignment["grade_id"]})
            grades.append(grade)
    logger.info(f"Grades retrieved for student: {student_id}")
    return grades

def add_feedback(student_id, teacher_id, assignment_id, feedback_text):
    """
    Adds feedback for a specific assignment.

    Args:
        student_id (ObjectId): The identifier of the student.
        teacher_id (ObjectId): The identifier of the teacher.
        assignment_id (ObjectId): The identifier of the assignment.
        feedback_text (str): Feedback text.

    Returns:
        ObjectId: The identifier of the feedback document created.
    """
    feedback_doc = feedback_collection.insert_one({
        "student_id": student_id,
        "teacher_id": teacher_id,
        "assignment_id": assignment_id,
        "feedback_text": feedback_text,
        "date": datetime.now()
    })
    logger.info(f"Feedback added for student: {student_id}, assignment: {assignment_id}")
    return feedback_doc.inserted_id

def get_feedback(student_id=None, teacher_id=None):
    """
    Retrieves feedback based on role. 
    Students can only see their feedback; teachers can filter by student.

    Args:
        student_id (ObjectId, optional): The identifier of the student.
        teacher_id (ObjectId, optional): The identifier of the teacher.

    Returns:
        list: A list of feedback documents based on role.
    """
    if student_id:
        logger.info(f"Fetching feedback for student: {student_id}")
        return list(feedback_collection.find({"student_id": student_id}, {"_id": 0, "feedback_text": 1, "date": 1}))
    elif teacher_id:
        logger.info(f"Fetching all feedback for teacher: {teacher_id}")
        return list(feedback_collection.find({"teacher_id": teacher_id}, {"_id": 0, "student_id": 1, "feedback_text": 1, "date": 1}))
    else:
        logger.warning("No valid role specified for fetching feedback.")
        return []
