from flask import Flask, render_template, request, redirect, url_for, session
import grpc
import lms_pb2
import lms_pb2_grpc
import logging
from werkzeug.utils import secure_filename
import io

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = 'supersecretkey'

# gRPC Channel Setup
channel = grpc.insecure_channel('lms_server:50051')
stub = lms_pb2_grpc.LMSStub(channel)
logger.info("Client connected to LMS Server")

@app.route('/')
def home():
    logger.info("Rendering home page")
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        role = request.form['role']
        logger.info(f"Attempting to register user: {username} as {role}")
        response = stub.Register(lms_pb2.RegisterRequest(username=username, password=password, role=role))
        if response.status == "Registration successful":
            logger.info(f"Registration successful for user: {username}")
            return redirect(url_for('home'))
        else:
            logger.warning(f"Registration failed for user: {username} - {response.status}")
            return "Registration Failed: User already exists", 400
    logger.info("Rendering registration page")
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        logger.info(f"Login attempt for user: {username}")
        try:
            response = stub.Login(lms_pb2.LoginRequest(username=username, password=password))
            if response.status == "Success":
                session['token'] = response.token
                logger.info(f"Login successful for user: {username}, Token: {response.token}")
                return redirect(url_for('dashboard'))
            else:
                logger.warning(f"Login failed for user: {username}")
                return render_template('login.html', error="Login Failed: Incorrect username or password"), 401
        except grpc.RpcError as e:
            logger.error(f"gRPC error: {e}")
            return render_template('login.html', error="An error occurred. Please try again later."), 500
    else:
        logger.info("Rendering login page")
        return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'token' not in session:
        logger.info("Access to dashboard denied - no valid session")
        return redirect(url_for('home'))
    logger.info("Rendering dashboard")
    return render_template('dashboard.html')

@app.route('/assignments', methods=['GET', 'POST'])
def assignments():
    if 'token' not in session:
        logger.info("Access to assignments denied - no valid session")
        return redirect(url_for('home'))

    if request.method == 'POST':
        file = request.files.get('assignment')
        if file and file.filename != '':
            filename = secure_filename(file.filename)
            file_content = file.read()  # Read file content as binary

            # Send binary data to gRPC service
            logger.info(f"Submitting assignment: {filename}")
            try:
                stub.Post(lms_pb2.PostRequest(token=session['token'], type="assignment", data=file_content))
                logger.info("Assignment submitted successfully")
                return redirect(url_for('assignments'))
            except grpc.RpcError as e:
                logger.error(f"gRPC error: {e.code()} - {e.details()}")
                return "Failed to submit assignment", 500

    try:
        response = stub.Get(lms_pb2.GetRequest(token=session['token'], type="assignments"))
        logger.info("Assignments retrieved")
        return render_template('assignments.html', assignments=response.items)
    except grpc.RpcError as e:
        logger.error(f"gRPC error: {e.code()} - {e.details()}")
        return "Failed to retrieve assignments", 500

@app.route('/grades')
def grades():
    if 'token' not in session:
        logger.info("Access to grades denied - no valid session")
        return redirect(url_for('home'))
    response = stub.Get(lms_pb2.GetRequest(token=session['token'], type="grades"))
    logger.info("Grades retrieved")
    return render_template('grades.html', grades=response.items)

@app.route('/feedback', methods=['GET', 'POST'])
def feedback():
    if 'token' not in session:
        logger.info("Access to feedback denied - no valid session")
        return redirect(url_for('home'))
    if request.method == 'POST':
        data = request.form['feedback']
        logger.info("Submitting feedback")
        stub.Post(lms_pb2.PostRequest(token=session['token'], type="feedback", data=data))
        logger.info("Feedback submitted successfully")
        return redirect(url_for('feedback'))
    response = stub.Get(lms_pb2.GetRequest(token=session['token'], type="feedback"))
    logger.info("Feedback retrieved")
    return render_template('feedback.html', feedback=response.items)

@app.route('/logout')
def logout():
    token = session.pop('token', None)
    if token:
        logger.info(f"Logout request for token: {token}")
        stub.Logout(lms_pb2.LogoutRequest(token=token))
        logger.info("Logout successful")
    return redirect(url_for('home'))

if __name__ == '__main__':
    logger.info("Starting LMS Client")
    app.run(host='0.0.0.0', port=5000)
