from copy import deepcopy

from linkedin_api.linkedin import Linkedin, default_evade

from celery_queue import celery


class UnImplementedError(Exception):
    pass


class LinkedInExtented(Linkedin):

    def _fetch(self, uri, evade=default_evade, base_request=False, headers={}, **kwargs):
        """
        override this command to add auth.
        """

        headers = headers or kwargs.get("headers", {})
        headers.update({
            'csrf-token': self.client.session.cookies.get_dict().get('JSESSIONID').replace('"','')
        })
        kwargs.update({"headers": headers})

        return super()._fetch(uri, evade, base_request, **kwargs)

    def _post(self, *args, **kwargs):
        raise UnImplementedError()


    def get_company_username(self, company_link):
        try:
            company_username = company_link.split('.com/company/')[1].replace('/','')
        except:
            raise ValueError("Use company link like https://www.linkedin.com/company/unilever/ only!")
        return company_username


    def get_company(self, company_username=None, company_link=None):
        """
        Fetch data about a given LinkedIn company.

        :param company_username: LinkedIn public name for a company
        :type public_id: str

        :return: Company data
        :rtype: dict
        """

        if not any([company_username, company_link]):
            raise AttributeError("Provide atleast `company_username` or `company_link`")

        if not company_username:
            try:
                company_username = company_link.split('.com/company/')[1].replace('/','')
            except:
                raise AttributeError("Use company link like https://www.linkedin.com/company/unilever/ only!")

        params = {
            "decorationId": "com.linkedin.voyager.dash.deco.organization.MemberCompany-65",
            "q": "universalName",
            "universalName": company_username,
        }

        res = self._fetch(f"/voyagerOrganizationDashCompanies", params=params)

        if res.status_code != 200:
            self.logger.info(f"request failed: {res.status_code}")
            return {}


        try:
            resp = res.json()["elements"][0]
        except IndexError:
            raise ValueError("Incorrect `company_username`")

        return {
            "internal_id": resp.get('entityUrn', '').split(':')[-1],
            "link": resp.get('url'),
            "website": resp.get('websiteUrl'),
            "address": resp.get("headquarter", {}).get('address', {}),
            "display_name": resp.get("name"),
            "universal_name": resp.get('universalName'),
            "employee_count": resp.get('employeeCount'),
            "specialities": resp.get("specialities"),
            "followers_count": resp.get("followingState", {}).get("followerCount"),
            "tagline": resp.get("tagline"),
            "description": resp.get("description"),
            "founded_on": resp.get("foundedOn", {}).get('year'),
            "industry": [i['name'] for i in resp.get("industry", {}).values()],
        }

    def get_jobs(self, company_details):

        resp = super().search_jobs(
            keywords=company_details['display_name'],
            companies=[company_details['internal_id']],
            remote=True, listed_at=24 * 60 * 60 * 1000
        )

        return [
            {
                "job_id": i.get('*savingInfo', ":").split(':')[-1],
                "job_state": i.get('jobState'),
                "title": i.get('title'),
                "location": i.get('formattedLocation'),
                "listed_at": i.get('listedAt'),
                "expire_at": i.get('expireAt')
            }
             for i in resp if i.get(
                'companyDetails', {}
            ).get('company', ':').split(':')[-1]==company_details['internal_id']
        ]

    def get_company_posts(self, company_details):
        resp = super().get_company_updates(
            public_id=company_details['internal_id'],
            urn_id=None, max_results=None, results=[]
        )
        render_api = 'com.linkedin.voyager.feed.render.UpdateV2'
        return [
            {
                "link": i['permalink'],
                "meta": i['value'][render_api]['updateMetadata'],
                "content": i['value'][render_api]['content'],
                "commentary": i['value'][render_api].get('commentary', '')
            }
            for i in resp if 'content' in i['value'][render_api].keys()
        ]

    def _get_company_events(self, universal_name, time_frame):
        params = {
            "decorationId": "com.linkedin.voyager.deco.organization.web.WebListedOrganizationEvent-6",
            "organizationIdOrUniversalName": universal_name,
            "q": "timeFrame", "timeFrame": time_frame, "start": 0, "count": 100
        }

        res = self._fetch(f"/voyagerOrganizationOrganizationEvents", params=params)

        if res.status_code != 200:
            self.logger.info(f"request failed: {res.status_code}")
            return {}


        try:
            resp = res.json()["elements"]
        except IndexError:
            raise ValueError("Incorrect `company_username`")

        return [
            {
                "name": i.get('eventResolutionResult', {}).get('localizedName'),
                "description": i.get('eventResolutionResult', {}).get('localizedDescription'),
                "display_time": i.get('eventResolutionResult', {}).get('displayEventTime', {}).get('text'),
                "attendee_count": i.get('attendeeCount'),
            } for i in resp
        ]

    def get_company_events(self, company_details):
        universal_name = company_details['universal_name']
        return {
            "UPCOMING": self._get_company_events(universal_name, "UPCOMING"),
            "TODAY": self._get_company_events(universal_name, "TODAY"),
            "PAST": self._get_company_events(universal_name, "PAST"),
        }

    def get_employees(self, company_details):

        resp = super().search_people(
            keyword_company=company_details['display_name'],
            current_company=[company_details['internal_id']],
        )

        public_id_list = list(set([i['public_id'] for i in resp]))

        result = []

        for public_id in public_id_list:
            result.append({
                **self.get_profile(public_id),
                **self.get_profile_contact_info(public_id),
                **self.get_profile_network_info(public_id),
                "skills": [i['name'] for i in self.get_profile_skills(public_id)]
            })

        return result

@celery.task()
def get_all_details(linkedin_email, linkedin_password, company_details, jobs=False, posts=False, employees=False, events=False):

    linked_in = LinkedInExtented(linkedin_email, linkedin_password)
    final_company_details = deepcopy(company_details)

    if jobs:
        final_company_details['jobs'] = linked_in.get_jobs(company_details)

    if posts:
        final_company_details['posts'] = linked_in.get_company_posts(company_details)

    if employees:
        final_company_details['employees'] = linked_in.get_employees(company_details)

    if events:
        final_company_details['events'] = linked_in.get_company_events(company_details)


linkedin_email = "agarwal.parth.101@gmail.com" # place your linkedin login email
linkedin_password = "32432"


l = LinkedInExtented(linkedin_email, linkedin_password)
c = l.get_company("innovaccer")
# j = l.get_jobs(c)
# u = l.get_company_posts(c)
# p = l.get_employees(c)
e = l.get_company_events(c)
