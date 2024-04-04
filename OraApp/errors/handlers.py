from flask import render_template, Blueprint
from flask_login import current_user

errors = Blueprint('errors', __name__)



def render_error_template(error_code):
    title = f"OraJobs | Error: {error_code}"
    user = current_user.employers if current_user.is_authenticated and current_user.employers else current_user.applicants if current_user.is_authenticated and current_user.applicants else None
    return render_template(f"errors/{error_code}.html", title=title, user=user), error_code

@errors.app_errorhandler(403)
def error_403(error):
    return render_error_template(403)

@errors.app_errorhandler(404)
def error_404(error):
    return render_error_template(404)

@errors.app_errorhandler(405)
def error_405(error):
    return render_error_template(405)

@errors.app_errorhandler(500)
def error_500(error):
    return render_error_template(500)



# @errors.app_errorhandler(403)
# def error_403(error):
#     if current_user.is_authenticated and current_user.employers:
#         user = current_user.employers
#         return render_template("errors/403.html", title="OraJobs | Error: 403", user=user), 403
#     elif current_user.is_authenticated and current_user.applicants:
#         user = current_user.applicants
#         return render_template("errors/403.html", title="OraJobs | Error: 403", user=user), 403
#     else:
#         return render_template("errors/403.html", title="OraJobs | Error: 403"), 403


# @errors.app_errorhandler(404)
# def error_404(error):
#     if current_user.is_authenticated and current_user.employers:
#         user = current_user.employers
#         return render_template("errors/404.html", title="OraJobs | Error: 404", user=user), 404
#     elif current_user.is_authenticated and current_user.applicants:
#         user = current_user.applicants
#         return render_template("errors/404.html", title="OraJobs | Error: 404", user=user), 404
#     else:
#         return render_template("errors/404.html", title="OraJobs | Error: 404"), 404



# @errors.app_errorhandler(405)
# def error_405(error):
#     if current_user.is_authenticated and current_user.employers:
#         user = current_user.employers
#         return render_template("errors/405.html", title="OraJobs | Error: 405",user=user), 405
#     elif current_user.is_authenticated and current_user.applicants:
#         user = current_user.applicants
#         return render_template("errors/405.html", title="OraJobs | Error: 405", user=user), 405
#     else:
#         return render_template("errors/405.html", title="OraJobs | Error: 405"), 405

# @errors.app_errorhandler(500)
# def error_500(error):
#     if current_user.is_authenticated and current_user.employers:
#         user = current_user.employers
#         return render_template("errors/500.html", title="OraJobs | Error: 500",user=user), 500
#     elif current_user.is_authenticated and current_user.applicants:
#         user = current_user.applicants
#         return render_template("errors/500.html", title="OraJobs | Error: 500",user=user), 500
#     else:
#         return render_template("errors/500.html", title="OraJobs | Error: 500"), 500




