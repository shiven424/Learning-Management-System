import uuid

def authenticate(username, password):
    # Simplified authentication logic; replace with real authentication
    print(f"incoming user:{username} password: {password}")
    return username == "student" and password == "password"

def generate_token(username):
    return str(uuid.uuid4())

def invalidate_token(token, sessions):
    if token in sessions:
        del sessions[token]
        return True
    return False
