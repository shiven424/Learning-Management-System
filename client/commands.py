import lms_pb2

def execute_command(stub, command):
    if command == "login":
        username = input("Username: ")
        password = input("Password: ")
        response = stub.Login(lms_pb2.LoginRequest(username=username, password=password))
        print(f"Login status: {response.status}, Token: {response.token}")

    elif command == "logout":
        token = input("Token: ")
        response = stub.Logout(lms_pb2.LogoutRequest(token=token))
        print(f"Logout status: {response.status}")

    elif command == "post":
        token = input("Token: ")
        post_type = input("Type (assignment/query): ")
        data = input("Data: ")
        response = stub.Post(lms_pb2.PostRequest(token=token, type=post_type, data=data))
        print(f"Post status: {response.status}")

    elif command == "get":
        token = input("Token: ")
        get_type = input("Type (assignments/queries/materials): ")
        response = stub.Get(lms_pb2.GetRequest(token=token, type=get_type))
        print(f"Get status: {response.status}, Items: {response.items}")

    else:
        print("Unknown command")
