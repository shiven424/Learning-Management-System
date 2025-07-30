from flask import Flask
from config import Config
from routes import auth, assignment, feedback, course_material, dashboard, forum, file_transfer

app = Flask(__name__, static_folder='static/react')
app.config.from_object(Config)

# Register Blueprints
app.register_blueprint(dashboard.bp)
app.register_blueprint(auth.bp)
app.register_blueprint(file_transfer.bp)
app.register_blueprint(assignment.bp)
app.register_blueprint(feedback.bp)
app.register_blueprint(course_material.bp)
app.register_blueprint(forum.bp)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
