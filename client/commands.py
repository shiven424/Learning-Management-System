import lms_pb2
import lms_pb2_grpc
import os

# Helper function to read the token
def read_token():
    try:
        with open('token.txt', 'r') as f:
            return f.read().strip()
    except FileNotFoundError:
        print("No token found. Please login first.")
        return None

# Function to execute commands based on user input
def execute_command(stub, command):
    if command == "login":
        username = input("Username: ")
        password = input("Password: ")
        response = stub.Login(lms_pb2.LoginRequest(username=username, password=password))
        print(f"Login status: {response.status}, Token: {response.token}")
        if response.status == "Success":
            with open('token.txt', 'w') as f:
                f.write(response.token)

    elif command == "logout":
        token = read_token()
        if token:
            response = stub.Logout(lms_pb2.LogoutRequest(token=token))
            print(f"Logout status: {response.status}")
            if response.status == "Logged out successfully":
                os.remove('token.txt')

    elif command == "post":
        token = read_token()
        if token:
            post_type = input("Type (assignment/grade/feedback): ").strip().lower()
            if post_type == "assignment":
                student_id = input("Student ID: ")
                filename = input("Filename: ")
                # Read file data
                try:
                    with open(filename, 'rb') as file:
                        file_data = file.read()
                    assignment_data = lms_pb2.AssignmentData(student_id=student_id, filename=filename, file_data=file_data)
                    response = stub.Post(lms_pb2.PostRequest(token=token, assignment=assignment_data))
                    print(f"Post status: {response.status}")
                except FileNotFoundError:
                    print("File not found. Please check the filename.")

            elif post_type == "grade":
                assignment_id = input("Assignment ID: ")
                grade = input("Grade: ")
                comments = input("Comments: ")
                grade_data = lms_pb2.GradeData(assignment_id=assignment_id, grade=grade, comments=comments)
                response = stub.Post(lms_pb2.PostRequest(token=token, grade=grade_data))
                print(f"Post status: {response.status}")

            elif post_type == "feedback":
                student_id = input("Student ID: ")
                assignment_id = input("Assignment ID: ")
                feedback_text = input("Feedback Text: ")
                feedback_data = lms_pb2.FeedbackData(student_id=student_id, assignment_id=assignment_id, feedback_text=feedback_text)
                response = stub.Post(lms_pb2.PostRequest(token=token, feedback=feedback_data))
                print(f"Post status: {response.status}")

            else:
                print("Invalid post type. Choose assignment, grade, or feedback.")

    elif command == "get":
        token = read_token()
        if token:
            get_type = input("Type (assignments/grades/feedback): ").strip().lower()
            if get_type == "assignments":
                student_id = input("Student ID (leave blank to fetch your assignments): ")
                request = lms_pb2.GetAssignmentsRequest(student_id=student_id)
                response = stub.Get(lms_pb2.GetRequest(token=token, assignments=request))
                print(f"Get status: {response.status}")
                for item in response.items:
                    print(f"Assignment: {item.data}")

            elif get_type == "grades":
                student_id = input("Student ID (leave blank to fetch your grades): ")
                request = lms_pb2.GetGradesRequest(student_id=student_id)
                response = stub.Get(lms_pb2.GetRequest(token=token, grades=request))
                print(f"Get status: {response.status}")
                for item in response.items:
                    print(f"Grade: {item.data}")

            elif get_type == "feedback":
                student_id = input("Student ID (leave blank to fetch your feedback): ")
                request = lms_pb2.GetFeedbackRequest(student_id=student_id)
                response = stub.Get(lms_pb2.GetRequest(token=token, feedback=request))
                print(f"Get status: {response.status}")
                for item in response.items:
                    print(f"Feedback: {item.data}")

            else:
                print("Invalid get type. Choose assignments, grades, or feedback.")

    else:
        print("Unknown command. Please use login, logout, post, or get.")
