from flask import Blueprint, request, redirect, url_for, render_template, session
import lms_pb2
import grpc
from grpc_client import stub, handle_grpc_error
from werkzeug.utils import secure_filename
from config import logger
from grpc_client import fetch_teachers_via_grpc
bp = Blueprint('assignments', __name__)

@bp.route('/assignments', methods=['GET', 'POST'])
def assignments():
    if 'token' not in session:
        return redirect(url_for('auth.home'))
    if request.method == 'POST':
        return handle_assignments_post()
    return render_assignments_get()

def handle_assignments_post():
    if session['role'] == 'teacher':
        for key, value in request.form.items():
            if key.startswith('grade_'):
                assignment_id_cleaned = key[len('grade_'):]  # This extracts the assignment_id
                grade = value  # The grade should be stored in the value

                if not grade:
                    logger.warning(f"Grade is empty for assignment: {assignment_id_cleaned}")
                
                try:
                    # Send the grade via gRPC
                    response = stub.Post(lms_pb2.PostRequest(
                        token=session['token'],
                        assignment_update=lms_pb2.AssignmentUpdate(
                            assignment_id=assignment_id_cleaned,
                            grade=grade  # Ensure this is passed correctly
                        )
                    ))
                    if response.status != "Assignment grade updated successfully":
                        logger.warning(f"Failed to post grade: {response.status}")
                except grpc.RpcError as e:
                    return handle_grpc_error(e)

        feedbacks = {k: v for k, v in request.form.items() if k.startswith('feedback_')}
        for assignment_id, feedback_text in feedbacks.items():
            assignment_id_cleaned = assignment_id[len('feedback_'):]
            try:
                # Sending feedback
                response = stub.Post(lms_pb2.PostRequest(
                    token=session['token'],
                    assignment_update=lms_pb2.AssignmentUpdate(
                        assignment_id=assignment_id_cleaned,
                        feedback_text=feedback_text
                    )
                ))
                if response.status != "Assignment feedback updated successfully":
                    logger.warning(f"Failed to post feedback: {response.status}")
            except grpc.RpcError as e:
                return handle_grpc_error(e)
    
    elif session['role'] == 'student':
        # Student uploads an assignment
        selected_teacher = request.form.get('teacher')  # Fetch the selected teacher from the dropdown
        if 'assignment' in request.files:
            uploaded_file = request.files['assignment']
            file_content = uploaded_file.read()

            if uploaded_file.filename != '':
                # Upload the assignment file to the server
                file_save_response = stub.Upload(lms_pb2.UploadFileRequest(
                    token=session['token'],
                    filename=secure_filename(uploaded_file.filename),
                    data=file_content
                ))

                if file_save_response.status == "success":
                    # Submit the assignment with the associated teacher
                    response = stub.Post(lms_pb2.PostRequest(
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
                    else:
                        logger.error(f"Failed to submit assignment: {response.status}")
                else:
                    logger.error(f"File could not be uploaded: {file_save_response.status}")
            else:
                logger.warning("No file uploaded.")
    
    return redirect(url_for('assignments'))

def render_assignments_get():
    try:
        role = session['role']
        username = session['username']
        
        if role == 'teacher':
            teachers = []  # No teachers list needed if the user is a teacher
            request_data = lms_pb2.AssignmentData(teacher_name=username)
        elif role == 'student':
            teachers = fetch_teachers_via_grpc()  # Fetch teachers for the student to select from
            request_data = lms_pb2.AssignmentData(student_name=username)
        else:
            return "Unknown role", 400

        # Fetch assignments
        response = stub.Get(lms_pb2.GetRequest(
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

        return render_template('assignments.html', assignments=assignments, role=role, teachers=teachers)
    
    except grpc.RpcError as e:
        return handle_grpc_error(e)