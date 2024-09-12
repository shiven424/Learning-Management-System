import grpc
from concurrent import futures
import lms_pb2_grpc
from lms_server import LMSServer

def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    lms_pb2_grpc.add_LMSServicer_to_server(LMSServer(), server)
    server.add_insecure_port('[::]:50051')
    server.start()
    print("LMS Server running on port 50051...")
    server.wait_for_termination()

if __name__ == '__main__':
    serve()
