from flask import Blueprint, render_template, request, redirect, url_for, session
import lms_pb2
import grpc
from grpc_client import stub, handle_grpc_error

bp = Blueprint('auth', __name__)

@bp.route('/')
def home():
    return render_template('login.html')

@bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        role = request.form['role']
        name = request.form.get('name', '')
        try:
            response = stub.Register(lms_pb2.RegisterRequest(username=username, password=password, role=role, name=name))
            if response.status == "Registration successful":
                return redirect(url_for('auth.home'))
            return "Registration Failed: User already exists", 400
        except grpc.RpcError as e:
            return handle_grpc_error(e)
    return render_template('register.html')

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        try:
            response = stub.Login(lms_pb2.LoginRequest(username=username, password=password))
            if response.status == "Success":
                session['token'] = response.token
                session['role'] = response.role
                session['username'] = username
                session['logged_in'] = True
                return redirect(url_for('dashboard.dashboard'))
            return render_template('login.html', error="Incorrect username or password"), 401
        except grpc.RpcError as e:
            return handle_grpc_error(e)
    return render_template('login.html')

@bp.route('/logout')
def logout():
    token = session.pop('token', None)
    if token:
        try:
            stub.Logout(lms_pb2.LogoutRequest(token=token))
            session.clear()
        except grpc.RpcError as e:
            handle_grpc_error(e)
    return redirect(url_for('auth.home'))


def check_session():
    if 'token' not in session:
        return False
    return True
