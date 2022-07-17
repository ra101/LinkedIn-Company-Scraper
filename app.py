import os

from celery import Celery
from dotenv import load_dotenv
from flask import Flask, request
from flask_migrate import Migrate
from sqlalchemy.inspection import inspect

import models
from models import db
from linkedin import LinkedInExtented


load_dotenv()


app = Flask("linkedin_company_scrapper")


with app.app_context():
    app.config.update(
        SQLALCHEMY_TRACK_MODIFICATIONS=True,
        SQLALCHEMY_DATABASE_URI=os.getenv(
            "DATABASE_URI", "postgresql://postgres:@localhost:5432/postgres"
        ),
        CELERY_BROKER_URL=os.getenv("CELERY_BROKER_URL", "redis://localhost:6379"),
        CELERY_RESULT_BACKEND=os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379"),
    )
    db.init_app(app)
    migrate = Migrate(app, db)

    celery = Celery(
        app.name,
        broker_url=app.config["CELERY_BROKER_URL"],
        result_backend=app.config["CELERY_RESULT_BACKEND"]
    )

    celery.conf.update(app.config)


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


def bulk_upsert(raw_data: list, model_cls: db.Model):
    primary_key = inspect(model_cls).primary_key[0].name
    columns = [column.name for column in inspect(model_cls).c]
    model_ints = {
        str(data[primary_key]): model_cls(**{c: data.get(c) for c in columns}) for data in raw_data
    }

    query_for_existing_rows = model_cls.query.filter(
        getattr(model_cls, primary_key).in_(model_ints.keys())
    ).all()

    # update previous records
    for instance in query_for_existing_rows:
        db.session.merge(model_ints.pop(str(getattr(instance, primary_key))))

    # create new records
    db.session.add_all(model_ints.values())

    db.session.commit()

    return model_ints


@celery.task(autoretry_for=(Exception,), retry_kwargs={'max_retries': 3, 'countdown': 300})
def scrape_and_save(company_details, jobs=False, posts=False, employees=False, events=False):
    linked_in = LinkedInExtented(linkedin_email, linkedin_password)

    app.app_context().push()

    if jobs:
        jobs_details = linked_in.loop.run_until_complete(
            linked_in.get_jobs(company_details)
        )
        if jobs_details:
            try:
                bulk_upsert(jobs_details, models.JobDetails)
            except:
                db.session.rollback()

    if posts:
        post_details = linked_in.loop.run_until_complete(
            linked_in.get_company_posts(company_details)
        )
        if post_details:
            try:
                bulk_upsert(post_details, models.PostDetails)
            except:
                db.session.rollback()

    if events:
        event_details = linked_in.loop.run_until_complete(
            linked_in.get_company_events(company_details)
        )
        if any(event_details.values()):
            try:
                bulk_upsert(
                    event_details['UPCOMING'] + event_details['TODAY']
                    + event_details['PAST'], models.EventDetails
                )
            except:
                db.session.rollback()

    if employees:
        employee_details = linked_in.loop.run_until_complete(
            linked_in.get_employees(company_details)
        )
        if employee_details:
            try:
                employee_ints = bulk_upsert(employee_details, models.EmployeeDetails)

                if employee_ints:
                    company_instance = db.session.query(
                        models.CompanyBaseDetails
                    ).get(company_details['internal_id'])

                    company_instance.employees.extend(employee_ints.values())
                    db.session.commit()
            except:
                db.session.rollback()


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
        return ({"error": "unable to login, check credentials in .env"}, 500)


    try:
        company_details = linked_in.get_company(
            company_username=company_name,
            company_link=company_link
        )
    except Exception:
        return ({"error": "Invalid Company Name or Link"}, 400)


    try:
        bulk_upsert([company_details], models.CompanyBaseDetails)
    except Exception:
        return ({"error": "unable to do database operations"}, 500)


    if any(response.values()):
        scrape_and_save.delay(company_details, **response)

    if company_name:
        response["company_name"] = company_name

    if company_link:
        response["company_link"] = company_link

    return response


if __name__ == "__main__":
    app.run()
