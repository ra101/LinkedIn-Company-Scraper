import os
from copy import deepcopy

from dotenv import load_dotenv
from flask import Flask, request
from flask_migrate import Migrate

try:
    from .celery_queue import celery
    from .linkedin import LinkedInExtented
    from .models import db, CompanyBaseDetails
except:
    from celery_queue import celery
    from linkedin import LinkedInExtented
    from models import db, CompanyBaseDetails

load_dotenv()


app = Flask("linkedin_company_scrapper")
linkedin_email = os.getenv("LI_EMAIL")
linkedin_password = os.getenv("LI_PASSWORD")


@app.route("/")
def hello_world():
    return "Hello World"


@app.route("/schema")
def schema():
    return {
        "company_name": "<str: company_name>",
        "company_link": "<str: company_link>",
        "jobs": "<bool: get_jobs? | default: False>",
        "posts": "<bool: get_company_posts? | default: False>",
        "employees": "<bool: get_employees? | default: False>",
        "events": "<bool: get_company_events? | default: False>",
    }


@app.route("/scrape", methods=["POST"])
def scrape():
    body = request.json
    response = {
        "jobs": body.get('jobs', False),
        "posts": body.get('posts', False),
        "employees": body.get('employees', False),
        "events": body.get('events', False)
    }

    company_name, company_link = body.get('company_name'), body.get('company_link')
    if not any([company_name, company_link]):
        return ({"error": "Provide atleast `company_name` or `company_link`"}, 400)

    try:
        linked_in = LinkedInExtented(linkedin_email, linkedin_password)
    except Exception:
        return ({"error": "enable to login, check credentials in .env"}, 500)


    try:
        company_details = linked_in.get_company(
            company_username=company_name,
            company_link=company_link
        )
    except Exception:
        return ({"error": "Invalid Company Name or Link"}, 400)


    get_all_details.delay(linkedin_email, linkedin_password, company_details, **response)

    if company_name:
        response["company_name"] = company_name

    if company_link:
        response["company_link"] = company_link

    return response


@celery.task(autoretry_for=(Exception,), retry_kwargs={'max_retries': 3, 'countdown': 300})
def scrape_and_save(company_details, jobs=False, posts=False, employees=False, events=False):
    linked_in = LinkedInExtented(linkedin_email, linkedin_password)

    # company_instance = db.session.query(CompanyBaseDetails).get(company_details['internal_id'])

    final_company_details = deepcopy(company_details)

    if jobs:
        final_company_details['jobs'] = linked_in.loop.run_until_complete(
            linked_in.get_jobs(company_details)
        )

    if posts:
        final_company_details['posts'] = linked_in.loop.run_until_complete(
            linked_in.get_company_posts(company_details)
        )

    if employees:
        final_company_details['employees'] = linked_in.loop.run_until_complete(
            linked_in.get_employees(company_details)
        )

    if events:
        final_company_details['events'] = linked_in.loop.run_until_complete(
            linked_in.get_company_events(company_details)
        )


def create_app():

    # database config
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv(
        "DATABASE_URI", "postgresql://postgres:@localhost:5432/postgres"
    )
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True

    db.init_app(app)
    migrate = Migrate(app, db)
    app.app_context().push()

    # running Server
    app.run()


if __name__ == "__main__":
    create_app()
