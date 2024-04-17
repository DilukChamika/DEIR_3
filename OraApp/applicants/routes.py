
from flask import render_template, Blueprint, url_for,jsonify, flash, redirect, request, abort
from OraApp import db, bcrypt
from OraApp.forms import Applicant_User_Update, User_Login, Applicant_Signup, Forgot_Password, Reset_Password, Change_Password
from OraApp.models import User, Applicant, Job, jobs_applied as applied,InterviewQuestion,SelectedApplicants,PersonInt,Notification, ScoreApplicant, JobsInquired, SubEmployers, Alert
from OraApp.utils import save_file, remove_file, user_role_required, send_pwd_reset_email
from flask_login import login_user, current_user, logout_user
from flask import Flask
from werkzeug.utils import secure_filename
import nltk
nltk.download('vader_lexicon')

from flask_mail import Mail
app = Flask(__name__)

# Configure Flask-Mail
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587  # Change to your mail server's port
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False
app.config['MAIL_USERNAME'] = 'navaratneudani@gmail.com'
app.config['MAIL_PASSWORD'] = 'jmss gfnq ojju vhgx'
app.config['MAIL_DEFAULT_SENDER'] = 'navaratneudani@gmail.com'

# Create the Mail instance
mail = Mail(app)

applicant = Blueprint('applicant', __name__)

def get_user():
    user = None
    if current_user.is_authenticated:
        if current_user.employers:
            user = current_user.employers
        elif current_user.applicants:
            user = current_user.applicants
    return user

# Applicant Dashboard
@applicant.route("/applicant/account")
@user_role_required('applicant')
def applicant_account():
    user = current_user.applicants
    jobs = user.applied_jobs
    query = db.session.query(applied).join(Applicant).filter(Applicant.id==user.id).all() 
    shortlists = [ i for i in query if i.shortlisted]
    notifications = Alert.query.filter_by(applicant_id=user.id).all()

    return render_template("applicants/account.html", title="DEIR: Diversity, Equity, Inclusion, Retention", user=user, jobs=jobs, shortlists=shortlists, notifications=notifications)

# Applicant Account Settings
@applicant.route("/applicant/settings", methods=['GET','POST'])
@user_role_required('applicant')
def settings():
    user = current_user.applicants
    form = Applicant_User_Update()

    applicant = Applicant.query.filter(Applicant.id == user.id).first()
    applicant_id = db.session.query(Applicant.user_id).filter(Applicant.id == user.id).scalar()
    user_details = User.query.filter(User.id == applicant_id).first()


    if form.validate_on_submit():
        applicant.f_name = form.f_name.data
        applicant.l_name = form.l_name.data
        user_details.email = form.email.data.lower()
        applicant.phone = form.phone.data 

        if form.image.data:
            new_file = save_file('applicant/image/', form.image.data)
            if new_file:
                if user.image != 'anony.png':
                    old_file = f'applicant/image/{str(user.image)}'
                    remove_file(old_file)
                user.image = new_file

        db.session.commit()
        flash(f'Account Updated Successfully.', 'success')
        return redirect(url_for('.settings'))

    form.f_name.data = applicant.f_name 
    form.l_name.data = applicant.l_name
    form.email.data = user_details.email
    form.phone.data = applicant.phone

    return render_template("applicants/settings.html", title="DEIR: Diversity, Equity, Inclusion, Retention", form=form, user = user)

#-----UPDATED
@applicant.route('/candidate_profile/<int:applicant_id>/<int:applicant_user_id>')
def userprofile(applicant_id,applicant_user_id):
    user = get_user()
    applicant = Applicant.query.get_or_404(applicant_id)
    about = SelectedApplicants.query.filter_by(user_id=applicant_user_id).first()
    censored_infor =  remove_sensitive_info(about.education)
    print(censored_infor)
    return render_template('applicants/candidate_profile.html',user=user, applicant=applicant, applicant_about=about, censored_info=censored_infor)


# Removing University and country information------UPDATED
# Load the English language model (you may need to install it first)
import spacy
nlp = spacy.load("en_core_web_sm")

def remove_sensitive_info(text):
    doc = nlp(text)
    redacted_text = []
    for token in doc:
        if token.ent_type_ in ['GPE', 'ORG']:
            redacted_text.append('XXXXX')  # Replace with redaction symbol
        else:
            redacted_text.append(token.text)
    return ' '.join(redacted_text)

@applicant.route("/applicant/application/<int:job_id>")
@user_role_required('applicant')
def apply_for_job(job_id):
    user = current_user.applicants
    job = Job.query.get_or_404(job_id)
    
    user.applied_jobs.append(job)
    db.session.commit()

    flash(f'Application sent Successfully!', 'success')
    return redirect(url_for('.jobs_applied'))

@applicant.route("/applicant/jobs-applied")
@user_role_required('applicant')
def jobs_applied():
    user = current_user.applicants
    page = request.args.get('page', 1, type=int)
    jobs = db.session.query(Job, applied.c.date_applied, applied.c.shortlisted).select_from(Job).join(applied).join(Applicant).filter(Applicant.id==user.id).order_by(applied.c.date_applied.desc()).paginate(page=page, per_page=15)

    return render_template("applicants/jobs.html", title="DEIR: Diversity, Equity, Inclusion, Retention", jobs=jobs, user=user)

@applicant.route("/applicant/shortlisted-jobs")
@user_role_required('applicant')
def shortlisted_jobs():
    user = current_user.applicants
    jobs = db.session.query(Job).join(applied).join(Applicant).filter((Applicant.id==user.id) & (applied.c.shortlisted)).all() 

    return render_template("applicants/shortlists.html", title="DEIR: Diversity, Equity, Inclusion, Retention", jobs=jobs, user=user)

@applicant.route("/applicant/<int:job_id>/remove-job/", methods=['POST'])
@user_role_required('applicant')
def remove_job(job_id):
    user = current_user.applicants
    job = Job.query.get_or_404(job_id)
    user.applied_jobs.remove(job)

    db.session.commit()
            
    flash(f'Job removed from the list successfully', 'success')
    return redirect(url_for('.jobs_applied'))

@applicant.route("/applicant/<int:applicant_id>/delete-image", methods=['POST'])
@user_role_required('applicant')
def delete_image(applicant_id):
    user = Applicant.query.get_or_404(applicant_id)
    if not user.user == current_user:
        abort(403)

    if user.image and user.image != "anony.png":
        file = f'applicant/image/{str(user.image)}'
        try:
            remove_file(file)
            user.image = 'anony.png'
            db.session.commit()
            flash(f'Image Removed Successfully!', category='success')
        except FileNotFoundError:
            user.image = 'anony.png'
            db.session.commit()
            flash(f'File not Found!', category='danger')
    
    return redirect(url_for('.settings'))

@applicant.route("/applicant/notifications")
@user_role_required('applicant')
def notifications():
    return redirect(url_for('.settings'))


#UPDATED
@applicant.route("/applicant/check_status/<int:job_id>")
@user_role_required('applicant')
def check_status(job_id):
    user = current_user.applicants
    user_id = current_user.id  # Get the user ID of the current logged-in user
    print("Applicant ID",user_id)
    applicant = Applicant.query.filter(Applicant.id == user.id).first()
    print("Applicant User ID",applicant.id)
     # Fetch questions associated with the user_id from PersonInt table
    questions_data_person_int = PersonInt.query.filter_by(applicant_id=user_id).first()
    
    # Initialize an empty list to hold questions
    question_list = []

    if questions_data_person_int:
        question_list.extend(questions_data_person_int.questions)

   
    if question_list:
        question_list_with_index = list(enumerate(question_list))
        return render_template('applicants/interview_questions_input.html', title="DEIR: Diversity, Equity, Inclusion, Retention", user=user, question_list_with_index=question_list_with_index)
    else:
        # Handle case when no questions are found
        return render_template('applicants/interview_questions_input.html', title="DEIR: Diversity, Equity, Inclusion, Retention", user=user, question_list=[])
    
#Question Answering Form ------UPDATED
import base64
@applicant.route("/applicant/submit_interview", methods=['POST'])
@user_role_required('applicant')
def submit_interview():
    user_id = current_user.id
    if request.method == 'POST':
        
        # Get data from the form
        answers = []
        for key, value in request.form.items():
            if key.startswith('answer'):
                print(value)
                answers.append(value)
            
        # Create a new InterviewQuestion instance or fetch the existing one based on your logic
        personal_questions = PersonInt.query.filter_by(applicant_id=user_id).first()

        # Update the answers in the database
        if personal_questions:
            personal_questions.answers = answers
            db.session.commit()

            # Flash success message
            flash('Answers submitted successfully!', 'success')
            return redirect(request.referrer)

        

    # If the form was not submitted or there was an issue, flash an error message
    flash('Failed to submit answers. Please try again.', 'error')
    return redirect(request.referrer)

import os
import matplotlib.pyplot as plt
from io import BytesIO

#Creating the pie chart------------
def create_pie_chart(percentage_scores, user_id, save_path=None):
    # Set the Matplotlib backend to 'Agg'
    plt.switch_backend('Agg')
    labels = percentage_scores.keys()
    sizes = list(percentage_scores.values())
    colors = ['lightcoral', 'lightskyblue', 'lightgreen']
    explode = (0.1, 0, 0)

    plt.pie(sizes, explode=explode, labels=labels, colors=colors, autopct='%1.1f%%', startangle=140)
    plt.axis('equal')

    # Include user ID in the title
    plt.title(f'Personality Traits - User ID: {user_id}')

    if save_path:
        directory = os.path.dirname(save_path)
        if not os.path.exists(directory):
            os.makedirs(directory)
        plt.savefig(save_path)
        return save_path
    else:
        # If no save_path is provided, save the image to a BytesIO buffer
        img_buffer = BytesIO()
        plt.savefig(img_buffer, format='png')
        img_buffer.seek(0)
        return img_buffer


from nltk.sentiment import SentimentIntensityAnalyzer
from nltk.tokenize import word_tokenize
from nltk.stem import PorterStemmer
import matplotlib.pyplot as plt

@applicant.route("/applicant/person-score-chart/")
@user_role_required('applicant')
def infer_personality_scores():
    stemmer = PorterStemmer()

    user_id = current_user.id
   
    # Assuming the InterviewQuestion model has columns answer1 and answer2
    interview_question = PersonInt.query.filter_by(applicant_id=user_id).first()
    answer1 = ""
    answer2 = ""
    if interview_question:
        answer1 = interview_question.answer1
        answer2 = interview_question.answer2

    personality_keywords = {
        'confidence': {'keywords': ['I will', 'I would', 'positive', 'Curious', 'adventurous'], 'weight': 1},
        'ethical': {'keywords': ['respect', 'positive', 'happy', 'empathetic'], 'weight': 1},
        'leadership': {'keywords': ['offer', 'ensure', 'would', 'control'], 'weight': 1}
    }

    def stem_and_tokenize(text):
        return [stemmer.stem(word) for word in word_tokenize(text.lower())]

    scores = {trait: 0 for trait in personality_keywords}

    for trait, details in personality_keywords.items():
        for keyword in details['keywords']:
            stemmed_keyword = stemmer.stem(keyword)
            scores[trait] += stem_and_tokenize(answer1).count(stemmed_keyword) + stem_and_tokenize(answer2).count(stemmed_keyword)

    total_words = len(word_tokenize(answer1)) + len(word_tokenize(answer2))
    # Check if total_words is zero to avoid ZeroDivisionError
    if total_words == 0:
        percentage_scores = {trait: 0 for trait in personality_keywords}
    else:
        percentage_scores = {trait: (score / total_words) * 100 for trait, score in scores.items()}
    
    response = {"person_score": percentage_scores}
    return jsonify(response)

from flask_mail import Message

# def send_email_with_attachment(file_path):
    

#     msg = Message('Interview PDF Submission', sender=('Udani',"navaratneudani@gmail.com"), recipients=['udn992110@gmail.com'])
#     msg.body = 'The applicant has submitted their interview PDF.'
    
#     with open(file_path, 'rb') as pdf_file:
#         print(file_path)
#         msg.attach(filename='interview.pdf', data=pdf_file.read(), content_type='application/pdf')

#     mail.send(msg)

@app.route('/applicant/interview_questions_input')
@user_role_required('applicant')
def interview_questions_input():
    # Add any necessary logic for this route
    return render_template('applicants/interview_questions_input.html',title="DEIR: Diversity, Equity, Inclusion, Retention")


# Signing in Applicant user
@applicant.route("/applicant/login", methods=['GET', 'POST'])
def applicant_login():
    if current_user.is_authenticated and current_user.applicants:
        return redirect(url_for('.applicant_account'))
    form = User_Login()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and user.applicants and bcrypt.check_password_hash(user.password, form.password.data):
            match = Applicant.query.filter_by(user_id=user.id).first()
            login_user(user, remember=form.remember.data)
            flash(f'Logged in as {match.l_name}!', 'success')
            return redirect(request.args.get('next') or url_for('.applicant_account'))
        else:
            flash(f'Invalid Email or Password! Please Try Again.', 'danger')
    return render_template("applicants/login.html", title="DEIR: Diversity, Equity, Inclusion, Retention", form=form)

import os
import re
import PyPDF2
import mysql.connector

#UPDATED
def extract_details_from_pdf(resume_path, user_id):
    # Check if the file exists before opening it
    if not os.path.exists(resume_path):
        raise FileNotFoundError(f"File not found: {resume_path}")
    
    # Read the PDF file and extract text from the first page
    with open(resume_path, 'rb') as pdf_file:
        reader = PyPDF2.PdfReader(pdf_file)
        page = reader.pages[0]
        

        # Extract text from each page
        all_texts = ""
        for sheet in reader.pages:
            all_texts += sheet.extract_text()


        text = page.extract_text()
        
        print("ALL PAGES CONTENT",all_texts)
        print("RESUME INFORMATION BEFORE PRE PROCESSING",text)
        
        # Text Preprocessing
        text = all_texts.replace(":", "")
        text = all_texts.replace("s'", "s")
        text = all_texts.replace("'s", "s")
        text = all_texts.replace("()","")
        text = all_texts.replace("-","")
        text = all_texts.replace("[^\w\s]","")

        print("RESUME INFORMATION",text)
        # Extract relevant details using regular expressions or pattern matching
        education_status_pattern = r"Education([\s\S]*?)Courses"
        certificate_pattern = r"Courses([\s\S]*)$"
        
        education_status_match = re.search(education_status_pattern, text, re.MULTILINE)
        certificate_status_match = re.search(certificate_pattern, text, re.MULTILINE)
        print("EDUCATION STATUS MATCH",education_status_match)
        print("COURSES STATUS MATCHED",certificate_status_match)
        education = "Primary education Completed"
        courses = "No Courses"

        if education_status_match:
            education = education_status_match.group(1)  # Get the part after "Education"
            print("EDUCATION INFORMATION",education)
        if certificate_status_match:
            courses = certificate_status_match.group(1)  # Get the part after "Courses"
            print("COURSES EXTRACTED",courses)
        # Insert 'Education' and 'Courses' values into the database
        #insert_into_mysql(education, courses, user_id)

        selected_applicant = SelectedApplicants(
        education=education,
        courses=courses,
        user_id=user_id
        )
        db.session.add(selected_applicant)
        db.session.commit()

        # # Flash a success message
        flash('Details Submitted Successfully', 'success')

        # Redirect back to the same page
        return redirect(request.referrer)

#Extract Education Details of Applicant ----UPDATED
@applicant.route("/applicant/education_details/", methods=['GET'])
@user_role_required('applicant')
def extract_education():
    print('Accessed /applicant/education_details/')
    user_id = current_user.id
   
    # Assuming the InterviewQuestion model has columns answer1 and answer2
    cv_details = SelectedApplicants.query.filter_by(user_id=user_id).first()
    education = ""
    courses =""

    if cv_details:
        education = cv_details.education
        courses = cv_details.courses

    education_keywords = {
        'primary_education': ['G.C.E', 'Primary School', 'Elementary School','Diploma','Year'],
        'secondary_education': ['Ordinary','Level', 'High School', 'Secondary School','Semester','Year'],
        'higher_education': ['Advanced', 'Level','College', 'University', 'Bachelor', 'Master', 'Ph.D.','SLIIT','GPA'],
        # Add more levels and keywords as needed
    }
   
    
    course_keywords = {
        'Machine Learning': ['Machine Learning', 'ML'],
        'Udemy': ['Udemy'],
        'Great Learning': ['Great Learning'],
        'Introduction': ['Introduction'],
        'Algorithm': ['Algorithm']
    }

    primary_count = count_keywords(education, education_keywords['primary_education'])
    secondary_count = count_keywords(education, education_keywords['secondary_education'])
    higher_count = count_keywords(education, education_keywords['higher_education'])
    course_count = {}

    for keyword, synonyms in course_keywords.items():
        count = count_keywords(courses, synonyms)
        course_count[keyword] = count

    # Construct the response
    responses = {
        "primary_count": primary_count,
        "secondary_count": secondary_count,
        "higher_count": higher_count,
        "course_count": course_count
    }

    # Print scores to the console
    print("Primary Count:", primary_count)
    print("Secondary Count:", secondary_count)
    print("Higher Count:", higher_count)
     # Print scores to the console
    for keyword, count in course_count.items():
        print(f"{keyword} Count: {count}")
    return jsonify(responses)

# Add a function to count keywords ----UPDATED
def count_keywords(text, keywords):
    count = 0
    for keyword in keywords:
        if keyword.lower() in text.lower():
            count += 1
    return count








# Add a function to count keywords
def count_keywords(text, keywords):
    return sum(text.lower().count(keyword.lower()) for keyword in keywords)

# def create_and_save_separate_charts(primary_count, secondary_count, higher_count, courses_count, user_id):
#     # Create and save the bar chart
#     create_bar_chart_and_save(primary_count, secondary_count, higher_count, user_id, save_path=f"D:\\Y3S2\\RevisionY3S2\\IP\\DailyDiaries\\to_send\\Week13\\flask-oracom-main\\flask-oracom-main\\OraApp\\static\\applicant\\uploaded\\bar_chart_{user_id}.png")

#     # Create and save the pie chart
#     create_pie_chart_and_save(courses_count, user_id, save_path=f"D:\\Y3S2\\RevisionY3S2\\IP\\DailyDiaries\\to_send\\Week13\\flask-oracom-main\\flask-oracom-main\\OraApp\\static\\applicant\\uploaded\\pie_chart_{user_id}.png")

    

def create_bar_chart_and_save(primary_count, secondary_count, higher_count, user_id, save_path):
    # Create a figure for the bar chart
    fig, ax = plt.subplots(figsize=(8, 6))

    # Create and display the bar chart
    categories = ['Primary Education', 'Secondary Education', 'Higher Education']
    counts = [primary_count, secondary_count, higher_count]
    plt.bar(categories, counts, color='lightblue')
    plt.xlabel('Education Levels')
    plt.ylabel('Level')
    plt.title(f'Education Level of - User ID: {user_id}')

    # Save the bar chart to the specified path
    plt.savefig(save_path)
    plt.close()

# Add a new function to create and save the pie chart
def create_pie_chart_and_save(counts, user_id, save_path):
    labels = counts.keys()
    sizes = counts.values()

    plt.figure(figsize=(8, 8))
    plt.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=140)
    plt.title(f'Self Learned Skills of -User ID: {user_id}')
    plt.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle.
    plt.savefig(save_path)
    plt.close()
    


#Inserting into Database
def insert_into_mysql(education, courses,user_id):
    # Configure your MySQL connection parameters
    mysql_config = {
        'user': 'root',
        'db': 'deir_1',
        'host': 'localhost',
        'port': 3306,  # Adjust the port as needed
    }

    # Connect to the MySQL server
    conn = mysql.connector.connect(**mysql_config)

    # Create a cursor object to execute SQL queries
    cursor = conn.cursor()

     # Define the SQL query to insert 'Education' and 'Courses' values with the user_id
    insert_query = "INSERT INTO select_applicants (Education, Courses, user_id) VALUES (%s, %s, %s)"

    # Execute the INSERT query with the extracted values
    values = (education, courses, user_id)

    # Execute the INSERT query
    cursor.execute(insert_query, values)

    # Commit the changes to the database
    conn.commit()

    # Close the cursor and the connection
    cursor.close()
    conn.close()


# Applicant user registration
@applicant.route("/applicant/signup", methods=['POST', 'GET'])
def applicant_signup():
    if current_user.is_authenticated and current_user.applicants:
        return redirect(url_for('.applicant_account'))
    form = Applicant_Signup()
    

    if form.validate_on_submit():
        resume = save_file('applicant/resume/', form.resume.data)
        
        # Get the chosen job categories as a list
        selected_job_categories = form.job_categories.data
        print(selected_job_categories)
        
         # Convert the list of selected categories into a string
        job_categories_str = ', '.join(selected_job_categories)
        print("Selected Job Categories:", job_categories_str)

        
        pw_hash = bcrypt.generate_password_hash(form.password.data).decode('utf-8')

        user = User(email=form.email.data.lower(), user_role='applicant', password=pw_hash)
        db.session.add(user)
        db.session.commit()
        # # # Extract details from the uploaded resume using a PDF parsing library
        extract_details_from_pdf(os.getcwd()+'/OraApp/static/applicant/resume/'+resume, user.id)
        
        if form.image.data:
            image = save_file('applicant/image/', form.image.data) 
            applicant = Applicant(f_name=form.f_name.data.strip().capitalize(), l_name=form.l_name.data.strip().capitalize(),gender=form.gender.data, phone=form.phone.data, resume=resume, job_categories=job_categories_str,image=image, user=user)
            db.session.add(applicant)
            db.session.commit()
        else:
            image = 'anony.png'
            applicant = Applicant(f_name=form.f_name.data.strip().capitalize(), l_name=form.l_name.data.strip().capitalize(), gender=form.gender.data, phone=form.phone.data,job_categories=job_categories_str,resume=resume,image=image, user=user)
            db.session.add(applicant)
            db.session.commit()

        flash(f'Account Successfully created for {form.email.data}!', 'success')
        login_user(user, remember=True)
        return redirect(url_for('.settings'))
    return render_template("applicants/signup.html", title="DEIR: Diversity, Equity, Inclusion, Retention", form=form)

# Applicant User password reset request
@applicant.route("/applicant/password-reset", methods=['GET', 'POST'])
@user_role_required('applicant')
def password_reset_request():
    if current_user.is_authenticated and current_user.applicants:
        return redirect(url_for('.applicant_account'))
    form = Forgot_Password()

    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            try:
                token = user.get_reset_token()
                reset_url = url_for('.password_reset_link', token=token, _external=True)
                send_pwd_reset_email(user.email, reset_url,'applicant', user.applicants.f_name)
                flash('A password reset link has been sent to your email', 'info')
                return redirect(url_for('.applicant_login'))
            except Exception as e:
                print(f"Error sending password reset email: {e}")
                flash('Something went wrong! Please Try Again.', 'warning')
                return redirect(url_for('.password_reset_request'))
        else:
            flash('Email not registered. Send the email you registered your account with.', 'warning')
            return redirect(url_for('.password_reset_request'))
    return render_template("forgot_password.html", title="DEIR: Diversity, Equity, Inclusion, Retention", form=form)

# # Applicant user password reset token
# @applicant.route("/applicant/password-reset/<string:token>", methods=['GET', 'POST'])
# def password_reset_link(token):
#     if current_user.is_authenticated and current_user.applicants:
#         return redirect(url_for('.applicant_account'))
#     user = User.verify_reset_token(token)
#     if not user or not user.applicant:
#         flash('The link is either invalid or has expired!', 'warning')
#         return redirect(url_for('.password_reset_request'))
          
#     form = Reset_Password()
#     if form.validate_on_submit():
#         pw_hash = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
#         user.password = pw_hash
#         db.session.commit()

#         flash('Your Password has been updated', 'success')
#         return redirect(url_for('.applicant_login'))
    
#     return render_template("reset_password.html", title="Applicant | Reset Password", form=form)
from flask_mail import Message
from flask import current_app

# Helper function to send password reset email
def send_pwd_reset_email(email, reset_url, user_role, name):
    msg = Message('Password Reset Request', sender=('Udani', 'udn992110@gmail.com'), recipients=[email])
    msg.body = f'''
    To reset your password, visit the following link:
    {reset_url}
    
    If you did not make this request, simply ignore this email.
    '''
    # Add HTML version of the email if needed

    # Send the email
    mail.send(msg)



# Applicant Alterts
@applicant.route("/applicant/alert_applicant", methods=['GET', 'POST'])
@user_role_required('applicant')
def alert_applicant():
    user = current_user.applicants
    notifications = Alert.query.filter_by(applicant_id=user.id).all()
   
    
    return render_template('applicants/notifications.html', title="DEIR: Diversity, Equity, Inclusion, Retention" , user=user, notifications=notifications)

    
@applicant.route('/applicant/following-employers')
@user_role_required('applicant')
def following_emp():
    user = current_user.applicants
    # Add any necessary logic for this route
    return render_template('applicants/following-emp.html',title="DEIR: Diversity, Equity, Inclusion, Retention", user=user)

  



@applicant.route("/applicant/delete-profile", methods=['GET', 'POST'])
@user_role_required('applicant')
def delete_profile():
    user = current_user
    userd = current_user.applicants

    applicant_id = Applicant.query.filter_by(user_id=user.id).first().id
    
    if request.method == 'POST':
        password = request.form.get('password')
        print("password = ", password)
       

        if user and bcrypt.check_password_hash(user.password, password):
            try:
                # Assuming you have proper relationships set up---NOT DELETED
                for application in Applicant.query.filter_by(user_id=user.id).all():
                    db.session.delete(application)

                
                for score in ScoreApplicant.query.filter_by(applicant_id=applicant_id).all():
                    db.session.delete(score)
                #JOBS INQUIRE NOT DELETED
                # If you have an InterviewQuestion table, delete related questions----SUCCEDDFULLY DELETED
                for question in InterviewQuestion.query.filter_by(applicant_id=user.id).all():
                    db.session.delete(question)

                for applied_job in JobsInquired.query.filter_by(user_id=user.id).all():
                    db.session.delete(applied_job)

                for selected_applicant in SelectedApplicants.query.filter_by(user_id=user.id).all():
                    db.session.delete(selected_applicant)

                for assigned_subemp in SubEmployers.query.filter_by(applicant_id=applicant_id).all():
                    db.session.delete(assigned_subemp)

                for alerts in Alert.query.filter_by(applicant_id=applicant_id).all():
                    db.session.delete(alerts)

                # Delete the user (assuming you have cascade set up in the User model)---DELETED
                db.session.delete(user)

                db.session.commit()
                logout_user()
                flash('Your profile has been successfully deleted.', 'success')
                return redirect(url_for('.applicant_login'))
            except Exception as e:
                print(f"Error deleting profile: {str(e)}")
                flash('An error occurred while deleting your profile. Please try again later.', 'danger')
        else:
            print("User or password is None")
            
            flash('Invalid Password! Please Try Again.', 'danger')
        
    return render_template("applicants/delete-profile.html", title="DEIR: Diversity, Equity, Inclusion, Retention", user=userd)




@applicant.route('/applicant/my-resume/', methods=['GET','POST'])
@user_role_required('applicant')
def my_resume():
    user = current_user.applicants
    form = Applicant_User_Update()
    if form.validate_on_submit():
        if form.resume.data:
            new_file = save_file('applicant/resume/', form.resume.data)
            if new_file:
                old_file = f'applicant/resume/{str(user.resume)}'
                try:
                    remove_file(old_file)
                except FileNotFoundError:
                    flash(f'File or Directory not found!', 'danger')
                user.resume = new_file
        db.session.commit()
        flash(f'Resume Updated Successfully.', 'success')
        return redirect(url_for('.my_resume'))

    return render_template("applicants/myresume.html",title="DEIR: Diversity, Equity, Inclusion, Retention", user=user, form=form)

@applicant.route('/applicant/messages')
@user_role_required('applicant')
def messages():
    user = current_user.applicants
    if request.method == 'GET':
        user_id = current_user.applicants.user_id  # Assuming there is a user_id attribute in the Applicant model
        applicant_user = User.query.filter_by(id=user_id).first()

        if applicant_user:
            email = applicant_user.email
            notifications = Notification.query.filter_by(recipient=email).all()
            print(notifications)    
        
        return render_template('applicants/messages.html',title="DEIR: Diversity, Equity, Inclusion, Retention", user=user, notifications=notifications)


@applicant.route('/applicant/meetings')
@user_role_required('applicant')
def meetings():
    user = current_user.applicants
    if request.method == 'GET':
        user_id = current_user.applicants.user_id  # Assuming there is a user_id attribute in the Applicant model
        applicant_user = User.query.filter_by(id=user_id).first()

        if applicant_user:
            email = applicant_user.email
            meetings = Notification.query.filter_by(recipient=email).all()
            #print(notifications)    

        return render_template('applicants/meetings.html',title="DEIR: Diversity, Equity, Inclusion, Retention", user=user , meetings=meetings)


@applicant.route('/applicant/change-password/', methods=['GET','POST'])
@user_role_required('applicant')
def change_password():
    userd = current_user.applicants
    user = current_user
    form = Change_Password()
    if form.validate_on_submit():
        
        if user and user.applicants and bcrypt.check_password_hash(user.password, form.old_password.data):
            pw_hash = bcrypt.generate_password_hash(form.new_password.data).decode('utf-8')

            user.password = pw_hash
            db.session.commit()
            flash(f'Password Updated Successfully.', 'success')
            return redirect(url_for('.applicant_account'))
            
        else:
            flash(f'Current Password is Wrong! Please Try Again.', 'danger')

    return render_template("applicants/change_password.html",title="DEIR: Diversity, Equity, Inclusion, Retention", user=userd, form=form)



# Skill Percentage for the side menu -------------UPDATED
@applicant.route("/applicant/skill_percentages", methods=['GET'])
@user_role_required('applicant')
def calculate_skill_percentages():
    print('Accessed /applicant/skill_percentages/')
    user_id = current_user.id

    # Assuming the InterviewQuestion model has columns answer1 and answer2
    cv_details = SelectedApplicants.query.filter_by(user_id=user_id).first()
    courses = ""

    if cv_details:
        courses = cv_details.courses

    course_keywords = {
        'Machine Learning': ['Machine Learning', 'ML'],
        'Udemy': ['Udemy'],
        'Great Learning': ['Great Learning'],
        'Introduction': ['Introduction'],
        'Algorithm': ['Algorithm']
    }

    total_skill_count = 0
    total_courses = 0

    for skill, synonyms in course_keywords.items():
        skill_count = count_keywords(courses, synonyms)
        total_skill_count += skill_count
        total_courses += len(synonyms)

    # Calculate the overall skill percentage
    if total_courses > 0:
        print("Total Skill Count", total_skill_count)
        print("Total Courses", total_courses)
        overall_skill_percentage = min((total_skill_count / total_courses) * 100 , 100)
        improvement_potential = max(100 - overall_skill_percentage, 0)

    else:
        overall_skill_percentage = 0
        improvement_potential = 0

    # Print overall skill percentage to the console
    response = {"Overall Skill Percentage:": overall_skill_percentage, "Improve Your Score Up To": improvement_potential}
    return jsonify(response)
    