
from OraApp import db
from OraApp.models import Job, jobs_applied, Employer,JobsInquired
from flask import render_template, Blueprint, request, abort
from OraApp.forms import Job_Search
from flask_login import login_user, current_user
from OraApp.utils import user_role_required

jobs = Blueprint('jobs', __name__)

def get_user():
    user = None
    if current_user.is_authenticated:
        if current_user.employers:
            user = current_user.employers
        elif current_user.applicants:
            user = current_user.applicants
    return user

# Job details
@jobs.route("/jobs/<int:job_id>/details/")
@user_role_required('applicant')
def profile(job_id):
    user_id = current_user.id
    user = get_user()
    print("Job Route User ID",user_id)
    print("Job Route JOB ID",job_id)
    
    job = Job.query.get_or_404(job_id)
    company_id = job.company_id
    print(company_id)

     # Create and add a new Application record
    application = JobsInquired(job_id=job_id, company_id=company_id, user_id=user_id)
    db.session.add(application)
    db.session.commit()

    query = db.session.query(jobs_applied.c.shortlisted).filter_by(job_id=job_id)
    return render_template("jobs/profile.html", title="DEIR: Diversity, Equity, Inclusion, Retention", user=user, job=job, query=query)

# List of all jobs
@jobs.route("/jobs/")
@jobs.route("/jobs/list/")
def job_list():
    user = get_user()
    form1 = Job_Search()
    page = request.args.get('page', 1, type=int)
    jobs = Job.query.order_by(Job.date_posted.desc()).paginate(page=page, per_page=15)

    query = db.session.query(Job.category.distinct().label('category'))
    filtered = Job.query
    categories = [row.category for row in query.all()]
    return render_template("jobs/list.html", title="DEIR: Diversity, Equity, Inclusion, Retention",user=user, jobs=jobs, filtered=filtered, form1=form1, categories=categories)

@jobs.route("/jobs/categories/")
def categories():
    user = get_user()
    form1 = Job_Search()
    page = request.args.get('page', 1, type=int)
    query = db.session.query(Job.category.distinct().label('category')).paginate(page=page, per_page=15)
    jobs = Job.query
    categories = [row.category for row in query.items]
    return render_template("jobs/categories.html", title="DEIR: Diversity, Equity, Inclusion, Retention",user=user, jobs=jobs, form1=form1, categories=categories,pages=query)

# Filter jobs by category
@jobs.route("/jobs/categories/<string:category>")
def filtered(category):
    user = get_user()
    form1 = Job_Search()
    page = request.args.get('page', 1, type=int)
    jobs = Job.query.filter_by(category=category).order_by(Job.date_posted.desc()).paginate(page=page, per_page=15) or abort(404)
    
    head = f'{category} Jobs'
    return render_template("jobs/filtered.html", title="DEIR: Diversity, Equity, Inclusion, Retention",user=user, jobs=jobs, form1=form1, head=head)

# Jobs search
@jobs.route("/jobs/search", methods=['POST'])
def job_search():
    user = get_user()
    form1 = Job_Search()
    form = request.form
    title_or_category = form['title']
    location = form['location']
    search1 = "%{0}%".format(title_or_category)
    search2 = "%{0}%".format(location)

    page = request.args.get('page', 1, type=int)

    jobs = db.session.query(Job).select_from(Job).filter((Job.title.like(search1) | Job.category.like(search1))).join(Employer).filter(Employer.location.like(search2)).order_by(Job.date_posted.desc()).paginate(page=page, per_page=15) 

    
    locations = f'in "{ location }"' if location else ''
    head = f'Search Results for "{ title_or_category }" {locations}'
    return render_template("jobs/filtered.html", title="DEIR: Diversity, Equity, Inclusion, Retention",user=user, jobs=jobs, head=head, form1=form1)