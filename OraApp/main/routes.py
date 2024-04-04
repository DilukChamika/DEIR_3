from OraApp import db
from flask import render_template, Blueprint, url_for, flash, redirect,request
from flask_login import logout_user, current_user
from OraApp.forms import Job_Search
from OraApp.models import Job, Applicant

main = Blueprint('main', __name__)

def get_user():
    user = None
    if current_user.is_authenticated:
        if current_user.employers:
            user = current_user.employers
        elif current_user.applicants:
            user = current_user.applicants
    return user

@main.route("/")
def home():
    form1 = Job_Search()
    page = request.args.get('page', 1, type=int)
    jobs = Job.query.order_by(Job.date_posted.desc()).paginate(page=page, per_page=15)

    query = db.session.query(Job.category.distinct().label('category'))
    filtered = Job.query
    categories = [row.category for row in query.all()]

    if current_user.is_authenticated:
        user = current_user.user_role
        return redirect(url_for(f'{user}.{user}_account'))
    return render_template("index.html", title="DEIR: Diversity, Equity, Inclusion, Retention", form1=form1,jobs=jobs, filtered=filtered, categories=categories)

@main.route("/about-us")
def about():
    user = get_user()
    return render_template("about.html", title="DEIR: Diversity, Equity, Inclusion, Retention", user=user)


@main.route("/about-us-ourstory")
def aboutourstory():
    user = get_user()
    return render_template("ourstory.html", title="DEIR: Diversity, Equity, Inclusion, Retention", user=user)

@main.route("/our-vision-and-mission")
def ourvnm():
    user = get_user()
    return render_template("our-vision-n-mission.html", title="DEIR: Diversity, Equity, Inclusion, Retention", user=user)

@main.route("/our-team")
def ourteam():
    user = get_user()
    return render_template("our-team.html", title="DEIR: Diversity, Equity, Inclusion, Retention", user=user)

@main.route("/blog")
def blog():
    user = get_user()
    return render_template("blog.html", title="DEIR: Diversity, Equity, Inclusion, Retention", user=user)

@main.route("/donate")
def donate():
    user = get_user()
    return render_template("donate.html", title="DEIR: Diversity, Equity, Inclusion, Retention", user=user)

@main.route("/faq")
def faq():
    user = get_user()
    return render_template("faq.html", title="DEIR: Diversity, Equity, Inclusion, Retention", user=user)

@main.route("/contact-us")
def contactus():
    user = get_user()
    return render_template("contactus.html", title="DEIR: Diversity, Equity, Inclusion, Retention", user=user)

@main.route("/privacy-policy")
def privacypolicy():
    user = get_user()
    return render_template("privacypolicy.html", title="DEIR: Diversity, Equity, Inclusion, Retention", user=user)

@main.route("/terms-and-conditions")
def termsncond():
    user = get_user()
    return render_template("termsnconditions.html", title="DEIR: Diversity, Equity, Inclusion, Retention", user=user)

@main.route("/data-retention-policy")
def drp():
    user = get_user()
    return render_template("drp.html", title="DEIR: Diversity, Equity, Inclusion, Retention", user=user)

@main.route("/candidates")
def candidates():
    user = get_user()
    users = Applicant.query.all()
    return render_template("candidates.html", title="DEIR: Diversity, Equity, Inclusion, Retention", user=user, candidates=users)

@main.route("/packages")
def packages():
    user = get_user()
    return render_template("packages.html", title="DEIR: Diversity, Equity, Inclusion, Retention", user=user)







@main.route("/logout")
def logout():
    logout_user()
    flash(f'Logged Out successfully.', 'primary')
    return redirect(url_for('.home'))


