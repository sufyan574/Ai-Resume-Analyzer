from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()

# ---------------------- USER ---------------------- #
class User(UserMixin, db.Model):
    __tablename__ = 'user'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # "hr" or "candidate"
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    resumes = db.relationship('Resume', backref='candidate', lazy=True)
    job_posts = db.relationship('JobPost', backref='hr', lazy=True)
    job_applications = db.relationship('JobApplication', backref='candidate_user', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# ---------------------- RESUME ---------------------- #
class Resume(db.Model):
    __tablename__ = 'resume'

    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    text = db.Column(db.Text)
    detected_skills = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

# ---------------------- JOB POST ---------------------- #
class JobPost(db.Model):
    __tablename__ = 'job_post'

    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.String(50), unique=True, nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    hr_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    applications = db.relationship('JobApplication', backref='job_post', lazy=True)

# ---------------------- JOB APPLICATION ---------------------- #
class JobApplication(db.Model):
    __tablename__ = 'job_application'

    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.Integer, db.ForeignKey('job_post.id'), nullable=True)
    candidate_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    resume_text = db.Column(db.Text)
    detected_skills = db.Column(db.Text)
    score = db.Column(db.Integer, default=0)
    shortlisted = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
