from config import logger
from flask import Blueprint, request, render_template, redirect, url_for, session, jsonify
from grpc_client import grpc_client
from routes.auth import check_session
import grpc
import lms_pb2

bp = Blueprint('feedback', __name__)

@bp.route('/api/feedback', methods=['GET', 'POST'])
def feedback():
    if not check_session():
        return jsonify({"error": "Unauthorized"}), 401
    
    if request.method == 'POST':
        feedback_text = request.json.get('feedback')
        selected_student = request.json.get('student')

        if session['role'] == 'teacher' and not selected_student:
            # Error handling if no student is selected
            try:
                return jsonify({"error": "Please select a student."}), 400
            except Exception as e:
                logger.error(f"Error fetching students: {e}")
                return jsonify({"error": "Failed to fetch students."}), 500

        try:
            # Submit feedback to gRPC service
            response = grpc_client.stub.Post(lms_pb2.PostRequest(
                token=session['token'],
                student_feedback=lms_pb2.FeedbackData(
                    feedback_text=feedback_text,
                    student_name=selected_student if session['role'] == 'teacher' else session['username']
                )
            ))
            if response.status == "Student feedback submitted successfully":
                return jsonify({"success": True}), 200
            else:
                return jsonify({"success": False}), 400
        except grpc.RpcError as e:
            return grpc_client.handle_grpc_error(e)

    return render_feedback_get()

def render_feedback_get():
    try:
        # Get the user's role and username from the session
        role = session['role']
        username = session['username']

        if role == 'teacher':
            students = grpc_client.fetch_students_via_grpc()  # Fetch students via gRPC
            request_data = lms_pb2.FeedbackData(teacher_name=username)
        elif role == 'student':
            students = []  # No students list needed if the user is a student
            request_data = lms_pb2.FeedbackData(student_name=username)
        else:
            return "Unknown role", 400

        # Send the gRPC request to get feedback
        response = grpc_client.stub.Get(lms_pb2.GetRequest(
            token=session['token'],
            feedback=request_data
        ))

        feedbacks = []
        for item in response.feedback_items:
            if item.teacher_name == username or item.student_name == username:
                feedbacks.append({
                    'feedback_id': item.feedback_id,
                    'feedback_text': item.feedback_text,
                    'student_name': item.student_name,
                    'teacher_name': item.teacher_name,
                    'submission_date': item.submission_date,
                })

        # logger.info(f"Feedbacks fetched successfully {feedbacks}")
        
        # Render the feedback template, passing feedbacks, role, and students
        return jsonify({"feedbacks": feedbacks, "role": role, "students": students}), 200

    except grpc.RpcError as e:
        return grpc_client.handle_grpc_error(e)