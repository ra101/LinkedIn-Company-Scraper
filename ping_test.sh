curl --location --request POST 'http://127.0.0.1:5000/scrape' \
--header 'Content-Type: application/json' \
--data-raw '{
    "company_name": "appsmith",
    "employees": true,
    "events": true,
    "jobs": true,
    "posts": true
}'
