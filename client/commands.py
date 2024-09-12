import lms_pb2
import os

def execute_command(stub, command):
    if command == "login":
        username = input("Username: ")
        password = input("Password: ")
        response = stub.Login(lms_pb2.LoginRequest(username=username, password=password))
        print(f"Login status: {response.status}, Token: {response.token}")
        # Save the token for subsequent requests
        with open('token.txt', 'w') as f:
            f.write(response.token)

    elif command == "logout":
        with open('token.txt', 'r') as f:
            token = f.read().strip()
        response = stub.Logout(lms_pb2.LogoutRequest(token=token))
        print(f"Logout status: {response.status}")
        # Clear the token file
        os.remove('token.txt')

    elif command == "post":
        with open('token.txt', 'r') as f:
            token = f.read().strip()
        post_type = input("Type (assignment/query): ")
        data = input("Data: ")
        response = stub.Post(lms_pb2.PostRequest(token=token, type=post_type, data=data))
        print(f"Post status: {response.status}")

    elif command == "get":
        with open('token.txt', 'r') as f:
            token = f.read().strip()
        get_type = input("Type (assignments/queries/materials): ")
        response = stub.Get(lms_pb2.GetRequest(token=token, type=get_type))
        print(f"Get status: {response.status}, Items: {response.items}")

    else:
        print("Unknown command")
