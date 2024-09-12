from database import find_user
import uuid
import logging
# Dictionary to hold active sessions
# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


sessions = {}

def authenticate(username, password):
    logger.info(f"Username {username}")
    user = find_user(username)
    logger.info(f"Username {user} found . Pass {user['password']}")
    if user and user['password'] == password:
        logger.info("Password match")
        return user
    else:
        logger.info("Password mismatch")
    return None

def generate_token(username):
    token = str(uuid.uuid4())
    sessions[token] = username  # Store token with associated username
    return token

def invalidate_token(token):
    if token in sessions:
        del sessions[token]
        return True
    return False

def get_user_from_token(token):
    return sessions.get(token)
