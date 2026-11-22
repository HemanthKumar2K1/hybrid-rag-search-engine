# Zoho CRM REST API v7 notes

Base URL: `https://www.zohoapis.com/crm/v7`

## Authentication

All requests use OAuth 2.0. Send the token in the header as `Authorization: Zoho-oauthtoken <access_token>`.

### Registering the app

Create a Server-based Application in the API console (api-console.zoho.com). That gives you the `client_id` and `client_secret`.

### Getting tokens

Exchange the authorization code for an access token and a refresh token:

```python
import requests

response = requests.post(
    "https://accounts.zoho.com/oauth/v2/token",
    data={
        "grant_type": "authorization_code",
        "client_id": "YOUR_CLIENT_ID",
        "client_secret": "YOUR_CLIENT_SECRET",
        "redirect_uri": "YOUR_REDIRECT_URI",
        "code": "AUTHORIZATION_CODE",
    },
)
tokens = response.json()
access_token = tokens["access_token"]    # valid for 1 hour
refresh_token = tokens["refresh_token"]  # doesn't expire, keep it safe
```

### Refreshing an expired access token

Access tokens expire after 3600 seconds. To get a new one, POST the refresh token to the same token endpoint with `grant_type=refresh_token`. The user doesn't have to log in again.

```python
def refresh_access_token(client_id, client_secret, refresh_token):
    response = requests.post(
        "https://accounts.zoho.com/oauth/v2/token",
        data={
            "grant_type": "refresh_token",
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
        },
    )
    return response.json()["access_token"]
```

### Scopes

| Scope | Access |
|---|---|
| `ZohoCRM.modules.ALL` | read/write records in all modules |
| `ZohoCRM.modules.READ` | read-only access to modules |
| `ZohoCRM.settings.ALL` | read/write settings and fields |
| `ZohoCRM.users.READ` | read users and roles |
| `ZohoCRM.bulk.ALL` | bulk read/write |

## Modules: Leads, Contacts, Deals, Accounts

CRM data lives in modules. The ones we use most are Leads, Contacts, Deals (called Potentials in older APIs) and Accounts.

### Listing records

Results are paginated, with at most 200 per page.

```python
def get_records(module_name, access_token, page=1, per_page=200):
    response = requests.get(
        f"https://www.zohoapis.com/crm/v7/{module_name}",
        headers={"Authorization": f"Zoho-oauthtoken {access_token}"},
        params={"page": page, "per_page": per_page},
    )
    return response.json().get("data", [])
```

### Creating a lead

```python
def create_lead(access_token, first_name, last_name, email, company):
    response = requests.post(
        "https://www.zohoapis.com/crm/v7/Leads",
        headers={"Authorization": f"Zoho-oauthtoken {access_token}"},
        json={"data": [{
            "First_Name": first_name,
            "Last_Name": last_name,
            "Email": email,
            "Company": company,
        }]},
    )
    return response.json()["data"][0]  # {"code": "SUCCESS", "details": {...}}
```

### Updating a record

PUT to `/crm/v7/{module}/{record_id}` with just the fields you want to change. Fields you leave out are left as they are.

```python
def update_deal_stage(access_token, deal_id, new_stage):
    response = requests.put(
        f"https://www.zohoapis.com/crm/v7/Deals/{deal_id}",
        headers={"Authorization": f"Zoho-oauthtoken {access_token}"},
        json={"data": [{"Stage": new_stage}]},
    )
    return response.json()
```

### Deleting a record

```python
def delete_record(access_token, module_name, record_id):
    response = requests.delete(
        f"https://www.zohoapis.com/crm/v7/{module_name}/{record_id}",
        headers={"Authorization": f"Zoho-oauthtoken {access_token}"},
    )
    return response.status_code == 200
```

## COQL queries

COQL is Zoho's SQL-like query language. It's handy when listing a whole module is too much and you only need records that match a filter.

```python
def search_with_coql(access_token, query):
    response = requests.post(
        "https://www.zohoapis.com/crm/v7/coql",
        headers={"Authorization": f"Zoho-oauthtoken {access_token}"},
        json={"select_query": query},
    )
    return response.json().get("data", [])
```

Some examples:

```sql
-- new leads from the tech industry
SELECT First_Name, Last_Name, Email, Phone
FROM Leads
WHERE Lead_Status = 'New' AND Industry = 'Technology'
ORDER BY Created_Time DESC
LIMIT 50 OFFSET 0

-- deals closing this quarter above 50000
SELECT Deal_Name, Stage, Amount, Closing_Date
FROM Deals
WHERE Closing_Date >= '2026-04-01' AND Amount > 50000
ORDER BY Amount DESC
```

Limitations:
- A query returns at most 200 records. Use `OFFSET` to page through the rest.
- No JOINs across modules. Fetch related records separately with the related records API.
- `COUNT` and `SUM` work, but you can't select normal fields in the same query.

## Webhooks

Webhooks let CRM call your server when a record changes, so you don't have to poll.

### Registering a webhook

You can register one in Settings > Developer Space > Notifications, or through the API:

```python
def create_webhook(access_token, notify_url, channel_id, events):
    # events look like ["Leads.create", "Deals.edit", "Contacts.delete"]
    response = requests.post(
        "https://www.zohoapis.com/crm/v7/actions/watch",
        headers={"Authorization": f"Zoho-oauthtoken {access_token}"},
        json={"watch": [{
            "channel_id": str(channel_id),
            "events": events,
            "notify_url": notify_url,
            "channel_expiry": "2026-12-31T00:00:00+05:30",
        }]},
    )
    return response.json()
```

### Payload

When a lead is created, CRM POSTs this to `notify_url`:

```json
{
  "query_params": {"channel_id": "1001", "module": "Leads", "operation": "create"},
  "ids": ["4876533000001234001"],
  "affected_fields": {
    "4876533000001234001": ["First_Name", "Last_Name", "Email", "Company"]
  }
}
```

You only get the record ids and the names of the changed fields, not the values. Do a GET on the record if you need the data.

### Checking the signature

Each webhook comes with an `x-zoho-webhook-token` header. Compare it with your secret so you can reject fake requests:

```python
import hashlib
import hmac

def is_valid_webhook(payload_bytes, signature_header, secret_token):
    expected = hmac.new(secret_token.encode(), payload_bytes, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature_header)
```

## Bulk API

For migrations or big syncs, use the Bulk API instead of thousands of single-record calls. Jobs run asynchronously: you create a job, upload a CSV, then poll until it finishes.

```python
def bulk_write_leads(access_token, file_path):
    headers = {"Authorization": f"Zoho-oauthtoken {access_token}"}

    job = requests.post(
        "https://www.zohoapis.com/crm/bulk/v7/write",
        headers=headers,
        json={
            "operation": "upsert",
            "callback": {"url": "https://yourserver.com/zoho/bulk-complete", "method": "post"},
            "resource": [{"type": "data", "module": {"api_name": "Leads"}, "file_id": None}],
        },
    )
    job_id = job.json()["data"]["details"]["id"]

    with open(file_path, "rb") as f:
        requests.post(
            f"https://www.zohoapis.com/crm/bulk/v7/write/{job_id}/upload",
            headers=headers,
            files={"file": (file_path, f, "text/csv")},
        )
    return job_id
```

Checking the job status:

```python
def get_bulk_job_status(access_token, job_id):
    response = requests.get(
        f"https://www.zohoapis.com/crm/bulk/v7/write/{job_id}",
        headers={"Authorization": f"Zoho-oauthtoken {access_token}"},
    )
    details = response.json()["data"]["details"]
    # ADDED, IN PROGRESS, COMPLETED or FAILED
    return details["status"], details.get("result", {})
```

## Rate limits and errors

### Rate limits

| Plan | Requests per day | Requests per minute |
|---|---|---|
| Free | 5,000 | 100 |
| Standard | 25,000 | 250 |
| Professional | 100,000 | 500 |
| Enterprise | Unlimited | 500 |

If you go over the per-minute limit you get a `429 Too Many Requests` with a `Retry-After` header (in seconds).

### Error codes

| Code | HTTP | Meaning |
|---|---|---|
| `INVALID_TOKEN` | 401 | token expired or revoked, refresh it |
| `INVALID_MODULE` | 400 | wrong module name |
| `MANDATORY_NOT_FOUND` | 400 | a required field is missing |
| `DUPLICATE_DATA` | 400 | a record with the same unique field exists |
| `LIMIT_EXCEEDED` | 429 | rate limited |
| `INTERNAL_ERROR` | 500 | Zoho-side error, retry later |

### Retrying

Retry on 429 and 5xx, waiting longer after each failure:

```python
import time

def api_request_with_retry(func, max_retries=5):
    for attempt in range(max_retries):
        response = func()
        if response.status_code == 429:
            time.sleep(int(response.headers.get("Retry-After", 2 ** attempt)))
        elif response.status_code >= 500:
            time.sleep(2 ** attempt)
        else:
            return response
    raise RuntimeError("request failed after retries")
```
