from flask import Blueprint, render_template, request, redirect, url_for, session, send_from_directory, jsonify
from grpc_client import grpc_client
import grpc
import lms_pb2
import logging
import os
bp = Blueprint('auth', __name__, static_folder='../static/react', template_folder='../static/react')

@bp.route('/', defaults={'path': ''})
@bp.route('/<path:path>')
def serve_react(path):
    # Ensure API routes are not served by React
    if path.startswith('api/'):
        return jsonify({"error": "API Route not found"}), 404
    
    # Serve React build files if they exist
    if path != "" and os.path.exists(os.path.join(bp.static_folder, path)):
        return send_from_directory(bp.static_folder, path)
    
    # Fallback: Serve React's index.html for any other non-API route
    return send_from_directory(bp.static_folder, 'index.html')

@bp.route('/api/register', methods=['POST'])
def register():
    data = request.json  # Extract the JSON data
    if not data:
        return jsonify({"error": "Invalid data"}), 400
    
    username = data.get('username')
    password = data.get('password')
    role = data.get('role')
    name = data.get('name', '')

    if not username or not password or not role:
        return jsonify({"error": "Missing required fields"}), 400

    try:
        response = grpc_client.stub.Register(lms_pb2.RegisterRequest(username=username, password=password, role=role, name=name))
            
        if response.status == "Registration successful":
            return jsonify({"message": "Registration successful", "redirect": "/login"}), 200
        return jsonify({"message": "Registration Failed: User already exists"}), 400
        
    except grpc.RpcError as e:
        return grpc_client.handle_grpc_error(e)

@bp.route('/api/login', methods=['POST'])
def login():
    data = request.json  # Extract the JSON data
    if not data:
        return jsonify({"error": "Invalid data"}), 400
    
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({"error": "Missing required fields"}), 400
        
    try:
        logging.info(f"{grpc_client.leader_address}")
        response = grpc_client.stub.Login(lms_pb2.LoginRequest(username=username, password=password))
            
        if response.status == "Success":
            session['token'] = response.token
            session['role'] = response.role
            session['username'] = username
            session['logged_in'] = True
            return jsonify({"message": "Login successful", "role": response.role, "token": response.token, "username": username}), 200
        return jsonify({"message": "Incorrect username or password"}), 401
    except grpc.RpcError as e:
        return grpc_client.handle_grpc_error(e)

@bp.route('/api/logout', methods=['POST'])
def logout():
    token = session.pop('token', None)
    if not token:
        return jsonify({"message": "User not logged in"}), 400
    
    try:
        grpc_client.stub.Logout(lms_pb2.LogoutRequest(token=token))
        session.clear()
        return jsonify({"message": "Logout successful"}), 200
    except grpc.RpcError as e:
        return grpc_client.handle_grpc_error(e)

@bp.route('/api/session')
def check_session():
    if 'token' in session:
        # Check if the session token is valid and not expired
        try:
            return jsonify({
                "logged_in": True, 
                "username": session.get('username'), 
                "role": session.get('role'),  
                "token": session.get('token')
            }), 200
        except Exception as e:
            print(f"Session check failed: {str(e)}")
            return jsonify({"logged_in": False, "error": "Session invalid or expired"}), 401
    return jsonify({"logged_in": False}), 401
