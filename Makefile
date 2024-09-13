# Makefile for Docker operations

# Variables
DOCKER_COMPOSE = docker-compose

# Default target
.PHONY: all
all: build up

# Build Docker images
.PHONY: build
build:
	$(DOCKER_COMPOSE) build --no-cache

# Spin up containers
.PHONY: up
up:
	$(DOCKER_COMPOSE) up -d

# Attach to the client container for interaction
.PHONY: client-attach
client-attach:
	$(DOCKER_COMPOSE) exec lms_client /bin/bash

server-attach:
	$(DOCKER_COMPOSE) exec lms_server /bin/bash

# Stop running containers
.PHONY: stop
stop:
	$(DOCKER_COMPOSE) stop

# Remove stopped containers
.PHONY: down
down:
	$(DOCKER_COMPOSE) down

# Cleanup dangling images and containers
.PHONY: clean
clean:
	$(DOCKER_COMPOSE) down --rmi all --volumes --remove-orphans

# Restart containers
.PHONY: restart
restart: stop up

# Display logs of the running services
.PHONY: logs
logs:
	$(DOCKER_COMPOSE) logs -f lms_client lms_server

.PHONY: rebuild-server
rebuild-server: build
	$(DOCKER_COMPOSE) up -d lms_server

# Rebuild and redeploy the client
.PHONY: rebuild-client
rebuild-client: build
	$(DOCKER_COMPOSE) up -d lms_client


# Help message for using the Makefile
.PHONY: help
help:
	@echo "Makefile Usage:"
	@echo "  make build          - Build the Docker images"
	@echo "  make up             - Start the containers in detached mode"
	@echo "  make client-attach  - Attach to the lms_client container"
	@echo "  make stop           - Stop the running containers"
	@echo "  make down           - Remove stopped containers"
	@echo "  make clean          - Remove containers, images, volumes, and orphans"
	@echo "  make restart        - Restart the containers"
	@echo "  make logs           - Display the logs of the running services"
	@echo "  make help           - Show this help message"
