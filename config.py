import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    # Flask security keys
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'myflasksecretkey2024'
    SECURITY_PASSWORD_SALT = os.environ.get('SECURITY_PASSWORD_SALT') or 'email-confirm-salt'

    # Database configuration
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(BASE_DIR, 'instance', 'resumes.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # File upload settings
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
    ALLOWED_EXTENSIONS = {'pdf', 'docx'}

    # ✅ Flask-Mail Configuration (for Gmail)
    MAIL_SERVER = 'smtp.gmail.com'
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USE_SSL = False
    MAIL_USERNAME = 'roshaanparvaizawan@gmail.com'
    MAIL_PASSWORD = 'aojyoyqomfmzucoz'  # your 16-char app password (no spaces)
    MAIL_DEFAULT_SENDER = ('AI Resume Analyzer', 'roshaanparvaizawan@gmail.com')
