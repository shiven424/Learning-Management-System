from config import logger
from flask import Blueprint, request, redirect, url_for, render_template, session, jsonify
from grpc_client import grpc_client
from werkzeug.utils import secure_filename
import grpc
import lms_pb2

bp = Blueprint('assignment', __name__, static_folder='../static/react', template_folder='../static/react')

@bp.route('/api/assignments', methods=['GET', 'POST'])
def assignments():
    if 'token' not in session:
        return jsonify({"error": "Unauthorized access."}), 401

    if request.method == 'POST':
        return handle_assignments_post()
    return render_assignments_get()

def handle_assignments_post():
    if session['role'] == 'teacher':
        data = request.json  # Parse JSON data from the frontend
        # Handle grading
        grade = data.get('grade')
        assignment_id = data.get('assignmentId')
        
        if grade:
            try:
                response = grpc_client.stub.Post(lms_pb2.PostRequest(
                    token=session['token'],
                    assignment_update=lms_pb2.AssignmentUpdate(
                        assignment_id=assignment_id,
                        grade=grade
                    )
                ))
                if response.status != "Assignment grade updated successfully":
                    logger.warning(f"Failed to post grade: {response.status}")
            except grpc.RpcError as e:
                return grpc_client.handle_grpc_error(e)

        # Handle feedback
        feedback_text = data.get('feedback')
        if feedback_text:
            try:
                response = grpc_client.stub.Post(lms_pb2.PostRequest(
                    token=session['token'],
                    assignment_update=lms_pb2.AssignmentUpdate(
                        assignment_id=assignment_id,
                        feedback_text=feedback_text
                    )
                ))
                if response.status != "Assignment feedback updated successfully":
                    logger.warning(f"Failed to post feedback: {response.status}")
            except grpc.RpcError as e:
                return grpc_client.handle_grpc_error(e)
    
    elif session['role'] == 'student':
        # Student uploads an assignment
        selected_teacher = request.form.get('teacher')  # Fetch the selected teacher from the dropdown
        if 'assignment' in request.files:
            uploaded_file = request.files['assignment']
            file_content = uploaded_file.read()

            if uploaded_file.filename != '':
                # Upload the assignment file to the server
                file_save_response = grpc_client.stub.Upload(lms_pb2.UploadFileRequest(
                    token=session['token'],
                    filename=secure_filename(uploaded_file.filename),
                    data=file_content
                ))

                if file_save_response.status == "success":
                    # Submit the assignment with the associated teacher
                    response = grpc_client.stub.Post(lms_pb2.PostRequest(
                        token=session['token'],
                        assignment=lms_pb2.AssignmentData(
                            student_name=session['username'],
                            teacher_name=selected_teacher,  # Assign the selected teacher
                            filename=secure_filename(uploaded_file.filename),
                            file_path=file_save_response.file_path,
                            file_id=str(file_save_response.file_id)
                        )
                    ))
                    if response.status == "Assignment submitted successfully":
                        logger.info(f"Assignment data uploaded successfully: {uploaded_file.filename}")
                        return jsonify({"message": "Assignment submitted successfully"}), 200
                    else:
                        logger.error(f"Failed to submit assignment: {response.status}")
                        return jsonify({"error": response.status}), 400
                else:
                    logger.error(f"File could not be uploaded: {file_save_response.status}")
                    return jsonify({"error": file_save_response.status}), 400
            else:
                logger.warning("No file uploaded.")
                return jsonify({"error": "No file uploaded."}), 400
    
    return jsonify({"message": "Assignments processed successfully."}), 200

def render_assignments_get():
    try:
        role = session['role']
        username = session['username']
        
        if role == 'teacher':
            request_data = lms_pb2.AssignmentData(teacher_name=username)
        elif role == 'student':
            teachers = grpc_client.fetch_teachers_via_grpc()  # Fetch teachers for the student to select from
            request_data = lms_pb2.AssignmentData(student_name=username)
        else:
            return jsonify({"error": "Unknown role"}), 400

        # Fetch assignments
        response = grpc_client.stub.Get(lms_pb2.GetRequest(
            token=session['token'],
            assignment=request_data
        ))

        assignments = []
        for item in response.assignment_items:
            if item.teacher_name == username or item.student_name == username:
                assignments.append({
                    'assignment_id': item.assignment_id,
                    'student_name': item.student_name,
                    'teacher_name': item.teacher_name,
                    'filename': item.filename,
                    'file_path': item.file_path,
                    'grade': item.grade,
                    'feedback_text': item.feedback_text,
                    'submission_date': item.submission_date,
                })
        if role == 'student':
            return jsonify({"assignments": assignments, "role": role, "teachers": teachers}), 200
        else:
            return jsonify({"assignments": assignments, "role": role}), 200        
    
    except grpc.RpcError as e:
        return grpc_client.handle_grpc_error(e)