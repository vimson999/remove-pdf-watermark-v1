import os

class Config:
    """Base configuration."""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'hard-to-guess-string-for-dev'
    UPLOAD_FOLDER = os.path.join(os.getcwd(), 'uploads')
    DOWNLOAD_FOLDER = os.path.join(os.getcwd(), 'downloads')
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # Limit upload to 50MB
    ALLOWED_EXTENSIONS = {'pdf'}

    # Logging Configuration
    LOG_FILE_MAX_BYTES = 10 * 1024 * 1024  # 10MB
    LOG_FILE_BACKUP_COUNT = 10
    LOG_LEVEL = 'INFO'

class DevelopmentConfig(Config):
    DEBUG = True

class TestingConfig(Config):
    TESTING = True
    WTF_CSRF_ENABLED = False
    UPLOAD_FOLDER = os.path.join(os.getcwd(), 'tests/test_uploads')
    DOWNLOAD_FOLDER = os.path.join(os.getcwd(), 'tests/test_downloads')

class ProductionConfig(Config):
    DEBUG = False

config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
