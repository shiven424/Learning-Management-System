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
def register_user(username, password, role):
    existing_user = users_collection.find_one({"username": username})
    if existing_user:
        return False  # User already exists
    users_collection.insert_one({"username": username, "password": password, "role": role})
    return True

def find_user(username):
    logger.info(f"find user for username: {username}")
    return users_collection.find_one({"username": username})

def add_assignment(data):
    assignments_collection.insert_one({"data": data})

def get_assignments():
    return list(assignments_collection.find({}))

def add_grade(data):
    grades_collection.insert_one({"data": data})

def get_grades():
    return list(grades_collection.find({}))

def add_feedback(data):
    feedback_collection.insert_one({"data": data})

def get_feedback():
    return list(feedback_collection.find({}))
