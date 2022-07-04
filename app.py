import os

from dotenv import load_dotenv
from flask import Flask, request

from linkedin import LinkedInExtented, get_all_details
from models import db


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


def create_app():

    # database config
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv(
        "DATABASE_URI", "postgresql://postgres:@localhost:5432/postgres"
    )

    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True
    db.init_app(app)
    app.app_context().push()
    db.create_all()

    # running Server
    app.run()


if __name__ == "__main__":
    create_app()
