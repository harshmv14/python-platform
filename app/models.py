from app import db
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timezone
from flask_login import UserMixin
class User(UserMixin,db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True, nullable=False)
    password_hash = db.Column(db.String(256))
    role = db.Column(db.String(10), default='student', nullable=False) # 'student' or 'admin'
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'

class Section(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    is_unlocked = db.Column(db.Boolean, default=True)
    questions = db.relationship(
        'Question', 
        backref='section', 
        lazy='dynamic', 
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f'<Section {self.title}>'

class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    section_id = db.Column(db.Integer, db.ForeignKey('section.id'), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    starter_code = db.Column(db.Text)
    hints = db.Column(db.Text)
    difficulty = db.Column(db.Integer, default=1) # e.g., 1-5 scale

    def __repr__(self):
        return f'<Question {self.title}>'

class Submission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    q_id = db.Column(db.Integer, db.ForeignKey('question.id'), nullable=False)
    code = db.Column(db.Text, nullable=False)
    output = db.Column(db.Text)
    status = db.Column(db.String(10)) # e.g., 'solved', 'failed'
    time_taken = db.Column(db.Float) # in seconds
    submitted_at = db.Column(db.DateTime, index=True, default=lambda: datetime.now(timezone.utc))

    user = db.relationship('User', backref='submissions')
    question = db.relationship('Question', backref='submissions')

class Draft(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    q_id = db.Column(db.Integer, db.ForeignKey('question.id'), nullable=False)
    code = db.Column(db.Text)
    last_saved = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    user = db.relationship('User', backref='drafts')
    question = db.relationship('Question', backref='drafts')

class Challenge(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    q_id = db.Column(db.Integer, db.ForeignKey('question.id'), nullable=False)
    start_time = db.Column(db.DateTime)
    end_time = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, default=False)

    question = db.relationship('Question', backref='challenges')


class AppSetting(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(50), unique=True, nullable=False)
    value = db.Column(db.String(100), nullable=False)
