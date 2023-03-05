import asyncio
from functools import partial
from copy import deepcopy
from datetime import datetime
from time import sleep as blocking_sleep

from linkedin_api.linkedin import Linkedin, default_evade


class UnImplementedError(Exception):
    pass


class LinkedInExtented(Linkedin):

    loop = asyncio.get_event_loop()
    asyncronize = lambda self, func, *args: self.loop.run_in_executor(None, func, *args)


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

    async def get_jobs(self, company_details):

        resp = await self.asyncronize(
            partial(
                super().search_jobs,
                keywords=company_details['display_name'],
                companies=[company_details['internal_id']],
                remote=True, listed_at=24 * 60 * 60 * 1000
            )
        )

        return [
            {
                "job_id": i.get('*savingInfo', ":").split(':')[-1],
                "job_state": i.get('jobState'),
                "title": i.get('title'),
                "location": i.get('formattedLocation'),
                "listed_at": str(datetime.fromtimestamp(int(i.get('listedAt', 0)/1000))),
                "expire_at": str(datetime.fromtimestamp(int(i.get('expireAt', 0)/1000))),
                "company_id": company_details['internal_id']
            }
             for i in resp if i.get(
                'companyDetails', {}
            ).get('company', ':').split(':')[-1]==company_details['internal_id']
        ]

    async def get_company_posts(self, company_details):
        resp = await self.asyncronize(
            super().get_company_updates, company_details['internal_id']
        )
        render_api = 'com.linkedin.voyager.feed.render.UpdateV2'
        return [
            {
                "link": i['permalink'],
                "content": i['value'][render_api]['content'],
                "commentary": i['value'][render_api].get('commentary', ''),
                "company_id": company_details['internal_id']
            }
            for i in resp if 'content' in i['value'][render_api].keys()
        ]

    def _get_company_events(self, company_details, time_frame):
        params = {
            "decorationId": "com.linkedin.voyager.deco.organization.web.WebListedOrganizationEvent-6",
            "organizationIdOrUniversalName": company_details['universal_name'],
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
                "event_id": i.get('eventResolutionResult', {}).get('vanityName'),
                "state": i.get('eventResolutionResult', {}).get("lifecycleState"),
                "name": i.get('eventResolutionResult', {}).get('localizedName'),
                "description": i.get('eventResolutionResult', {}).get('localizedDescription', {}).get('text'),
                "display_time": i.get('eventResolutionResult', {}).get('displayEventTime', {}).get('text'),
                "attendee_count": i.get('attendeeCount'),
                "company_id": company_details['internal_id'],
            } for i in resp
        ]

    async def get_company_events(self, company_details):
        return {
            "UPCOMING": await self.asyncronize(
                self._get_company_events, company_details, "UPCOMING"
            ),
            "TODAY": await self.asyncronize(
                self._get_company_events, company_details, "TODAY"
            ),
            "PAST": await self.asyncronize(
                self._get_company_events, company_details, "PAST"
            ),
        }

    async def _get_employees(self, public_id_list):

        blocking_sleep(300)

        result = []

        for public_id in public_id_list:
            result.append({
                "public_id": public_id,
                **await self.asyncronize(self.get_profile, public_id),
                **await self.asyncronize(self.get_profile_contact_info, public_id),
                **await self.asyncronize(self.get_profile_network_info, public_id),
                "skills": [
                    i['name'] for i in await self.asyncronize(
                        self.get_profile_skills, public_id
                    )
                ],
            })

        return result


    async def get_employees_functions(self, company_details):

        resp = await self.asyncronize(
            partial(
                super().search_people,
                keyword_company=company_details['display_name'],
                current_company=[company_details['internal_id']]
            )
        )

        public_id_megalist = list(set([i['public_id'] for i in resp]))

        public_id_chunks = [
            public_id_megalist[i:i + 1] for i in range(0, len(public_id_megalist), 1)
        ]

        function_list = []

        for public_id_list in public_id_chunks:
            function_list.append(
                partial(self._get_employees, public_id_list=public_id_list)
            )
        return function_list


def get_li_creds():
    os.environ['LI_CURRENT_IDX'] = str((int(os.environ['LI_CURRENT_IDX']) + 1) % max(li_array_len , 1))
    return li_creds[int(os.environ['LI_CURRENT_IDX'])]


# python linkedin.py -n appsmith-au -j -p -e -E
if __name__ == "__main__":
    import os
    import sys
    import json

    import argparse
    from dotenv import load_dotenv


    load_dotenv()


    li_array_len, li_creds, os.environ['LI_CURRENT_IDX'] = int(os.getenv("LI_ARRAY_LEN", 0)), [], "0"

    if li_array_len:
        for i in range(0, li_array_len):
            li_temp_email, li_temp_pass = os.getenv(f"LI_EMAIL_{i}"), os.getenv(f"LI_PASS_{i}")
            if li_temp_email and li_temp_pass:
                li_creds.append({"username": li_temp_email, "password": li_temp_pass})
    else:
        li_creds.append({"username": os.getenv("LI_EMAIL"), "password": os.getenv("LI_PASS")})

    parser = argparse.ArgumentParser(prog="LinkedIn-CLI")

    parser.add_argument('-l', '--company_link', type=str, metavar='')
    parser.add_argument('-n', '--company_name', type=str, metavar='')
    parser.add_argument('-j', '--jobs', action='store_true',)
    parser.add_argument('-p', '--posts', action='store_true')
    parser.add_argument('-e', '--employees', action='store_true')
    parser.add_argument('-E', '--events', action='store_true')

    args = parser.parse_args()

    linked_in = LinkedInExtented(**get_li_creds(), refresh_cookies=False)

    company_details = linked_in.get_company(
        company_username=args.company_name, company_link=args.company_link
    )
    final_company_details = deepcopy(company_details)

    if args.jobs:
        final_company_details['jobs'] = linked_in.loop.run_until_complete(
            linked_in.get_jobs(company_details)
        )

    if args.posts:
        final_company_details['posts'] = linked_in.loop.run_until_complete(
            linked_in.get_company_posts(company_details)
        )

    if args.employees:
        final_company_details['employees'] = []

        func_list = linked_in.loop.run_until_complete(
            linked_in.get_employees_functions(company_details)
        )

        for func in func_list:
            final_company_details['employees'].append(
                linked_in.loop.run_until_complete(func())
            )

    if args.events:
        final_company_details['events'] = linked_in.loop.run_until_complete(
            linked_in.get_company_events(company_details)
        )

    sys.stdout.write(json.dumps(final_company_details))
