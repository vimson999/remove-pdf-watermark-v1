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

    # Configure Logging
    if not app.debug and not app.testing:
        # Production Logging
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
        app.logger.addHandler(file_handler)
        app.logger.setLevel(logging.INFO)
        app.logger.info('PDF Processor startup')
    else:
        # Development/Test Logging
        logging.basicConfig(level=logging.INFO)

    # Register Blueprints
    from app.routes.main import main_bp
    app.register_blueprint(main_bp)

    return app