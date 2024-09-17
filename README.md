# Learning Management System (LMS)

This is a microservices-based Learning Management System (LMS) built using gRPC for communication between services, Flask for file uploads and static content, and MongoDB for database storage. The services are containerized using Docker.

## Prerequisites

Before running the system, ensure that you have the following installed:

- Docker (version 19.03.0+)
- Docker Compose (version 1.25.0+)

## Folder Structure

```
├── client/
│   ├── ui.py               # Client UI for interacting with LMS services
│   ├── templates/          # HTML templates for the Flask UI
│   ├── static/             # Static files like CSS, JS for the Flask UI
├── server/
│   ├── lms_server.py       # gRPC server handling LMS operations
│   ├── authentication.py   # Authentication and session management
│   ├── database.py         # MongoDB operations (user registration, assignments, etc.)
├── proto/
│   ├── lms.proto           # Protocol Buffers file defining gRPC services
├── requirements.txt        # Python dependencies
├── Dockerfile.server       # Dockerfile for the gRPC server
├── Dockerfile.client       # Dockerfile for the client and Flask app
├── docker-compose.yml      # Docker Compose configuration
└── README.md               # Project documentation
```

## Setup Instructions

### Step 1: Clone the Repository

Start by cloning the repository to your local machine:

```bash
git clone <repository-url>
cd <repository-folder>
```

### Step 2: Build and Run the Containers

Run the following command to build and start all services (gRPC server, client Flask app, and MongoDB) using Docker Compose:

```bash
docker-compose up --build
```

This will:

- Build the Docker image for the gRPC server (`lms_server`).
- Build the Docker image for the client Flask app (`lms_client`).
- Start a MongoDB container.

### Step 3: Access the Services

Once the containers are running, you can access the services as follows:

- **Flask App (Client UI)**: Navigate to [http://localhost:5000](http://localhost:5000) in your browser.
- **gRPC Server**: The gRPC server is running on port 50051 for internal communication between services.
- **MongoDB**: MongoDB is exposed on port 27017.

### Step 4: Interact with the LMS

- **User Registration**: Register users via the client UI or gRPC endpoints.
- **Submit Assignments**: Students can submit assignments through the client UI or via gRPC.
- **Grade Assignments**: Teachers can grade assignments via gRPC requests.
- **View Feedback**: Students and teachers can retrieve feedback on assignments.

### Step 5: Stopping the Containers

To stop all services, press `Ctrl + C` in the terminal running the Docker Compose process, or use the following command in a new terminal:

```bash
docker-compose down
```

### Step 6: Cleaning Up

To remove the containers, volumes, and networks created by Docker Compose, run:

```bash
docker-compose down --volumes --remove-orphans
```

## File Overview

### Dockerfile.client

Defines the client service (Flask App):

- Installs dependencies from `requirements.txt`.
- Compiles the gRPC stubs from `proto/lms.proto`.
- Runs the Flask UI (`ui.py`) on startup.

### Dockerfile.server

Defines the gRPC server service:

- Installs necessary Python dependencies.
- Compiles gRPC stubs.
- Starts the gRPC server on port 50051.

### docker-compose.yml

Docker Compose orchestrates the following services:

- `lms_server`: gRPC server for managing LMS functionality.
- `lms_client`: Flask app acting as a client for the LMS.
- `mongo`: MongoDB instance for data storage.

### proto/lms.proto

Defines the protocol buffers file used by the gRPC server and client for communication. It includes messages and services for:

- User registration and login.
- Assignment submission and grading.
- Feedback management.
- Course material upload and retrieval.

## Environment Variables

The following environment variables are used in the system:

- `MONGO_URI`: MongoDB connection string. Example: `mongodb://mongo:27017/lms_db`.
- `FILE_STORAGE_DIR`: Directory to store uploaded files (used in Flask for file uploads).

Both are set by default in `docker-compose.yml`.

## gRPC API Overview

Here is a quick overview of the key gRPC endpoints:

- **Register**: Register a new user (student/teacher).
- **Login**: Login and receive an authentication token.
- **Post Assignment**: Submit an assignment.
- **Get Assignments**: Retrieve assignments (for students or teachers).
- **Post Feedback**: Submit feedback on assignments.
- **Get Feedback**: Retrieve feedback for a student or teacher.
- **Upload Course Material**: Upload teaching materials.
- **Get Course Materials**: Retrieve course materials by course or teacher.

## License

This project is licensed under the MIT License. See the `LICENSE` file for details.

---