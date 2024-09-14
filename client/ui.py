from flask import Flask, render_template, request, redirect, url_for, session, send_file
import grpc
import lms_pb2
import lms_pb2_grpc
import logging
import os
from werkzeug.utils import secure_filename
import io
import base64

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = 'supersecretkey'
app.config.update(
    SESSION_COOKIE_SECURE=True,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    FILE_STORAGE_DIR='documents'
)

# gRPC Channel Setup
channel = grpc.insecure_channel('lms_server:50051')
stub = lms_pb2_grpc.LMSStub(channel)
logger.info("Client connected to LMS Server")

# Utilities for session and validation
def check_session():
    if 'token' not in session:
        logger.warning("No valid session detected")
        return False
    return True

def handle_grpc_error(e):
    logger.error(f"gRPC error: {e.code()} - {e.details()}")
    return "An error occurred. Please try again later.", 500

# Views (GET / POST Handlers)
@app.route('/')
def home():
    return render_home()

def render_home():
    logger.info("Rendering home page")
    return render_template('login.html')


# Registration View
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        return handle_register_post()
    return render_register_get()

def handle_register_post():
    username, password, role = request.form['username'], request.form['password'], request.form['role']
    logger.info(f"Attempting to register user: {username} as {role}")
    
    try:
        response = stub.Register(lms_pb2.RegisterRequest(username=username, password=password, role=role))
        if response.status == "Registration successful":
            logger.info(f"Registration successful for user: {username}")
            return redirect(url_for('home'))
        logger.warning(f"Registration failed: {response.status}")
        return "Registration Failed: User already exists", 400
    except grpc.RpcError as e:
        return handle_grpc_error(e)

def render_register_get():
    logger.info("Rendering registration page")
    return render_template('register.html')


# Login View
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        return handle_login_post()
    return render_login_get()

def handle_login_post():
    username, password = request.form['username'], request.form['password']
    logger.info(f"Login attempt for user: {username}")
    
    try:
        response = stub.Login(lms_pb2.LoginRequest(username=username, password=password))
        if response.status == "Success":
            session['token'], session['role'], session['username'], session['logged_in'] = response.token, response.role, username, True
            logger.info(f"Login successful for user: {username}")
            return redirect(url_for('dashboard'))
        logger.warning(f"Login failed for user: {username}")
        return render_template('login.html', error="Incorrect username or password"), 401
    except grpc.RpcError as e:
        return handle_grpc_error(e)

def render_login_get():
    logger.info("Rendering login page")
    return render_template('login.html')


# Dashboard View
@app.route('/dashboard')
def dashboard():
    if not check_session():
        return redirect(url_for('home'))
    logger.info("Rendering dashboard")
    return render_template('dashboard.html')


# Assignments View
@app.route('/assignments', methods=['GET', 'POST'])
def assignments():
    if not check_session():
        return redirect(url_for('home'))

    if request.method == 'POST':
        return handle_assignments_post()
    return render_assignments_get()

def handle_assignments_post():
    for assignment_id, grade in request.form.items():
        if assignment_id.startswith('grade_'):
            post_grade(assignment_id[len('grade_'):], grade)
    
    feedbacks = {k: v for k, v in request.form.items() if k.startswith('feedback_')}
    for assignment_id, feedback in feedbacks.items():
        post_feedback(assignment_id[len('feedback_'):], feedback)

    return redirect(url_for('assignments'))

def render_assignments_get():
    try:
        response = stub.Get(lms_pb2.GetRequest(
            token=session['token'],
            assignments=lms_pb2.GetAssignmentsRequest(student_id="student_id_placeholder")  # Replace with actual student_id
        ))
        assignments = [{
            'assignment_id': item.assignment_id,
            'filename': item.filename,
            'data': item.data.encode('utf-8') if isinstance(item.data, str) else item.data
        } for item in response.items]
        logger.info("Assignments retrieved successfully")
        return render_template('assignments.html', assignments=assignments, role=session['role'])
    except grpc.RpcError as e:
        return handle_grpc_error(e)


# Grades View



# Feedback View
@app.route('/feedback', methods=['GET', 'POST'])
def feedback():
    if not check_session():
        return redirect(url_for('home'))

    if request.method == 'POST':
        return handle_feedback_post()
    return render_feedback_get()

def handle_feedback_post():
    feedback_text = request.form['feedback']
    logger.info("Submitting feedback")
    try:
        response = stub.Post(lms_pb2.PostRequest(
            token=session['token'],
            feedback=lms_pb2.FeedbackData(
                student_id="student_id_placeholder",  # Replace with actual student_id
                assignment_id="assignment_id_placeholder",  # Replace with actual assignment_id
                feedback_text=feedback_text
            )
        ))
        if response.status == "Success":
            logger.info("Feedback submitted successfully")
            return redirect(url_for('feedback'))
        else:
            logger.warning(f"Failed to submit feedback: {response.status}")
            return "Failed to submit feedback", 400
    except grpc.RpcError as e:
        return handle_grpc_error(e)

def render_feedback_get():
    try:
        response = stub.Get(lms_pb2.GetRequest(
            token=session['token'],
            feedback=lms_pb2.GetFeedbackRequest(
                student_id="student_id_placeholder",  # Replace with actual student_id
                teacher_id="teacher_id_placeholder"  # Optional: Replace with actual teacher_id
            )
        ))
        feedback_items = [{'assignment_id': item.assignment_id, 'feedback_text': item.feedback_text} for item in response.items]
        logger.info("Feedback retrieved")
        return render_template('feedback.html', feedback=feedback_items)
    except grpc.RpcError as e:
        return handle_grpc_error(e)


# File Download
@app.route('/files/<filename>')
def download_file(filename):
    if not check_session():
        return redirect(url_for('home'))
    return serve_file(filename)

def serve_file(filename):
    file_path = os.path.join(app.config['FILE_STORAGE_DIR'], filename)
    if os.path.exists(file_path):
        logger.info(f"Serving file: {filename}")
        return send_file(file_path)
    logger.warning(f"File not found: {filename}")
    return "File not found", 404


# Logout
@app.route('/logout')
def logout():
    return handle_logout()

def handle_logout():
    token = session.pop('token', None)
    if token:
        logger.info(f"Logout request for token: {token}")
        try:
            session.clear()
            stub.Logout(lms_pb2.LogoutRequest(token=token))
            logger.info("Logout successful")
        except grpc.RpcError as e:
            handle_grpc_error(e)
    return redirect(url_for('home'))


# Base64 Filter
@app.template_filter('b64encode')
def b64encode_filter(data):
    if not isinstance(data, bytes):
        data = str(data).encode('utf-8')
    return base64.b64encode(data).decode('utf-8')


if __name__ == '__main__':
    logger.info("Starting LMS Client")
    app.run(host='0.0.0.0', port=5000)
