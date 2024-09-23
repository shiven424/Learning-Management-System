from flask import Flask
from config import Config
from grpc_client import setup_grpc_client
from routes import auth, assignments, feedback, course_material, dashboard

app = Flask(__name__)
app.config.from_object(Config)

# gRPC Client Setup
setup_grpc_client()

# Register Blueprints
app.register_blueprint(auth.bp)
app.register_blueprint(assignments.bp)
app.register_blueprint(feedback.bp)
app.register_blueprint(course_material.bp)
app.register_blueprint(dashboard.bp)
app.register_blueprint(forum.bp)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
