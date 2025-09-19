"""import atexit
from flask import Flask
from config import Config
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from app.queue_system import start_workers, task_queue

db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'

def create_app(config_class=Config):
    #Creates and configures an instance of the Flask application.
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    login_manager.init_app(app)

    from app.auth import bp as auth_bp
    app.register_blueprint(auth_bp)

    from app.main import bp as main_bp
    app.register_blueprint(main_bp)

    # Start the background worker threads
    if app.config.get('WERKZEUG_RUN_MAIN') != 'true' and not app.testing:
        start_workers()

        # A function to wait for the queue to finish when the app exits
        def wait_for_queue():
            task_queue.join()
        atexit.register(wait_for_queue)

    return app

from app.models import User 

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

"""

import atexit
from flask import Flask
from config import Config
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
# REMOVED: from app.queue_system import start_workers, task_queue
import os

db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    login_manager.init_app(app)

    # ... (blueprint registration is the same) ...
    from app.auth import bp as auth_bp
    app.register_blueprint(auth_bp)
    from app.main import bp as main_bp
    app.register_blueprint(main_bp)
    from app.admin import bp as admin_bp
    app.register_blueprint(admin_bp)


    from app.queue_system import start_workers, task_queue
    # We check the environment variable to ensure this runs only in the main process
    if os.environ.get('WERKZEUG_RUN_MAIN'):
        start_workers(app) # <-- PASS THE 'app' OBJECT HERE

        def wait_for_queue():
            task_queue.join()
        atexit.register(wait_for_queue)

    return app

from app.models import User 

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))
