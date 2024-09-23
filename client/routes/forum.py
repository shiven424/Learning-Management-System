from flask import Blueprint, request, redirect, url_for, render_template, session
import lms_pb2
import grpc
from grpc_client import stub, handle_grpc_error
from werkzeug.utils import secure_filename
from config import logger
from grpc_client import fetch_teachers_via_grpc
bp = Blueprint('assignments', __name__)

@bp.route('/forum', methods=['GET', 'POST'])