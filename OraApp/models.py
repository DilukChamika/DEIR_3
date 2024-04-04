
from flask import current_app
from datetime import datetime
from OraApp import db, login_manager
from flask_login import UserMixin
from itsdangerous import URLSafeTimedSerializer
from sqlalchemy.orm import relationship

@login_manager.user_loader
def load_user(id):
    return User.query.get(int(id))
# # InterviewQuestion database model class for interview_questions table
# class InterviewQuestion(db.Model):
#     __tablename__ = 'interview_questions'
#     id = db.Column(db.Integer, primary_key=True)
#     question1 = db.Column(db.Text, nullable=False)
#     question2 = db.Column(db.Text, nullable=False)
#     answer1 = db.Column(db.Text,nullable=False)
#     answer2 = db.Column(db.Text,nullable=False)
#     job_id = db.Column(db.Integer, nullable=False)
#     applicant_id = db.Column(db.Integer, nullable=False)
    
#     date_submitted = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

 
#UPDATED  - the table in phpmyadmin is also changed to JSON format
class InterviewQuestion(db.Model):
    __tablename__ = 'interview_questions'
    id = db.Column(db.Integer, primary_key=True)
    questions = db.Column(db.JSON, nullable=False)  # Store questions as JSON
    job_id = db.Column(db.Integer, nullable=False)
    date_submitted = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


#UPDATED --table added in backend
class PersonInt(db.Model):
    __tablename__ = 'person_int'
    id = db.Column(db.Integer, primary_key=True)
    questions = db.Column(db.JSON, nullable=False)  # Store questions as JSON
    answers = db.Column(db.JSON, nullable=False)  # Store answers as JSON
    job_id = db.Column(db.Integer, nullable=False)
    applicant_id = db.Column(db.Integer, nullable=False)
   

class ScoreApplicant(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    employer_id = db.Column(db.Integer, nullable=False)
    applicant_id = db.Column(db.Integer,  nullable=False)
    score = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    

class JobsInquired(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.Integer, nullable=False)
    company_id = db.Column(db.Integer, nullable=False)
    user_id = db.Column(db.Integer, nullable=False)


#Column for CV data 
class SelectedApplicants(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    education = db.Column(db.String(255))
    courses = db.Column(db.String(255))
    user_id = db.Column(db.Integer)

# users database model class for users table
    
    def __init__(self, education, courses, user_id):
        self.education = education
        self.courses = courses
        self.user_id = user_id
        
class User(db.Model, UserMixin):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    user_role = db.Column(db.String(20), nullable=False)
    password = db.Column(db.String(60),nullable=False)
    applicants = db.relationship('Applicant', backref='user', uselist=False, lazy=True)
    admins = db.relationship('Admin', backref='user', uselist=False, lazy=True)
    employers = db.relationship('Employer', backref='user', uselist=False, lazy=True)

    def get_reset_token(self, expires_sec=1800):
        s = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
        return s.dumps({'user_id': self.id})

    @staticmethod
    def verify_reset_token(token):
        s = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])

        try:
            user_id = s.loads(token)['user_id']
        except:
            return None
        return User.query.get(user_id)
# Association Table for connecting applicants to jobs table using a many-to-many relationship
jobs_applied = db.Table(
    'jobs_applied',
    db.Column('job_id',db.Integer, db.ForeignKey('jobs.id'), nullable=False),
    db.Column('applicant_id',db.Integer, db.ForeignKey('applicants.id'), nullable=False),
    db.Column('date_applied', db.DateTime(timezone=True), nullable=False, default=datetime.utcnow),
    db.Column('shortlisted', db.Boolean, nullable=False, server_default='0'),
    db.PrimaryKeyConstraint('job_id', 'applicant_id')
)

# applicants database model class for applicants table-----UPDATED
class Applicant(db.Model):
    __tablename__ = 'applicants'
    id = db.Column(db.Integer, primary_key=True)
    f_name = db.Column(db.String(20), nullable=False)
    l_name = db.Column(db.String(20), nullable=False)
    gender = db.Column(db.String(10), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    resume = db.Column(db.String(25), nullable=False)
    image = db.Column(db.String(25),  nullable=False, server_default='anony.png')
    applied_jobs = db.relationship('Job', secondary=jobs_applied, backref='applicants', lazy=True)
    date_joined = db.Column(db.DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True, nullable=False)
    job_categories = db.Column(db.String(100))  # New column for job categories

# Add this new model to your models.py file
class SubEmployers(db.Model):
    __tablename__ = 'sub_employers'
    id = db.Column(db.Integer, primary_key=True)
    employer_id = db.Column(db.Integer, db.ForeignKey('employers.id'), nullable=False)
    applicant_id =db.Column(db.Integer, db.ForeignKey('applicants.id'),nullable=False)
    sub_employee_id = db.Column(db.Integer, db.ForeignKey('employers.id'), nullable=False)
    date_invited = db.Column(db.DateTime, default=datetime.utcnow)

# employers database model class for employers table
class Employer(db.Model):
    __tablename__ = 'employers'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(60), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    location = db.Column(db.String(20), nullable=False)
    tagline = db.Column(db.String(60), nullable=False)
    description = db.Column(db.Text, nullable=False)
    website = db.Column(db.String(60))
    logo = db.Column(db.String(25),  nullable=False, server_default='company.png')
    date_joined = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    jobs = db.relationship('Job', backref='company', lazy=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True, nullable=False)
    
# admin database model class for admins table
class Admin(db.Model):
    __tablename__ = 'admins'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(20), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    image = db.Column(db.String(20),  nullable=False, server_default='anony.png')
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True, nullable=False)

# Job database model class for jobs table
class Job(db.Model):
    __tablename__ = 'jobs'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(20), nullable=False)
    category = db.Column(db.String(60), nullable=False)
    salary = db.Column(db.Float(20), nullable=False, server_default='0')
    type = db.Column(db.String(20), nullable=False)
    description = db.Column(db.Text, nullable=False)
    date_posted = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    company_id = db.Column(db.Integer, db.ForeignKey('employers.id'), nullable=False)

    


# Alerts database model class for notifications table
class Notification(db.Model):
    __tablename__ = 'notifications'
    id = db.Column(db.Integer, primary_key=True)
    recipient = db.Column(db.String(100), nullable=False)
    subject = db.Column(db.String(255), nullable=False)
    body = db.Column(db.Text, nullable=False)
    meeting_time = db.Column(db.DateTime, nullable=False)
    meeting_topic = db.Column(db.String(100), nullable=False)
    meeting_duration = db.Column(db.Integer, nullable=False)
    meeting_url = db.Column(db.String(255))
    date_sent = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

# # Company database model class for companies table
# class Company(db.Model):
#     __tablename__ = 'companies'
#     id = db.Column(db.Integer, primary_key=True)
#     name = db.Column(db.String(255), nullable=False)
#     description = db.Column(db.Text, nullable=True)
#     website = db.Column(db.String(255), nullable=True)
#     email = db.Column(db.String(255), nullable=False)
#     logo = db.Column(db.String(25),  nullable=False, server_default='company.png')
#     date_created = db.Column(db.DateTime, nullable=False)
    
# Transcript database model class for transcript table
class Transcript(db.Model):
    __tablename__ = 'transcript'
    id = db.Column(db.Integer, primary_key=True)
    transcript = db.Column(db.Text, nullable=False)
    date_created = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

class Alert(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(255), nullable=False)
    applicant_id = db.Column(db.Integer, nullable=False)
