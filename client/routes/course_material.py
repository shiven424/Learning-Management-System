from config import logger
from flask import Blueprint, request, render_template, redirect, url_for, session, jsonify
from grpc_client import grpc_client
from routes.auth import check_session
from werkzeug.utils import secure_filename

import grpc
import lms_pb2

bp = Blueprint('course_material', __name__, static_folder='../static/react', template_folder='../static/react')

@bp.route('/api/course_materials', methods=['GET', 'POST'])
def course_material():
    if not check_session():
        logger.warning("User not authenticated, redirecting to home.")
        return jsonify({"error": "Unauthorized access."}), 401
    
    if request.method == 'POST':
        logger.info("Handling POST request for course material.")
        return handle_course_material_post()
    
    logger.info("Rendering course material page (GET request).")
    return render_course_material_get()

def handle_course_material_post():    
    if session['role'] == 'teacher':
        logger.info(f"POST request received for course material upload by teacher: {session['username']}")
        if 'course_material' in request.files:
            uploaded_file = request.files['course_material']
            file_content = uploaded_file.read()

            logger.debug(f"Uploaded file: {uploaded_file.filename}, size: {len(file_content)} bytes")

            if uploaded_file.filename != '':
                try:
                    # Upload the course_material file to the server
                    logger.info(f"Uploading file: {uploaded_file.filename} to the server.")
                    file_save_response = grpc_client.stub.Upload(lms_pb2.UploadFileRequest(
                        token=session['token'],
                        filename=secure_filename(uploaded_file.filename),
                        data=file_content
                    ))

                    logger.debug(f"File upload response: {file_save_response.status}")

                    if file_save_response.status == "success":
                        # Submit the course_material with the associated teacher
                        logger.info(f"Submitting course material for teacher: {session['username']}")
                        response = grpc_client.stub.Post(lms_pb2.PostRequest(
                            token=session['token'],
                            content=lms_pb2.CourseMaterial(
                                teacher_name=session['username'],
                                filename=secure_filename(uploaded_file.filename),
                                file_path=file_save_response.file_path,
                                file_id=str(file_save_response.file_id)
                            )
                        ))

                        logger.debug(f"Course material submission response: {response.status}")

                        if response.status == "course_materials submitted successfully":
                            logger.info(f"Course material data uploaded successfully: {uploaded_file.filename}")
                            return jsonify({"message": "Course material submitted successfully"}), 200
                        else:
                            logger.error(f"Failed to submit course material: {response.status}")
                            return jsonify({"error": response.status}), 400
                    else:
                        logger.error(f"File could not be uploaded: {file_save_response.status}")
                        return jsonify({"error": file_save_response.status}), 400
                
                except grpc.RpcError as e:
                    logger.error(f"gRPC error during file upload: {e.code()} - {e.details()}")

            else:
                logger.warning("No file uploaded.")
                return jsonify({"error": "No file uploaded."}), 400
        else:
            logger.warning("No course_material file found in request.")
            return jsonify({"error": "No course_material file found in request."}), 400
    
    return jsonify({"message": "Assignments processed successfully."}), 200

def render_course_material_get():
    try:
        # Get the user's role and username from the session
        role = session['role']
        username = session['username']

        if role == 'teacher':
            request_data = lms_pb2.CourseMaterial(teacher_name=username)
        elif role == 'student':
            request_data = lms_pb2.CourseMaterial()
        else:
            return jsonify({"error": "Unknown role"}), 400

        # Send the gRPC request to get course_materials
        response = grpc_client.stub.Get(lms_pb2.GetRequest(
            token=session['token'],
            content=request_data
        ))

        course_materials = []
        
        # Loop through the response and filter based on the role
        for item in response.course_items:
            # If the user is a teacher, only show their own materials
            if role == 'teacher' and item.teacher_name == username:
                course_materials.append({
                    'material_id': item.material_id,
                    'course_name': item.course_name,
                    'filename': item.filename,
                    'file_path': item.file_path,
                    'teacher_name': item.teacher_name,
                    'upload_date': item.upload_date,
                })
            # If the user is a student, show all materials
            elif role == 'student':
                course_materials.append({
                    'material_id': item.material_id,
                    'course_name': item.course_name,
                    'filename': item.filename,
                    'file_path': item.file_path,
                    'teacher_name': item.teacher_name,
                    'upload_date': item.upload_date,
                })

        logger.info(f"Course materials fetched: {course_materials}")              
                
        return jsonify({"course_materials": course_materials, "role": role}), 200
    except grpc.RpcError as e:
        return grpc_client.handle_grpc_error(e)