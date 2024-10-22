from config import logger, FILE_STORAGE_DIR
from flask import  session, send_file, Blueprint
from grpc_client import grpc_client
from urllib.parse import quote, unquote
from werkzeug.utils import secure_filename
import grpc
import io
import lms_pb2
import os

bp = Blueprint('file_transfer', __name__)



@bp.route('/download/<path:file_path>')
def download_file(file_path):
    try:
        # Decode the file path to handle special characters and slashes
        file_path = unquote(file_path)
        
        response = grpc_client.stub.Download(lms_pb2.DownloadFileRequest(
            token=session['token'],
            file_path=file_path
        ))

        if response.status == "success":
            return send_file(
                io.BytesIO(response.data),
                download_name =os.path.basename(file_path),
                as_attachment=True
            )
        else:
            return "File not found", 404

    except grpc.RpcError as e:
        return grpc_client.handle_grpc_error(e)
    

def save_assignment(file):
    filename = secure_filename(file.filename)
    file_path = os.path.join(FILE_STORAGE_DIR, filename)
    file.save(file_path)

def save_course_material(file):
    filename = secure_filename(file.filename)
    file_path = os.path.join(FILE_STORAGE_DIR, filename)
    file.save(file_path)
