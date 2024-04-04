
from flask import render_template, Blueprint, url_for, flash, redirect,jsonify, request, abort
from OraApp import db, bcrypt
from datetime import datetime
from sqlalchemy import text


from OraApp.forms import User_Login, Employer_Signup,Employer_User_Update, Job_Add, Job_Update, Forgot_Password, Reset_Password, Company_Search,JobDesc_Add,Change_Password
from OraApp.models import User, Employer,SubEmployers, PersonInt,ScoreApplicant,Job,JobsInquired, jobs_applied,Notification, Applicant,InterviewQuestion,Transcript,SelectedApplicants
from OraApp.utils import save_file, user_role_required, remove_file, send_pwd_reset_email, send_shortlist_email
from flask_login import login_user, current_user, logout_user
from flask import Flask
from flask_mail import Mail
import assemblyai as aai
app = Flask(__name__)

#Text Cortex API feature
from flask import request, jsonify
from textcortex import TextCortex

# Create the hemingwai object and enter your API Key
hemingwai = TextCortex(api_key='gAAAAABlrLsW6byDXazQbCre1EiKTnIO2mk94XMKWM1_HLcSmAB7wWeI8-2jviT03HBMFTwkWh-lkPV_uJ39bYmI7rgWR_6LWqXVAAzmHIxZRiR-XMGV_XHa7-CiXX3LYy1E3RtpbCtf')


#Zoom meeting Feature 
from OraApp.transcript.zoom import ZoomClient
from datetime import datetime

ZOOM_ACCOUNT_ID = '13Xtl2FwSgWaTMxkoFLXPw'
ZOOM_CLIENT_ID = '4XcypFV7SeCnbsAG9vA8iw'
ZOOM_CLIENT_SECRET = 'ZVm3d9EiITlVBABiZl09wfs8MxzwM6lU'
aai.settings.api_key = 'c5a0c81305fc41c69eac52bc8e5124cc'

transcriber = aai.Transcriber()

client = ZoomClient(account_id=ZOOM_ACCOUNT_ID, client_id=ZOOM_CLIENT_ID, client_secret=ZOOM_CLIENT_SECRET)


import base64
import requests

# Configure Flask-Mail
smtp_server = app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587  # Change to your mail server's port
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False
sender_email = app.config['MAIL_USERNAME'] = 'udn992110@gmail.com'
sender_password = app.config['MAIL_PASSWORD'] = 'trxe edvj nsgv blbl'
sender_def_email =app.config['MAIL_DEFAULT_SENDER'] = 'udn992110@gmail.com'
app.config['MAIL_DEBUG'] = True

# Create the Mail instance
mail = Mail(app)

employer = Blueprint('employer', __name__)
def store_transcript_in_db(transcript_text):
    try:
        new_transcript = Transcript(transcript=transcript_text)
        db.session.add(new_transcript)
        db.session.commit()
        return True
    except Exception as e:
        print(f"Failed to store transcript in the database: {str(e)}")
        return False


def get_user():
    user = None
    if current_user.is_authenticated:
        if current_user.employers:
            user = current_user.employers
        elif current_user.applicants:
            user = current_user.applicants
    return user


@employer.route("/employer/posted-job-count/", methods=['GET'])
@user_role_required('employer')
def get_posted_job_count():
    print('Accessed /employer/posted-job-count/')
    user = current_user.employers
    com_id = user.id

    job_count = Job.query.filter_by(company_id=com_id).count()
    #print("Company ID",job_count)

    # # Get the count of posted jobs
    # job_posts = user.jobs
    # print(job_posts)

    # Get the count of applicants
    applicant_count = 40 #db.session.query(JobsInquired).filter_by(company_id=com_id).count()
    # Get the count of shortlisted applicants
    shortlisted_count = SelectedApplicants.query.count()

    print(shortlisted_count)
    # Convert the Applicant objects to a serializable format (for example, a dictionary)
    #shortlisted_count_serializable = [applicant.to_dict() for applicant in shortlisted_count]

    response = {
        "job_count": job_count,
        "applicant_count": applicant_count,
        "shortlisted_count":shortlisted_count
    }

    return jsonify(response)
@employer.route("/employer/applicant-count/")
@user_role_required('employer')
def get_applicant_count():
    print('Accessed /employer/applicant-count/')
    user = current_user.employers
    applicant_count = db.session.query(Applicant).select_from(Applicant).join(jobs_applied).join(Job).filter_by(company=user).count()
    response = {"applicant_count": applicant_count}
    #print(applicant_count)
    return jsonify(response)

# performance route
@employer.route('/employer/performance')
@user_role_required("employer")
def performance():
    return render_template('/employers/performance.html')

# Employer dashboard ---UPDATED
@employer.route("/employer/account/")
@user_role_required('employer')
def employer_account():
    user = current_user.employers
    print(user)
    job_posts = user.jobs
    applicants = db.session.query(Applicant).select_from(Applicant).join(jobs_applied).join(Job).filter_by(company=user).all()
    listed = db.session.query(Applicant).select_from(Applicant).join(jobs_applied).filter_by(shortlisted=True).join(Job).filter_by(company=user).all() 
    

    #Extracting the user id from the employer table
    user_id = Employer.query.filter_by(id=user.id).first().user_id
     # Check if the user is a subemployer
    sub_employer_details = SubEmployers.query.filter_by(sub_employee_id=user_id).first()
    
    if sub_employer_details:
        user = current_user.employers
        print(user)
        print("I am a sub employer")
        print(sub_employer_details.date_invited)
        
        # Fetch all applicants assigned to the sub-employer
        # Fetch all applicants assigned to the sub-employer, excluding those who are already scored
        assigned_applicants = db.session.query(Applicant).join(SubEmployers).filter(
        SubEmployers.sub_employee_id == user_id,
        ~exists().where(and_(ScoreApplicant.applicant_id == Applicant.id, ScoreApplicant.employer_id == user.id))
        ).all()

        # Fetch scores for each assigned applicant
        applicant_scores = {}
        for applicant in assigned_applicants:
            print("Applicant ID in account.html",applicant.id)
            user_id = Applicant.query.filter_by(id=applicant.id).first().user_id
    
            jobs_inquired_id = JobsInquired.query.filter_by(user_id=user_id).first().job_id
            job_description = Job.query.filter_by(id=jobs_inquired_id).first().description

            similarity_score = compare_job_description(user_id, job_description)
            personality_score = infer_personality_scores(applicant.id)
            education_score = extract_education(user_id)


            # Store scores in the dictionary
            applicant_scores[applicant.id] = {
                'job_description': job_description,
                'similarity_score': similarity_score,
                'personality_score': personality_score,
                'education_score': education_score
            }
        return render_template("employers/account.html", title="DEIR: Diversity, Equity, Inclusion, Retention", user=user, jobs=job_posts, applicants=applicants, listed=listed, assigned_applicants=assigned_applicants, applicant_scores=applicant_scores)

    
    return render_template("employers/account.html", title="DEIR: Diversity, Equity, Inclusion, Retention", jobs=job_posts, applicants=applicants, listed=listed, user=user)

# Employer/company details
@employer.route("/company/<int:company_id>/profile/")
def profile(company_id):
    user = get_user()
    company = Employer.query.get_or_404(company_id)
    return render_template("employers/profile.html", title="DEIR: Diversity, Equity, Inclusion, Retention", user=user, company=company)

@employer.route('/generate_transcript', methods=['POST', 'GET'])
def generate_transcript():
    if request.method == 'POST':
        print("Client print",client)
        recs = client.get_recordings()
        print("Recordings" ,recs)
        if recs.get('meetings'):    
            rec_id = recs['meetings'][0]['id']
            my_url = client.get_download_url(rec_id)
            transcript = transcriber.transcribe(my_url)
            transcript_text = transcript.text
            print("Transcript text",transcript.text)
            # Store the transcript in the database
            success = store_transcript_in_db(transcript_text)

            if success:
                return jsonify({'success': True, 'message': 'Transcript generated and stored successfully.', 'transcript': transcript_text}), 200
            else:
                return jsonify({'success': False, 'message': 'Failed to store transcript.'}), 500
        else:
            print('No meetings to transcribe.')
            return jsonify({'success': False, 'message': 'No meetings to transcribe.'}), 404
    else:
        return jsonify({'success': False, 'message': 'Invalid request method.'}), 405

# company list
@employer.route("/companies/")
@employer.route("/company/list/")
def company_list():
    user = get_user()
    form1 = Company_Search()
    page = request.args.get('page', 1, type=int)
    companies = Employer.query.paginate(page=page, per_page=15)
    head = 'List of Companies'
    return render_template("employers/list.html", title="DEIR: Diversity, Equity, Inclusion, Retention",user=user, companies=companies, head=head, form1=form1)

@employer.route("/employer/jobs/<int:job_id>/details/")
@user_role_required('employer')
def job_details(job_id):
    user = get_user()
    job = Job.query.get_or_404(job_id)
    if not job.company == current_user.employers:
        abort(403)
    applicants = db.session.query(jobs_applied.c.job_id).filter_by(job_id=job_id).all()

    return render_template("employers/job-details.html", title="DEIR: Diversity, Equity, Inclusion, Retention",user=user, job=job, applicants=applicants)

@employer.route("/employer/posted-jobs")
@user_role_required('employer')
def posted_jobs():
    user = current_user.employers
    page = request.args.get('page', 1, type=int)
    jobs = Job.query.filter_by(company=user).order_by(Job.date_posted.desc()).paginate(page=page, per_page=15)
    applications_list = db.session.query(jobs_applied.c.job_id, jobs_applied.c.applicant_id, jobs_applied.c.shortlisted)

    return render_template("employers/jobs.html", title="DEIR: Diversity, Equity, Inclusion, Retention", jobs=jobs, applications_list=applications_list, user=user)



# Generate token for zoom meeting
def generate_access_token():
    client_credentials = f"{ZOOM_CLIENT_ID}:{ZOOM_CLIENT_SECRET}"
    encoded_credentials = base64.b64encode(client_credentials.encode()).decode()

    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Authorization": f"Basic {encoded_credentials}"
    }

    data = {
        "grant_type": "account_credentials",
        "account_id": ZOOM_ACCOUNT_ID
    }

    response = requests.post('https://zoom.us/oauth/token', headers=headers, data=data)

    if response.status_code == 200:
        return response.json().get('access_token')
    else:
        return None

# create zoom meeting using the token
@employer.route('/create_meeting', methods=['POST', 'GET'])
def create_meeting(topic, type, start_time, duration, timezone):
    print("Inside create meeting function") 
    access_token = generate_access_token()

    if access_token:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {access_token}"            
        }

        data = {
            "topic": topic,
            "type": type,
            "start_time": start_time,
            "duration": duration,
            "timezone": timezone
        }

        response = requests.post('https://api.zoom.us/v2/users/me/meetings', headers=headers, json=data)
        # print(response)
        if response.status_code == 201:
            meeting_info = response.json()
            meeting_url = meeting_info.get('join_url')
            print("Meeting url inside the create meeting function: ",meeting_url)

            #print(f"Meeting URL: {meeting_url}")
            return jsonify({"message": "Zoom meeting created successfully", "meeting_info": response.json(), "meeting_url": meeting_url}), 201
        else:
            return jsonify({"message": "Failed to create Zoom meeting", "error": response.json()}), 500
        
    else:
        return jsonify({"message": "Failed to generate access token"}), 500    

# Jobs posting---UPDATED
@employer.route("/employer/post-jobs/", methods=['GET', 'POST'])
@user_role_required('employer')
def post_jobs():
    user = current_user.employers
    form = Job_Add()
    
    form.company_id.data = user.id


    if form.validate_on_submit():
        print("Inside Print job")
         # Access the questions directly from the request object
        num_questions = int(request.form['num_questions'])
        questions = [request.form[f'question_{i}'] for i in range(num_questions)]
        print("Questions:", questions)

        salary = form.salary.data if form.salary.data else 0
        job = Job(title=form.title.data.strip(), category=form.category.data, type=form.type.data, description=form.description.data, salary=salary, company=user)
        db.session.add(job)
        db.session.commit()
        
        job_id = job.id
        print("Job ID",job_id)
        # Save questions into the database
        interview_question = InterviewQuestion(
            questions=questions,
            job_id=job.id,  # Add job_id and applicant_id accordingly
            date_submitted=datetime.utcnow()
        )
        db.session.add(interview_question)
        db.session.commit()

        flash(f'New Job Added Successfully!', 'success')
        return redirect(url_for('.posted_jobs'))
    
        

    h = 'New Job'
    return render_template("employers/post_jobs.html", title="DEIR: Diversity, Equity, Inclusion, Retention", form=form, user=user, h=h)

#UPDATED
@employer.route("/employer/generate_description")
@user_role_required('employer')
def generate_description():
    job_title = request.args.get('job_title')
    category = request.args.get('category')
    num_titles = 3 
    #print("Job Title:", job_title)
    #print("Category:", category)

    if job_title and category:
        generated_titles = 0
        hashtags = ""
        description = hemingwai.generate_blog(
            blog_title=f"Propose a job description for a {job_title} position for women.",
            blog_keywords=category +" Female-friendly",
        )[0]["text"]
        
    
        while generated_titles < num_titles:
            product_hashtags = hemingwai.generate_blog_title(
                blog_intro=description,
                blog_keywords=[category],
            )
            #print("Hashtags",product_hashtags[0]['text'])

            if 'text' in product_hashtags[0]:
                blog_title = product_hashtags[0]['text'].split('\n\n')[0]
                
                # Check if the word 'Blog' is present in the title
                if 'Blog' not in blog_title:
                    hashtags += f"#{blog_title.replace(' ', '')} "  # Add hashtag with spacing
                    generated_titles += 1

                    # Check if you have reached the desired number of titles
                    if generated_titles >= num_titles:
                        break
        print("HashTags : ",hashtags)
        #print("Description:", description)
        response = {"description": description,
                    "hashtags": hashtags}
        return jsonify(response)
    else:
        return jsonify({"error": "Missing parameters job_title and category"}), 400
    
    
@employer.route("/employer/jobs/<int:job_id>/update", methods=['GET', 'POST'])
@user_role_required('employer')
def edit_jobs(job_id):
    user = current_user.employers
    job = Job.query.get_or_404(job_id)

    if not job.company == current_user.employers:
        abort(403)

    form = Job_Update()
    if form.validate_on_submit():
        job.title = form.title.data.strip()
        job.category = form.category.data.strip()
        job.type = form.type.data 
        job.description = form.description.data
        job.salary = form.salary.data if form.salary.data else 0

        db.session.commit()
        flash(f'Job Updated Successfully.', 'success')
        return redirect(url_for('.posted_jobs'))
  
    form.title.data = job.title 
    form.category.data = job.category
    form.salary.data = job.salary
    form.type.data = job.type
    form.description.data = job.description
    h = 'Update Job'
    return render_template("employers/post_jobs.html", title="DEIR: Diversity, Equity, Inclusion, Retention", form=form, user=user, job=job, h=h)

@employer.route("/employer/<int:job_id>/remove-job/", methods=['POST'])
@user_role_required('employer')
def remove_job(job_id):
    job = Job.query.get_or_404(job_id)
    if not job.company == current_user.employers:
        abort(403)

    db.session.delete(job)
    db.session.commit()
            
    flash(f'Job Removed Successfully!', 'success')
    return redirect(url_for('.posted_jobs'))

@employer.route("/employer/applicants/")
@user_role_required('employer')
def applicants():
    user = current_user.employers
    page = request.args.get('page', 1, type=int)

    query = db.session.query(Applicant, Job, jobs_applied.c.shortlisted, jobs_applied.c.date_applied).select_from(Applicant).join(jobs_applied).order_by(jobs_applied.c.date_applied).join(Job).filter_by(company=user).paginate(page=page, per_page=15)
    # Extract applicant IDs from the query result
    applicant_ids = [applicant.id for applicant, _, _, _ in query.items]
    print(applicant_ids)
    return render_template("employers/candidates.html", title="DEIR: Diversity, Equity, Inclusion, Retention", user=user, applicants=query)

@employer.route("/employer/applicants/<int:job_id>")
@user_role_required('employer')
def applicants_per_job(job_id):
    user = current_user.employers
    job = Job.query.get_or_404(job_id)
    page = request.args.get('page', 1, type=int)
    if not job.company == current_user.employers:
        abort(403)
    applicants = db.session.query(Applicant, jobs_applied.c.shortlisted, jobs_applied.c.date_applied).select_from(Applicant).join(jobs_applied).filter_by(job_id=job_id).join(Job).order_by(jobs_applied.c.date_applied).all()

    return render_template("employers/filtered.html", title="DEIR: Diversity, Equity, Inclusion, Retention", user=user, applicants=applicants, job=job)
from nltk.stem import PorterStemmer
from nltk.tokenize import word_tokenize

#Analyse Applicant Personality
@employer.route("/employer/infer_personality_scores/<int:applicant_id>/<int:job_id>")
@user_role_required('employer')
def infer_personality_scores(applicant_id, job_id):
    stemmer = PorterStemmer()

    user_id = applicant_id
   
    # Assuming the InterviewQuestion model has columns answer1 and answer2
    interview_question = InterviewQuestion.query.filter_by(applicant_id=user_id).first()
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


#List the applicants
@employer.route("/employer/applicants/shortlisted")
@user_role_required('employer')
def listed_applicants():
    user = current_user.employers
    print(user)
    page = request.args.get('page', 1, type=int)

    # Assuming you have a variable storing the applicant_id of the interviewed applicant
    interviewed_applicant_id = ...  # Replace this with the actual applicant_id

    query = (
        db.session.query(Applicant, Job)
        .select_from(Applicant)
        .join(jobs_applied)
        .filter_by(shortlisted=True)
        .filter(Applicant.id != interviewed_applicant_id)  # Exclude the interviewed applicant
        .join(Job)
        .filter_by(company=user)
        .paginate(page=page, per_page=15)
    )
    print("Query",query)
    # Get a list of applicant IDs after filtering
    shortlisted_applicant_ids = [applicant.id for applicant, _ in query.items]
    #print("Shortlisted Applicants IDs",shortlisted_applicant_ids)
    
    shortlisted_applicants_info = []
    for applicant_id in shortlisted_applicant_ids:
        # Get user_id from the Applicants table
        user_id = Applicant.query.filter_by(id=applicant_id).first().user_id
        print("User ID", user_id)
        # Get job_id from the JobsInquired table
        jobs_inquired_id = JobsInquired.query.filter_by(user_id=user_id).first().job_id
        similarity_score = None
        if jobs_inquired_id:
            job_description = Job.query.filter_by(id=jobs_inquired_id).first().description
            #print("Job Description for Job ID ",jobs_inquired_id," is as follows ",job_description)

            # Calculate similarity score
            similarity_score = compare_job_description(user_id, job_description)
            
            # Append the similarity score to the user
            shortlisted_user = {'id': user_id, 'similarity_score': similarity_score,'applicant_id':applicant_id}
            shortlisted_applicants_info.append(shortlisted_user)

            # Print similarity score inside the loop
            print(f"Similarity Score for User ID {user_id}: {similarity_score}")
    
    print("Shortlisted Applicants Info:", shortlisted_applicants_info)
    # Pass the shortlisted_applicants_info to the template
    return render_template("employers/listed.html", title="DEIR: Diversity, Equity, Inclusion, Retention", user=user, applicants=query, similarity_info=shortlisted_applicants_info)

from collections import Counter
import re
#Job Description to CV score
def compare_job_description(user_id, job_description):
    cv_details = SelectedApplicants.query.filter_by(user_id=user_id).first()

    cv_text = cv_details.education.lower()  # Assuming 'education' is the field containing CV text
    job_description = job_description.lower()

    # Tokenize the text into words using regular expressions
    cv_words = set(re.findall(r'\b\w+\b', cv_text))
    job_words = set(re.findall(r'\b\w+\b', job_description))

    # Calculate Jaccard similarity coefficient
    intersection_size = len(cv_words & job_words)
    union_size = len(cv_words | job_words)

    # Calculate the similarity as a percentage
    similarity_percentage = (intersection_size / union_size) * 100
    

    # Format the similarity percentage to two decimal places
    formatted_similarity_percentage = "{:.2f}".format(similarity_percentage)

    print("Similarity Percentage:", formatted_similarity_percentage)
    return float(formatted_similarity_percentage)
    

#Comparison Chart
@employer.route("/employer/compare-charts")
@user_role_required('employer')
def compare_charts():
    user = current_user.employers
    page = request.args.get('page', 1, type=int)

    # Assuming you have a variable storing the applicant_id of the interviewed applicant
    interviewed_applicant_id = ...  # Replace this with the actual applicant_id

    query = (
        db.session.query(Applicant, Job)
        .select_from(Applicant)
        .join(jobs_applied)
        .filter_by(shortlisted=True)
        .filter(Applicant.id != interviewed_applicant_id)  # Exclude the interviewed applicant
        .join(Job)
        .filter_by(company=user)
        .paginate(page=page, per_page=15)
    )

    # Get a list of applicant IDs after filtering
    shortlisted_applicant_ids  = [( applicant.user_id) for applicant, _ in query.items]
   # print("Short-listed Applicants",shortlisted_applicant_ids)

    # Call extract_education for each shortlisted applicant and collect responses
    response = []
    for applicant_id in shortlisted_applicant_ids:
        result = extract_education_for_applicant(applicant_id)
        response.append(result)
    print(response)

    return jsonify(response)

# Analyse CV 
def extract_education_for_applicant(applicant_id):
    
   
    # Assuming the InterviewQuestion model has columns answer1 and answer2
    cv_details = SelectedApplicants.query.filter_by(user_id=applicant_id).first()
    education = ""
    

    if cv_details:
        education = cv_details.education
        

    education_keywords = {
        'primary_education': ['G.C.E', 'Primary School', 'Elementary School','Diploma','Year'],
        'secondary_education': ['Ordinary','Level', 'High School', 'Secondary School','Semester','Year'],
        'higher_education': ['Advanced', 'Level','College', 'University', 'Bachelor', 'Master', 'Ph.D.','SLIIT','GPA'],
        # Add more levels and keywords as needed
    }
   
    
    primary_count = count_keywords(education, education_keywords['primary_education'])
    secondary_count = count_keywords(education, education_keywords['secondary_education'])
    higher_count = count_keywords(education, education_keywords['higher_education'])

    return {
        "applicant_id": applicant_id,
        "primary_count": primary_count,
        "secondary_count": secondary_count,
        "higher_count": higher_count
    }

# Add a function to count keywords
def count_keywords(text, keywords):
    return sum(text.lower().count(keyword.lower()) for keyword in keywords)


@employer.route("/employer/candidates/")
@user_role_required('employer')
def candidates():
    pass



# # Listing candidates and Sending email notifications to shortlisted applicants
@employer.route("/employer/list-applicant/<int:job_id>/<int:applicant_id>")
@user_role_required('employer')
def list_applicant(job_id, applicant_id):

    user = current_user.employers
    job = Job.query.get_or_404(job_id)
    applicant = Applicant.query.filter_by(id=applicant_id).first()
    email=User.query.filter_by(id=applicant.user_id).first().email
    if not job.company == user:
        abort(403)

    db.session.query(jobs_applied).filter((jobs_applied.c.job_id==job_id)&(jobs_applied.c.applicant_id==applicant_id)).update(dict(shortlisted = True))
    list = db.session.query(Job, Applicant, jobs_applied.c.date_applied).select_from(Job).join(jobs_applied).join(Applicant).filter((jobs_applied.c.job_id==job_id)&(jobs_applied.c.applicant_id==applicant_id)).first()

    try:
        # Update the shortlisted status
        db.session.query(jobs_applied).filter((jobs_applied.c.job_id == job_id) & (jobs_applied.c.applicant_id == applicant_id)).update(dict(shortlisted=True))
        db.session.commit()

        # Get details for the email
        list_details = db.session.query(Job, Applicant, jobs_applied.c.date_applied).select_from(Job).join(jobs_applied).join(Applicant).filter((jobs_applied.c.job_id == job_id) & (jobs_applied.c.applicant_id == applicant_id)).first()

        # Send the shortlist email
        send_shortlist_email(email, list_details[0].title, list_details[0].company.name, list_details[2])

        flash('Applicant listed and email sent successfully', 'success')
        return redirect(url_for('.listed_applicants'))

    except Exception as e:
        flash('Something went wrong! Please Try Again.', 'warning')
        print(str(e))
        return redirect(url_for('.applicants'))
    
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

#Send email for shortlisted Applicants
def send_shortlist_email(emails, job_title, company_name, application_date):
    print('Entering send_shortlist_email function')

    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['Subject'] = 'You have been shortlisted for a job'

    # Customize the email body with the job information
    body = f'Congratulations! You have been shortlisted for the following job:\n\n'
    body += f'Job Title: {job_title}\n'
    body += f'Company: {company_name}\n'
    body += f'Application Date: {application_date}\n'

    msg.attach(MIMEText(body, 'plain'))

    try:
        server = smtplib.SMTP(smtp_server, 587)
        server.starttls()
        server.login(sender_email, sender_password)

        
        msg['To'] = emails
        print(emails)
        server.sendmail(sender_email, emails, msg.as_string())

        server.quit()
        print('Email sent successfully')
    except Exception as e:
        print('Email sending failed:', str(e))

#Score Applicant Page -----UPDATED 
@employer.route('/score_applicant/<int:applicant_id>/<int:job_id>')
@user_role_required('employer')
def score_this_applicant(applicant_id,job_id):
    user = current_user.employers
    
    
    print("APPLICANT ID",applicant_id)
    print("JOB ID",job_id)
    applicant = Applicant.query.get_or_404(applicant_id)
    job = Job.query.get_or_404(job_id)
    user_id = Applicant.query.filter_by(id=applicant_id).first().user_id
    
    jobs_inquired_id = JobsInquired.query.filter_by(user_id=user_id).first().job_id
    job_description = Job.query.filter_by(id=jobs_inquired_id).first().description

    # Fetch applicant's answers from the PersonInt table
    applicant_answers = None
    persona_question = PersonInt.query.filter_by(applicant_id=user_id).first()

    #Fetching JSON Questions array and Answer Array for the applicant 
    applicant_answers = persona_question.answers
    applicant_ques = persona_question.questions

    similarity_score = compare_job_description(user_id, job_description)
    personality_score = infer_personality_scores(applicant_id)
    education_score = extract_education(user_id)

     # Query all employers except the current one
    emp_details = Employer.query.filter(Employer.id != user.id).all()

    # Preprocess the data before rendering the template
    applicant_questions_and_answers = zip(applicant_ques, applicant_answers)

     # Query all users except the current employer
    employers = User.query.filter((User.id != current_user.id) & (User.user_role == 'employer')).all()


    #Subemployer Score Report
    current_employer_id = Employer.query.filter(user_id != user.id).first().id
    print("CURRENT_EMPLOYER_ID",current_employer_id)
    #Extract the sub employer details which have the IDs of the employers(not user ids)
    sub_employers = SubEmployers.query.filter_by(employer_id=current_employer_id).all()
    
    scores_dict = {}
    if sub_employers:
        sub_employee_ids = [sub_emp.sub_employee_id for sub_emp in sub_employers]
        print("SUB EMPLOYEE IDS",sub_employee_ids)
        sub_employer_user_ids = [Employer.query.filter_by(user_id=sub_emp_id).first().id for sub_emp_id in sub_employee_ids]

        print("SUB EMPLOYEES",sub_employer_user_ids)
        # If there are sub-employers, extract their scores and the current employer's score
        #extract the scores of the sub employers using the USER_IDs of the employers(not ids)
        sub_employer_scores = ScoreApplicant.query.filter(ScoreApplicant.employer_id.in_(sub_employer_user_ids),
                                                           ScoreApplicant.applicant_id == applicant_id).all()

        current_employer_score = ScoreApplicant.query.filter_by(employer_id=current_employer_id,
                                                                applicant_id=applicant_id).first()
        if current_employer_score:
            print("SCOREEE OF CURRENT EMPLOYEEEEEE",current_employer_score.score)
            # Process the scores as needed
            # For example, create a dictionary with employer ID as key and score as value
            scores_dict = {current_employer_id: current_employer_score.score}
            for sub_employer_score in sub_employer_scores:
                scores_dict[sub_employer_score.employer_id] = sub_employer_score.score
                print("Dictionary",scores_dict)
    
    return render_template('employers/scoreApplicant.html',
                           applicant=applicant,
                           job=job,
                           applicant_questions_and_answers=applicant_questions_and_answers,
                           education_score=education_score,
                           personality_score=personality_score,
                           similarity_score=similarity_score,
                           job_description=job_description,
                           jobs_inquired_id=jobs_inquired_id,
                           user_id=user_id,
                           employers =employers,
                           scores_dict = scores_dict,
                           emp_details = emp_details, user=user)

#Add Sub Employee
@employer.route('/employer/add_subemployer/<int:employee_id>/<int:applicant_id>/<int:job_id>', methods=['GET', 'POST'])
@user_role_required('employer')
def add_subemployer(employee_id,applicant_id,job_id):
     print("Inside Add Sub employer Function")
     user = current_user.employers

     print("User. ID in count",user.id)
     print("Sub Employee ID in count", employee_id)
     print("Applicant ID in count", applicant_id)
    # Check the current count of sub-employees for the same applicant ID and same employee
     current_applicant_sub_employees_employees_applicant_count = SubEmployers.query.filter_by(employer_id=user.id,applicant_id=applicant_id).count()
     print("current_applicant_sub_employees_employees_applicant_count",current_applicant_sub_employees_employees_applicant_count)
     
     # Limit the number of sub-employees to 3 for the same applicant ID
     if current_applicant_sub_employees_employees_applicant_count >= 3:
        flash('You can invite at most 3 sub-employees for the same applicant.', 'warning')
        return redirect(url_for('employer.score_this_applicant', applicant_id=applicant_id, job_id=job_id))
    
    
     existing_relationship = SubEmployers.query.filter_by(employer_id=user.id, sub_employee_id=employee_id,applicant_id=applicant_id).first()
     
     print("Relationship",existing_relationship)
     if existing_relationship:
        print("Yes")
        flash('You have already invited this sub-employee to score.', 'warning')
     else:
         
         # Create a new relationship
         new_relationship = SubEmployers(employer_id=user.id, sub_employee_id=employee_id,applicant_id= applicant_id,date_invited=datetime.utcnow())
         db.session.add(new_relationship)
         db.session.commit()
         flash('Successfully invited sub-employee to score.', 'success')

         return redirect(url_for('employer.score_this_applicant', applicant_id=applicant_id, job_id=job_id))

     # If it's a GET request or if the relationship already exists, redirect to a different page or handle accordingly
     return redirect(url_for('employer.score_this_applicant', applicant_id=applicant_id, job_id=job_id))


# @employer.route('/employer/score_report/<int:applicant_id>')
# @user_role_required('employer')
# def score_report(applicant_id):
#     # Get the current employer's ID (assuming you have access to it)
#     user = current_user.employers  # You need to implement this function
#     current_employer_id = user.id
#     print("Current Employer ID under Score report",current_employer_id)
#     # Check if there are any sub-employers for the current employer
#     sub_employers = SubEmployers.query.filter_by(employer_id=current_employer_id).all()
    
#     if sub_employers:
#         # If there are sub-employers, extract their scores and the current employer's score
#         sub_employer_scores = ScoreApplicant.query.filter(ScoreApplicant.employer_id.in_([sub_emp.sub_employee_id for sub_emp in sub_employers]),
#                                                            ScoreApplicant.applicant_id == applicant_id).all()

#         current_employer_score = ScoreApplicant.query.filter_by(employer_id=current_employer_id,
#                                                                 applicant_id=applicant_id).first()

#         # Process the scores as needed
#         # For example, create a dictionary with employer ID as key and score as value
#         scores_dict = {current_employer_id: current_employer_score.score}
#         for sub_employer_score in sub_employer_scores:
#             scores_dict[sub_employer_score.employer_id] = sub_employer_score.score

#         return jsonify(scores_dict)
#     else:
#         # Handle the case where there are no sub-employers
#         return jsonify({"message": "No sub-employers found for the current employer."}), 404
    
from sqlalchemy import exists, and_

@employer.route('/submit_scores_subemployer/<int:applicant_id>', methods=['GET', 'POST'])
@user_role_required('employer')
def submit_scores_subemployer(applicant_id):
    print("submit_scores_subemployer")
    user = current_user.employers
    
    job_posts = user.jobs
    applicants = db.session.query(Applicant).select_from(Applicant).join(jobs_applied).join(Job).filter_by(company=user).all()
    listed = db.session.query(Applicant).select_from(Applicant).join(jobs_applied).filter_by(shortlisted=True).join(Job).filter_by(company=user).all() 
    # Fetch all applicants assigned to the sub-employer, excluding those who are already scored
    assigned_applicants = db.session.query(Applicant).join(SubEmployers).filter(
        SubEmployers.sub_employee_id == user.id,
        ~exists().where(and_(ScoreApplicant.applicant_id == Applicant.id, ScoreApplicant.employer_id == user.id))
    ).all()
    print("submit_scores_subemployer applicantID",assigned_applicants)
    # Fetch scores for each assigned applicant
    applicant_scores = {}
    for applicant in assigned_applicants:
            print("Applicant ID in account.html",applicant.id)
            user_id = Applicant.query.filter_by(id=applicant.id).first().user_id
    
            jobs_inquired_id = JobsInquired.query.filter_by(user_id=user_id).first().job_id
            job_description = Job.query.filter_by(id=jobs_inquired_id).first().description

            similarity_score = compare_job_description(user_id, job_description)
            personality_score = infer_personality_scores(applicant.id)
            education_score = extract_education(user_id)


            # Store scores in the dictionary
            applicant_scores[applicant.id] = {
                'job_description': job_description,
                'similarity_score': similarity_score,
                'personality_score': personality_score,
                'education_score': education_score
            }

    if request.method == 'POST':
        your_score = request.form.get('your_score')

        # Check if the score is provided in the form
        if your_score is not None and your_score != '':
            try:
                your_score = float(your_score)
                print("Your Score", your_score)

                # Save the score for the current employer
                score_for_applicant = ScoreApplicant(employer_id=user.id, applicant_id=applicant_id, score=your_score)
                db.session.add(score_for_applicant)
                db.session.commit()
                flash('Scores submitted successfully.', 'success')
                return render_template("employers/account.html", title="DEIR: Diversity, Equity, Inclusion, Retention", jobs=job_posts, applicants=applicants, user=user,listed=listed, assigned_applicants=assigned_applicants, applicant_scores=applicant_scores)

            except ValueError:
                flash('Invalid score format. Please enter a valid number.', 'error')


    return render_template("employers/account.html", title="DEIR: Diversity, Equity, Inclusion, Retention", jobs=job_posts, applicants=applicants, listed=listed, user=user,assigned_applicants=assigned_applicants, applicant_scores=applicant_scores)


@employer.route('/submit_scores/<int:applicant_id>/<int:job_id>', methods=['GET', 'POST'])
@user_role_required('employer')
def submit_scores(applicant_id, job_id):
    user = current_user.employers
    applicant = Applicant.query.get_or_404(applicant_id)

    # Check if the current employer is a sub-employer
    is_sub_employer = SubEmployers.query.filter_by(employer_id=user.id).first() is not None
    print("Is or is not sub employee", is_sub_employer)    
    # Check if the current employer is allowed to access the page
    if not is_sub_employer and user.id != applicant.user_id:
        flash("You are not allowed to access this page.", "warning")
        return redirect(url_for("employers/listed.html"))  # Replace 'some_other_page' with the appropriate route

    if request.method == 'POST':
        your_score = request.form.get('your_score')

        # Check if the score is provided in the form
        if your_score is not None and your_score != '':
            try:
                your_score = float(your_score)
                print("Your Score", your_score)

                # Save the score for the current employer
                score_for_applicant = ScoreApplicant(employer_id=user.id, applicant_id=applicant_id, score=your_score)
                db.session.add(score_for_applicant)

                # Save the scores for sub-employees if the current employer is a sub-employer
                if is_sub_employer:
                    sub_employees = SubEmployers.query.filter_by(employer_id=user.id).all()
                    for sub_employee in sub_employees:
                        sub_employee_id = sub_employee.sub_employee_id
                        sub_employee_score = request.form.get(f'sub_{sub_employee_id}_score')

                        # Check if the sub-employee score is provided
                        if sub_employee_score is not None and sub_employee_score != '':
                            sub_employee_score = float(sub_employee_score)
                            score_for_sub_employee = ScoreApplicant(employer_id=user.id, applicant_id=applicant.id, score=sub_employee_score)
                            db.session.add(score_for_sub_employee)

                db.session.commit()
                flash('Scores submitted successfully.', 'success')
                return redirect(url_for('employer.score_this_applicant', applicant_id=applicant_id, job_id=job_id))
            except ValueError:
                flash('Invalid score format. Please enter a valid number.', 'error')

    return render_template('employers/submitScores.html', applicant=applicant, is_sub_employer=is_sub_employer)

#Interview Applicant Page 
@employer.route('/interview_applicant/<int:applicant_id>/<int:job_id>')
@user_role_required('employer')
def interview_applicant_page(applicant_id, job_id):
    # Your logic here
    user = current_user.employers
    job = Job.query.get_or_404(job_id)
    applicant = Applicant.query.get_or_404(applicant_id)

    return render_template('employers/interview_applicant.html', user=user, job=job, applicant=applicant)

#Employer send interview Questions-------UPDATED
@employer.route('/send_interview_questions/<int:applicant_id>/<int:job_id>', methods=['POST'])
@user_role_required('employer')
def send_interview_questions(applicant_id, job_id):
    if request.method == 'POST':
        # Get data from the form
        question1 = request.form.get('question1')
        question2 = request.form.get('question2')

        # Fetch existing interview questions for the specific job and applicant
        interview_question = InterviewQuestion.query.filter_by(job_id=job_id).first()
        persona_question = PersonInt.query.filter_by(applicant_id=applicant_id).first()
        
        print("Existing Questions:", interview_question)
        existing_questions = []

        # Store the personalized interview question in the new table
        if interview_question:
            # Update existing questions with new ones
            existing_questions = interview_question.questions
            existing_questions.append(question1)
            existing_questions.append(question2)
            print("New Questions array:", existing_questions)

            # Check if answers exist, keep them, otherwise set to None
            answers = persona_question.answers if persona_question and persona_question.answers else None

            personalized_int = PersonInt(
                job_id=int(job_id),
                applicant_id=int(applicant_id),
                questions=existing_questions,
                answers=answers
            )
        
            db.session.add(personalized_int)
            db.session.commit()

            return redirect(url_for('employer.listed_applicants', job_id=job_id))

    return redirect(url_for('employer.error_page'))  # Handle other cases or redirect if necessary

@employer.route('/success_page/<int:applicant_id>')
@user_role_required('employer')
def success_page(applicant_id):
    user = current_user.employers
    # Render the success page with the applicant_id
    return render_template('employer/success_page.html', applicant_id=applicant_id, user=user)


# This notifications path used for display transcripts for employer hence there are no notifications for the employer
@employer.route("/employers/notifications/")
@user_role_required('employer')
def notifications():
    user = current_user.employers
    return render_template('/employers/notifications.html', user=user)
    pass # pass statement is a placeholder & it does not provide any value to the client

# employer account settings
@employer.route("/employer/settings/", methods=['GET', 'POST'])
@user_role_required('employer')
def settings():
    user = current_user.employers
    form = Employer_User_Update()

    if form.validate_on_submit():
        user.name = form.name.data.strip().upper()
        user.user.email = form.email.data.lower()
        user.phone = form.phone.data 
        user.location = form.location.data 
        user.tagline = form.tagline.data 
        user.description = form.description.data 
        user.website = form.website.data 

        if form.logo.data:
            new_file = save_file('employer/logo/', form.logo.data)
            if new_file:
                if user.logo != 'company.png':
                    old_file = f'employer/logo/{str(user.logo)}'
                    remove_file(old_file)
                
                user.logo = new_file

        db.session.commit()
        flash(f'Account Updated Successfully.', 'success')
        return redirect(url_for('.settings'))
  
    form.name.data = user.name 
    form.email.data = user.user.email
    form.phone.data = user.phone
    form.location.data = user.location
    form.tagline.data = user.tagline
    form.description.data = user.description
    form.website.data = user.website

    return render_template("employers/settings.html", title="DEIR: Diversity, Equity, Inclusion, Retention", form=form, user = user)

#Employer Delete Profile_Picture
@employer.route("/employer/<int:employer_id>/delete-logo", methods=['POST'])
@user_role_required('employer')
def delete_image(employer_id):
    user = Employer.query.get_or_404(employer_id)
    if not user.user == current_user:
        abort(403)

    if user.logo and user.logo != "company.png":
        file = f'employer/logo/{str(user.logo)}'
        try:
            remove_file(file)
            user.logo = 'company.png'
            db.session.commit()
            flash(f'Logo Removed Successfully!', category='success')
        except FileNotFoundError:
            user.logo = 'company.png'
            db.session.commit()
            flash(f'File not Found!', category='danger')
    
    return redirect(url_for('.settings'))

# employer account sign in
@employer.route("/employer/login/", methods=['GET', 'POST'])
def employer_login():
    if current_user.is_authenticated and current_user.employers:
        return redirect(url_for('.employer_account'))
    form = User_Login()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and user.employers and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user, remember=form.remember.data)
            flash(f'Login successs.', 'info')

            return redirect(request.args.get('next') or url_for('.employer_account'))
        else:
            flash(f'Invalid Email or Password! Please Try Again.', 'danger')
    return render_template("employers/login.html", title="DEIR: Diversity, Equity, Inclusion, Retention", form=form)

# employer registration
@employer.route("/employer/signup/", methods=['GET', 'POST'])
def employer_signup():
    if current_user.is_authenticated and current_user.employers:
        return redirect(url_for('.employer_account'))
    form = Employer_Signup()
    if form.validate_on_submit():
        pw_hash = bcrypt.generate_password_hash(form.password.data).decode('utf-8')

        user = User(email=form.email.data.lower(), user_role='employer', password=pw_hash)
        db.session.add(user)

        if form.logo.data:
            logo = save_file('employer/logo/', form.logo.data) 
            employer = Employer(name=form.name.data.strip().upper(), location=form.location.data.strip().capitalize(), phone=form.phone.data, tagline=form.tagline.data, description=form.description.data, website=form.website.data, logo=logo, user=user)
            db.session.add(employer)
            db.session.commit()
        else:
            employer = Employer(name=form.name.data.strip().upper(), location=form.location.data.strip().capitalize(), phone=form.phone.data, tagline=form.tagline.data, description=form.description.data, website=form.website.data, user=user)
            db.session.add(employer)
            db.session.commit()

        flash(f'Account Successfully created for {form.email.data}!', 'success')
        login_user(user, remember=True)
        return redirect(url_for('.employer_account'))        
    return render_template("employers/signup.html", title="DEIR: Diversity, Equity, Inclusion, Retention", form=form)


# Employer User password reset request
@employer.route("/employer/password-reset", methods=['GET', 'POST'])
def password_reset_request():
    if current_user.is_authenticated and current_user.employers:
        return redirect(url_for('.employer_account'))
    form = Forgot_Password()

    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and user.employers:
            # Remove the try-except block for testing
            token = user.get_reset_token()
            print(f"Token: {token}")
            reset_url = url_for('.password_reset_link', token=token, _external=True)
            print(f"Reset URL: {reset_url}")

            # Send the password reset email
            send_pwd_reset_email(user.email, reset_url, 'employer', user.employers.name)

            flash('A password reset link has been sent to your email', 'info')
            return redirect(url_for('.employer_login'))
        else:
            flash('Email not registered. Send the email you registered your account with.', 'warning')
            return redirect(url_for('.password_reset_request'))
    return render_template("forgot_password.html", title="DEIR: Diversity, Equity, Inclusion, Retention", form=form)

@employer.route("/employer/send-message/<int:applicant_id>", methods=['GET', 'POST'])
@user_role_required('employer')
def send_message(applicant_id):
    
    if request.method == 'POST':
        recipient = request.form['recipient']
        subject = request.form['subject']
        body = request.form['body']
        meeting_time = request.form['meeting-time']
        meeting_topic = request.form['meeting-topic']
        meeting_duration = request.form['meeting-duration']

        
        if recipient and subject and body and meeting_time and meeting_topic and meeting_duration:
            # Call create_meeting with individual arguments
            meeting_creation_response = create_meeting(
                meeting_topic,
                2,  # Assuming 2 is for a scheduled meeting type
                meeting_time,
                int(meeting_duration),
                'UTC'  # Assuming the timezone is UTC
            )

            print("Meeting creation response:", meeting_creation_response)
            
            meeting_url = ""
            # Extract the response from the tuple
            response, status_code = meeting_creation_response
            
            # Check the status code
            if status_code == 201:
                # Extract meeting URL from the JSON response
                meeting_url = response.json.get('meeting_url')
                print("Meeting URL in another function:", meeting_url)
            else:
                print(f"Failed to create Zoom meeting. Status code: {status_code}")
            body_with_meeting_details = f"{body}\n\nMeeting Details:\nTopic: {meeting_topic}\nTime: {meeting_time}\nDuration: {meeting_duration}\nMeeting URL:{meeting_url}"

            msg = Message(subject=subject, recipients=[recipient])
            msg.body = body_with_meeting_details
            msg.sender="udn992110@gmail.com"
            print("Meeting URL outside of the create Zoom meeting Function", meeting_url)
            
            success = store_notification(recipient, subject, body_with_meeting_details, meeting_time, meeting_topic, meeting_duration, meeting_url)
            
            try:
                mail.send(msg)
                flash('Email sent successfully!', 'success')
                
                if success:
                    print("send message function successfully executed!")
                    return render_template('employer/applicants.html', title='DEIR: Diversity, Equity, Inclusion, Retention',
                                           applicant_id=applicant_id, meeting_creation_response=meeting_creation_response, meeting_url=meeting_url)
                else:
                    print("error in the sending message part!")
                    return redirect(url_for('employer.applicants', applicant_id=applicant_id))
            except Exception as e:
                #flash(f'Failed to send email: {str(e)}', 'danger')
                return redirect(url_for('employer.applicants', applicant_id=applicant_id))
        else:

            flash('All fields are required', 'danger')

    return render_template('employer/candidates.html', title='DEIR: Diversity, Equity, Inclusion, Retention', applicant_id=applicant_id)

@employer.route("/employer/meeting-details/<int:applicant_id>")
@user_role_required('employer')
def meeting_details(applicant_id):
    user = current_user.employers
    print("Inside meeting details route")
    # Fetch the applicant's email from the Applicant table
    user_id = db.session.query(Applicant.user_id).filter(Applicant.id == applicant_id).scalar()

    # Check if the applicant exists
    if not user_id:
        abort(404)  # Or handle the case where the applicant is not found

    applicant_email = db.session.query(User.email).filter(User.id==user_id).scalar()
    print(applicant_email)
    # Fetch meeting details from the Notification table based on the applicant's email
    notification_details = db.session.query(Notification).filter(Notification.recipient == applicant_email).first()
    print(notification_details)
    # Check if the notification details exist
    if not notification_details:
        abort(404)  # Or handle the case where details are not found

    return render_template('employers/meeting_details.html', user=user, notification_details=notification_details)

def store_notification(recipient, subject, body_with_meeting_details, meeting_time, meeting_topic, meeting_duration, meeting_url):
    try:
        new_notification = Notification(
            recipient=recipient,
            subject=subject,
            body=body_with_meeting_details,
            meeting_time=datetime.strptime(meeting_time, '%Y-%m-%dT%H:%M'),  # Example format, adjust as per your input
            meeting_topic=meeting_topic,
            meeting_duration=int(meeting_duration),
            meeting_url=meeting_url
        )
        db.session.add(new_notification)
        db.session.commit()
        print("DATA STORED SUCESSFULLYYYYYYYYY!")
        return True  # Return True if successfully stored
    except Exception as e:
        print(f"Failed to store notification: {str(e)}")
        print("data not stored!")
        return False  # Return False if an error occurred while storing


# Employer user password reset token
@employer.route("/employer/password-reset/<string:token>", methods=['GET', 'POST'])
def password_reset_link(token):
    if current_user.is_authenticated and current_user.employers:
        return redirect(url_for('.employer_account'))
    
    user = User.verify_reset_token(token)

    if not user or not user.employers:
        flash('The link is either invalid or has expired!', 'warning')
        return redirect(url_for('.password_reset_request'))

    form = Reset_Password()

    if form.validate_on_submit():
        pw_hash = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user.password = pw_hash
        db.session.commit()

        flash('Your Password has been updated', 'success')
        return redirect(url_for('.employer_login'))

    # Debugging print statements
    print(f"Token: {token}")
    print(f"User: {user}")
    print(f"User.employers: {user.employers if user else None}")

    return render_template("reset_password.html", title="DEIR: Diversity, Equity, Inclusion, Retention", form=form)
from flask_mail import Message
from flask import current_app

from collections import defaultdict
import json
def infer_personality_scores(user_id):
    stemmer = PorterStemmer()
    print("User id",user_id)
    # Assuming the InterviewQuestion model has a column called answers storing JSON array
    interview_questions = PersonInt.query.filter_by(applicant_id=user_id).first()
    answers = []
    if interview_questions:
        answers = json.loads(interview_questions.answers)

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
            for answer in answers:
                scores[trait] += sum(stem_and_tokenize(answer).count(stemmed_keyword) for answer in answers)

    total_words = sum(len(word_tokenize(answer)) for answer in answers)
    # Check if total_words is zero to avoid ZeroDivisionError
    if total_words == 0:
        percentage_scores = {trait: 0 for trait in personality_keywords}
    else:
        percentage_scores = {trait: (score / total_words) * 100 for trait, score in scores.items()}
    
    response = {"person_score": percentage_scores}
    return response



def extract_education(user_id):
  
    # Assuming the InterviewQuestion model has columns answer1 and answer2
    cv_details = SelectedApplicants.query.filter_by(user_id=user_id).first()
    education = ""
    

    if cv_details:
        education = cv_details.education
        

    education_keywords = {
        'primary_education': ['G.C.E', 'Primary School', 'Elementary School','Diploma','Year'],
        'secondary_education': ['Ordinary','Level', 'High School', 'Secondary School','Semester','Year'],
        'higher_education': ['Advanced', 'Level','College', 'University', 'Bachelor', 'Master', 'Ph.D.','SLIIT','GPA'],
        # Add more levels and keywords as needed
    }
   
    
    primary_count = count_keywords(education, education_keywords['primary_education'])
    secondary_count = count_keywords(education, education_keywords['secondary_education'])
    higher_count = count_keywords(education, education_keywords['higher_education'])

    # Construct the response
    responses = {
        "primary_count": primary_count,
        "secondary_count": secondary_count,
        "higher_count": higher_count
    }

    # Print scores to the console
    print("Primary Count:", primary_count)
    print("Secondary Count:", secondary_count)
    print("Higher Count:", higher_count)
    
    return responses


# Helper function to send password reset email
def send_pwd_reset_email(email, reset_url, user_role, name):
    msg = Message('Password Reset Request', sender=('Dhananjana', 'udn992110@gmail.com'), recipients=[email])

    # Add HTML version of the email
    msg.html = render_template('email/reset_password.html', reset_url=reset_url)

    # Add text version of the email
    msg.body = f'''
    To reset your password, visit the following link:
    {reset_url}

    If you did not make this request, simply ignore this email.
    '''

    try:
        mail.send(msg)
        print('Email sent successfully')
    except Exception as e:
        print('Email sending failed:', str(e))


# Company search
@employer.route("/company/search", methods=['POST'])
def company_search():
    form1 = Company_Search()
    form = request.form
    name_or_location = form['name']
    search = "%{0}%".format(name_or_location)

    page = request.args.get('page', 1, type=int)
    companies = Employer.query.filter((Employer.name.like(search) | Employer.location.like(search))).order_by(Employer.name.desc()).paginate(page=page, per_page=15) 
    
    head = f'Search Results for "{name_or_location}": {companies.total}'
    return render_template("employers/list.html", title="DEIR: Diversity, Equity, Inclusion, Retention", companies=companies, head=head, form1=form1)


@employer.route("/employer/delete-profile", methods=['GET', 'POST'])
@user_role_required('employer')
def employer_account_delete():
    userd = current_user.employers
    user = current_user
    employer_id = Employer.query.filter_by(user_id=user.id).first().id
    job_inquired = JobsInquired.query.filter_by(company_id=employer_id).first()

    job_id = job_inquired.job_id if job_inquired else None


    print("CURRENT USER IN DELETE PROFILE", user)

    if request.method == 'POST':
        password = request.form.get('delete-profile-pass')
        if user and bcrypt.check_password_hash(user.password, password):
            try:
                for employer in Employer.query.filter_by(user_id=user.id).all():
                    db.session.delete(employer)
                
               
                for score in ScoreApplicant.query.filter_by(employer_id=employer_id).all():
                    db.session.delete(score)
               
               
                for question in InterviewQuestion.query.filter_by(job_id=job_id).all():
                    db.session.delete(question)

                
                for applied_job in JobsInquired.query.filter_by(company_id=employer_id).all():
                    db.session.delete(applied_job)

                
                for jobs_posted in Job.query.filter_by(company_id=employer_id).all():
                    db.session.delete(jobs_posted)

               
                for assigned_subemp in SubEmployers.query.filter_by(employer_id=employer_id).all():
                    db.session.delete(assigned_subemp)

                db.session.delete(user)

                db.session.commit()
                logout_user()
                flash('Your profile has been successfully deleted.', 'success')
                return redirect(url_for('.employer_login'))

            
            except Exception as e:
                print(f"Error deleting profile: {str(e)}")
                flash('An error occurred while deleting your profile. Please try again later.', 'danger')
                return redirect(url_for('.employer_account_delete'))

        else:
            flash(f'Invalid Password! Please Try Again.', 'danger')
            return redirect(url_for('.employer_account_delete'))
        
    else:
        return render_template("employers/delete-profile.html", title="DEIR: Diversity, Equity, Inclusion, Retention",  user=userd)
    










@employer.route("/employers/messages")
@user_role_required('employer')
def messages():
    user = current_user.employers
    return render_template('/employers/messages.html', title="DEIR: Diversity, Equity, Inclusion, Retention" , user=user)


@employer.route("/employers/meetings")
@user_role_required('employer')
def meetings():
    user = current_user.employers
    return render_template('/employers/meetings.html', title="DEIR: Diversity, Equity, Inclusion, Retention", user=user)



@employer.route('/employers/change-password/', methods=['GET','POST'])
@user_role_required('employer')
def change_password():
    userd = current_user.employers
    user = current_user
    form = Change_Password()
    if form.validate_on_submit():
        user_query = User.query.filter_by(email=user.email).first()
        if user_query and user_query.employers and bcrypt.check_password_hash(user_query.password, form.old_password.data):
            pw_hash = bcrypt.generate_password_hash(form.new_password.data).decode('utf-8')
            user.password = pw_hash
            db.session.commit()
            flash(f'Password Updated Successfully.', 'success')
            return redirect(url_for('.employer_account'))
        else:
            flash(f'Current Password is Wrong! Please Try Again.', 'danger')

    return render_template("employers/change_password.html",title="DEIR: Diversity, Equity, Inclusion, Retention", user=userd, form=form)