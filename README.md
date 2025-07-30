# Learning Management System (LMS)

This LMS system now includes a **Raft-based consensus protocol** to ensure reliability and consistency across multiple nodes. Below is the detailed documentation of the new changes and how the system leverages Raft for fault tolerance.

---

## Prerequisites  

Ensure you have the following installed before setting up the system:  

- Docker (version 19.03.0+)  
- Docker Compose (version 1.25.0+)  

---

## Folder Structure  

```  
├── client/
│   ├── ui.py               # Client UI for interacting with LMS services  
│   ├── templates/          # HTML templates for the Flask UI  
│   ├── static/             # Static files like CSS, JS for the Flask UI  
├── server/
│   ├── lms_server.py       # gRPC server handling LMS operations  
│   ├── llm_requests.py     # LLM operations via gRPC and external API calls  
│   ├── authentication.py   # Authentication and session management  
│   ├── database.py         # MongoDB operations  
│   ├── raft.py        # Raft consensus implementation  
├── proto/
│   ├── lms.proto           # Protocol Buffers file defining gRPC services  
├── requirements.txt        # Python dependencies  
├── Dockerfile.server       # Dockerfile for the gRPC server  
├── Dockerfile.client       # Dockerfile for the Flask client  
├── Dockerfile.llm          # Dockerfile for LLM server (Gemma 2B model)  
├── docker-compose.yml      # Docker Compose configuration  
└── README.md               # Project documentation  
```

---

## Raft Protocol Overview  

Raft is a **leader-based consensus algorithm** that ensures the nodes in the system agree on the same state, even in the event of failures. In this LMS system, multiple gRPC nodes run as peers to maintain a consistent state (like assignments, grades, and feedback). If a leader node fails, a new leader is elected among the remaining nodes to continue operations seamlessly.  

### Key Concepts in Raft Implementation:  

- **Leader Election:** If a node does not receive heartbeats from the leader within a certain timeout, it starts an election and becomes a candidate.  
- **Log Replication:** Each operation is logged and replicated across nodes to maintain consistency.  
- **Fault Tolerance:** The system remains operational as long as the majority of nodes are available.  

---

## Raft Node Implementation  

The **RaftNode** class defines the node's behavior, including election, leader role, log replication, and heartbeat management. Below is a summary of the key components:  

### Key Components:  

1. **Node Roles:**  
   - **Follower:** Listens for heartbeats and elections.  
   - **Candidate:** Starts an election if no leader is detected.  
   - **Leader:** Sends heartbeats and manages log replication.  

2. **Log Management:**  
   Each node stores a local log for consistency, saved at `/app/logs/raft.log`. The logs are used to replay operations during recovery.  

3. **Heartbeats:**  
   The leader sends periodic heartbeats to all followers to maintain authority.  

4. **Leader Election:**  
   If no heartbeats are received, nodes start elections to choose a new leader based on majority votes.  

---

## Environment Variables  

- `SERVER_NAME`: Used to identify the current node.  
- `MONGO_URI`: MongoDB connection string (default in `docker-compose.yml`).  
- `FILE_STORAGE_DIR`: Directory for uploaded files.  

---

## Setup Instructions  

### Step 1: Clone the Repository  

```bash  
git clone <repository-url>  
cd <repository-folder>  
```  

### Step 2: Build and Run the Containers  

```bash  
docker-compose up --build  
```  

This will:  

- Build and start the gRPC server nodes and Flask client.  
- Start the MongoDB container and Ollama server.  

---

## Raft Node Configuration  

### Raft Nodes in Docker Compose  

The **`docker-compose.yml`** file sets up multiple gRPC server nodes to act as peers for the Raft protocol. Example configuration:

```yaml  
version: '3'
services:
  lms_server_1:
    build:
      context: ./server
      dockerfile: Dockerfile.server
    environment:
      - SERVER_NAME=lms_server_1
    ports:
      - "5000:5000"

  lms_server_2:
    build:
      context: ./server
      dockerfile: Dockerfile.server
    environment:
      - SERVER_NAME=lms_server_2
    ports:
      - "5001:5000"

  lms_server_3:
    build:
      context: ./server
      dockerfile: Dockerfile.server
    environment:
      - SERVER_NAME=lms_server_3
    ports:
      - "5002:5000"
```

---

## gRPC Endpoints for Raft  

### 1. **RequestVote** (Start Election)  

A node requests votes from peers during elections.  
**Request:**  
```protobuf  
message VoteRequest {  
  int32 term = 1;  
  string candidate_id = 2;  
  int32 last_log_index = 3;  
  int32 last_log_term = 4;  
}  
```  
**Response:**  
```protobuf  
message VoteResponse {  
  bool vote_granted = 1;  
}  
```  

---

### 2. **AppendEntries** (Heartbeat / Log Replication)  

The leader sends heartbeats or log entries to followers.  
**Request:**  
```protobuf  
message AppendEntriesRequest {  
  int32 term = 1;  
  string leader_id = 2;  
  int32 prev_log_index = 3;  
  int32 prev_log_term = 4;  
  repeated LogEntry entries = 5;  
  int32 leader_commit = 6;  
}  
```  

**Response:**  
```protobuf  
message AppendEntriesResponse {  
  bool success = 1;  
}  
```  

---

## Accessing the Services  

- **Client UI:** [http://localhost:5000](http://localhost:5000)  
- **gRPC Servers:** Accessible on ports 5000, 5001, 5002.  

---

## Stopping the Containers  

To stop all services:  

```bash  
docker-compose down  
```  

---

## Cleaning Up  

To remove containers, volumes, and networks:  

```bash  
docker-compose down --volumes --remove-orphans  
```  

---

## License  

This project is licensed under the MIT License. See the `LICENSE` file for details.  

---

By incorporating the **Raft consensus algorithm**, the LMS ensures high availability and consistent state management across nodes, making it robust against failures.