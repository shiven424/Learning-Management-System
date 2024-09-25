from flask import Blueprint, request, render_template, redirect, url_for, session
import grpc
import lms_pb2
from config import logger, stub
from grpc_client import handle_grpc_error, fetch_students_via_grpc
from routes.auth import check_session
bp = Blueprint('feedback', __name__)

@bp.route('/feedback', methods=['GET', 'POST'])
def feedback():
    if not check_session():
        return redirect(url_for('auth.home'))
    
    if request.method == 'POST':
        feedback_text = request.form['feedback']
        selected_student = request.form.get('student')  # Fetch the selected student

        if session['role'] == 'teacher' and not selected_student:
            # Error handling if no student is selected
            try:
                students = fetch_students_via_grpc(stub)  # Fetch students via gRPC
                return render_template('feedback.html', error="Please select a student.", students=students, role=session['role'])
            except Exception as e:
                logger.error(f"Error fetching students: {e}")
                return render_template('feedback.html', error="Failed to fetch students.", role=session['role'])

        try:
            # Submit feedback to gRPC service
            response = stub.Post(lms_pb2.PostRequest(
                token=session['token'],
                student_feedback=lms_pb2.FeedbackData(
                    feedback_text=feedback_text,
                    student_name=selected_student if session['role'] == 'teacher' else session['username']
                )
            ))
            if response.status == "Student feedback submitted successfully":
                return redirect(url_for('feedback.feedback'))
            else:
                students = fetch_students_via_grpc(stub)  # Fetch students again for the re-render
                return render_template('feedback.html', error="Failed to submit feedback.", students=students, role=session['role'])
        except grpc.RpcError as e:
            return handle_grpc_error(e)

    return render_feedback_get()

def render_feedback_get():
    try:
        # Get the user's role and username from the session
        role = session['role']
        username = session['username']

        if role == 'teacher':
            students = fetch_students_via_grpc(stub)  # Fetch students via gRPC
            request_data = lms_pb2.FeedbackData(teacher_name=username)
        elif role == 'student':
            students = []  # No students list needed if the user is a student
            request_data = lms_pb2.FeedbackData(student_name=username)
        else:
            return "Unknown role", 400

        # Send the gRPC request to get feedback
        response = stub.Get(lms_pb2.GetRequest(
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
        return render_template('feedback.html', feedbacks=feedbacks, role=role, students=students)

    except grpc.RpcError as e:
        return handle_grpc_error(e)