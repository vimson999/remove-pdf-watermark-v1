from flask import Flask
from config import config
import os
import logging
from logging.handlers import RotatingFileHandler

def create_app(config_name='default'):
    app = Flask(__name__)
    app.config.from_object(config[config_name])

    # Ensure upload/download directories exist
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(app.config['DOWNLOAD_FOLDER'], exist_ok=True)

    # Configure Logging (Persist to file in ALL environments)
    if not os.path.exists('logs'):
        os.mkdir('logs')

    file_handler = RotatingFileHandler(
        'logs/app.log', 
        maxBytes=app.config.get('LOG_FILE_MAX_BYTES', 10240000), 
        backupCount=app.config.get('LOG_FILE_BACKUP_COUNT', 10)
    )
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    ))
    file_handler.setLevel(logging.INFO)
    
    # Add file handler to app logger
    app.logger.addHandler(file_handler)
    app.logger.setLevel(logging.INFO)
    
    # In development, also log to console (if not already handled by Flask's default)
    if app.debug:
        stream_handler = logging.StreamHandler()
        stream_handler.setLevel(logging.INFO)
        app.logger.addHandler(stream_handler)

    app.logger.info('PDF Processor startup')

    # Register Blueprints
    from app.routes.main import main_bp
    app.register_blueprint(main_bp)

    return app