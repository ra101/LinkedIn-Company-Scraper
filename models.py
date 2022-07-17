from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


employment_record = db.Table(
    'linkedin_employment_records',
    db.Column('company_id', db.BigInteger(), db.ForeignKey('linkedin_companies_base_details.internal_id')),
    db.Column('employee_id' ,db.Text(), db.ForeignKey('linkedin_employees_details.public_id')),
)


class CompanyBaseDetails(db.Model):
    __tablename__ = "linkedin_companies_base_details"

    internal_id = db.Column(db.BigInteger(), primary_key=True)
    link = db.Column(db.Text())
    website = db.Column(db.Text())
    address = db.Column(db.JSON())
    display_name = db.Column(db.Text())
    universal_name = db.Column(db.Text())
    employee_count = db.Column(db.JSON())
    specialities = db.Column(db.ARRAY(db.Text()))
    followers_count = db.Column(db.BigInteger())
    tagline = db.Column(db.Text())
    description = db.Column(db.Text())
    founded_on = db.Column(db.Integer())
    industry = db.Column(db.ARRAY(db.Text()))

    jobs = db.relationship('JobDetails', backref='company')
    events = db.relationship('EventDetails', backref='company')
    posts = db.relationship('PostDetails', backref='company')
    employees = db.relationship('EmployeeDetails', secondary=employment_record, backref='companies')

    def __repr__(self):
        return f"CompanyBaseDetails <{self.universal_name}>"


class JobDetails(db.Model):
    __tablename__ = "linkedin_jobs_details"

    job_id = db.Column(db.BigInteger(), primary_key=True)
    job_state = db.Column(db.Text())
    title = db.Column(db.Text())
    location = db.Column(db.Text())
    listed_at = db.Column(db.DateTime())
    expire_at = db.Column(db.DateTime())

    company_id = db.Column(
        db.BigInteger(), db.ForeignKey('linkedin_companies_base_details.internal_id')
    )

    def __repr__(self):
        return f"JobDetails <{self.company.universal_name}: {self.title}>"


class EventDetails(db.Model):
    __tablename__ = "linkedin_events_details"

    event_id = db.Column(db.Text(), primary_key=True)
    state = db.Column(db.Text())
    name = db.Column(db.Text())
    description = db.Column(db.Text())
    display_time = db.Column(db.DateTime())
    attendee_count = db.Column(db.BigInteger())

    company_id = db.Column(
        db.BigInteger(), db.ForeignKey('linkedin_companies_base_details.internal_id')
    )

    def __repr__(self):
        return f"EventDetails <{self.company.universal_name}: {self.name}>"


class PostDetails(db.Model):
    __tablename__ = "linkedin_posts_details"

    link = db.Column(db.Text(), primary_key=True)
    content = db.Column(db.JSON())
    commentary = db.Column(db.JSON())

    company_id = db.Column(
        db.BigInteger(), db.ForeignKey('linkedin_companies_base_details.internal_id')
    )

    def __repr__(self):
        return f"PostDetails <{self.company.universal_name}: {self.link}>"


class EmployeeDetails(db.Model):
    __tablename__ = "linkedin_employees_details"

    public_id = db.Column(db.Text(), primary_key=True)
    firstName = db.Column(db.Text())
    lastName = db.Column(db.Text())
    headline = db.Column(db.Text())
    summary = db.Column(db.Text())
    industryName = db.Column(db.Text())
    locationName = db.Column(db.Text())
    student = db.Column(db.Boolean())
    geoCountryName = db.Column(db.Text())
    geoLocationName = db.Column(db.Text())
    experience = db.Column(db.ARRAY(db.JSON()))
    education = db.Column(db.ARRAY(db.JSON()))
    languages = db.Column(db.ARRAY(db.JSON()))
    publications = db.Column(db.ARRAY(db.JSON()))
    certifications = db.Column(db.ARRAY(db.JSON()))
    volunteer = db.Column(db.ARRAY(db.JSON()))
    honors = db.Column(db.ARRAY(db.JSON()))
    email_address = db.Column(db.Text())
    websites = db.Column(db.ARRAY(db.JSON()))
    twitter = db.Column(db.ARRAY(db.JSON()))
    birthdate = db.Column(db.DateTime())
    phone_numbers = db.Column(db.ARRAY(db.JSON()))
    followable = db.Column(db.Boolean())
    followersCount = db.Column(db.BigInteger())
    connectionsCount = db.Column(db.BigInteger())
    skills = db.Column(db.ARRAY(db.Text()))

    def __repr__(self):
        return f"EmployeeDetails <{self.firstName} {self.lastName}>"
