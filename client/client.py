import grpc
import lms_pb2
import lms_pb2_grpc
from commands import execute_command

def run():
    print("Client has started listening")
    channel = grpc.insecure_channel('lms_server:50051')
    stub = lms_pb2_grpc.LMSStub(channel)
    
    while True:
        command = input("Enter command (login, logout, post, get, exit): ").strip().lower()
        if command == "exit":
            break
        execute_command(stub, command)

if __name__ == '__main__':
    run()
