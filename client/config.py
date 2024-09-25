import logging
from grpc_client import setup_grpc_client

FILE_STORAGE_DIR = 'documents'


class Config:
    SECRET_KEY = 'supersecretkey'
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    FILE_STORAGE_DIR = FILE_STORAGE_DIR


logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)



# gRPC Client Setup
channel, stub = setup_grpc_client()