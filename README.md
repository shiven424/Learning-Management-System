# LMS
Learning Management System with LLM integration
distributed_lms/
│
├── Dockerfile.server
├── Dockerfile.client
├── docker-compose.yml
├── proto/
│   └── lms.proto
├── server/
│   ├── server.py
│   ├── lms_server.py
│   ├── authentication.py
│   └── database.py        # New: MongoDB connection and operations
├── client/
│   ├── client.py
│   ├── ui.py
│   ├── templates/
│   └── static/
└── requirements.txt
