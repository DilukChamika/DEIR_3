from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
import os
from os import path
from sqlalchemy import create_engine
from flask_mail import Mail
import secrets

dir = 'OraApp'
bcrypt = Bcrypt()
db = SQLAlchemy()
login_manager = LoginManager()
mail = Mail()

db_name = 'deir_2' #'jobsdb'
db_user = 'root'
db_pwd = ''
# secret_key = os.environ.get('SECRET_KEY')
secret_key = secrets.token_hex(24)
# xmp_soc = '?unix_socket=/opt/lampp/var/mysql/mysql.sock'
xmp_soc = ''


# Flask App function with initialized configurations
def create_app():
    app = Flask(__name__)

    app.config['SECRET_KEY'] = secret_key
    # sqlite db uri...app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{db_name}"
    app.config['SQLALCHEMY_DATABASE_URI'] = f"mysql+pymysql://{db_user}:@localhost:3306/{db_name}{xmp_soc}"



    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True
    app.config['MAIL_SERVER'] = 'smtp.gmail.com'
    app.config['MAIL_PORT'] = 587
    app.config['MAIL_USE_TLS'] = True
    app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USER')
    app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PWD')

    db.init_app(app)
    bcrypt.init_app(app)
    login_manager.init_app(app)
    mail.init_app(app)

    from .main.routes import main
    from .applicants.routes import applicant
    from .employers.routes import employer
    from .jobs.routes import jobs
    from .admin.routes import admin
    from .errors.handlers import errors

    app.register_blueprint(main)
    app.register_blueprint(applicant)
    app.register_blueprint(employer)
    app.register_blueprint(admin)
    app.register_blueprint(jobs)
    app.register_blueprint(errors)

    @app.template_filter()
    def numberFormat(value):
        return format(int(value), ',d') 
#comment
    # db.create_all(app=app)
    # create_db(app)

    return app
#comment
# creating sqlite database in app directory
# def create_db(app):
#     if not path.exists(f'{dir}/{db_name}'):
#         db.create_all(app=app)



