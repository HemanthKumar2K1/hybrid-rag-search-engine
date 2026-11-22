# Zoho SalesIQ integration notes

This covers the chat widget, the visitor JS API, the REST API and webhooks.

## Chat widget

The widget is a single script tag. It loads with `defer`, so it doesn't block the page.

### Plain HTML

Put this before `</body>`. You get the widget code from Settings > Website > Code.

```html
<script type="text/javascript">
var $zoho = $zoho || {};
$zoho.salesiq = $zoho.salesiq || {
  widgetcode: "YOUR_WIDGET_CODE",
  values: {},
  ready: function() {}
};

var d = document;
var s = d.createElement("script");
s.type = "text/javascript";
s.id = "zsiqscript";
s.defer = true;
s.src = "https://salesiq.zohopublic.com/widget";
var t = d.getElementsByTagName("script")[0];
t.parentNode.insertBefore(s, t);
</script>
```

### React / Next.js

Load the script in a `useEffect` in the root layout:

```jsx
import { useEffect } from "react";

export default function RootLayout({ children }) {
  useEffect(() => {
    window.$zoho = window.$zoho || {};
    window.$zoho.salesiq = {
      widgetcode: process.env.NEXT_PUBLIC_SALESIQ_WIDGET_CODE,
      values: {},
      ready: () => {},
    };

    const script = document.createElement("script");
    script.src = "https://salesiq.zohopublic.com/widget";
    script.defer = true;
    document.body.appendChild(script);

    return () => document.body.removeChild(script);
  }, []);

  return <html><body>{children}</body></html>;
}
```

## Visitor API

By default visitors are anonymous. Once you tell SalesIQ who the user is, operators see their details in the chat panel, and you can target campaigns at them.

### Identifying a logged-in user

After the user logs in, call `$zoho.salesiq.visitor.name()`, `.email()` and `.info()`. `info()` takes any key-value pairs, and operators see them next to the chat.

```javascript
function identifyVisitor(user) {
  $zoho.salesiq.visitor.name(user.displayName);
  $zoho.salesiq.visitor.email(user.email);
  $zoho.salesiq.visitor.info({
    "Plan": user.subscriptionPlan,
    "Company": user.company,
    "Account ID": user.accountId,
    "Days Active": user.daysActive,
  });
}
```

### Custom events

Events show up in the visitor's timeline:

```javascript
$zoho.salesiq.visitor.event("pricing_page_viewed", {
  plan: "Enterprise",
  duration: 45,
  source: "google_ads",
});

$zoho.salesiq.visitor.event("checkout_started", {
  cart_value: 1299.00,
  currency: "USD",
  items: 3,
});
```

### Single-page apps

In an SPA the widget doesn't reload when the route changes, so send the page info yourself:

```javascript
function trackPageView(pageTitle, pageUrl) {
  $zoho.salesiq.visitor.question(pageTitle);
  $zoho.salesiq.visitor.lastchat(pageUrl);
}
```

## Proactive chat triggers

Triggers open the chat or send a message without the visitor clicking anything.

### From JavaScript

This example opens a chat after 60 seconds on the pricing page:

```javascript
$zoho.salesiq.ready = function() {
  $zoho.salesiq.floatwindow.visible("show");

  setTimeout(function() {
    if (window.location.pathname === "/pricing") {
      $zoho.salesiq.chat.start();
      $zoho.salesiq.chat.send("Hi, need help picking a plan?");
    }
  }, 60000);
};
```

### From the dashboard

Under SalesIQ > Triggers you can set up rules without writing code:

| Condition | Action |
|---|---|
| URL contains `/pricing` | show chat after 30s |
| visit count >= 3 | open chat window |
| visitor from a given country | route to regional operator |
| cart value > $500 (custom variable) | send discount message |
| exit intent | show retention message |

## REST API

We use the REST API to pull chat history into the warehouse and to sync visitors to CRM.

### Auth

It uses the same Zoho OAuth tokens as CRM. Reads need the `SalesIQ.conversations.READ` scope, and writes need `SalesIQ.conversations.ALL`.

```python
import requests

SALESIQ_BASE = "https://salesiq.zohoapis.com/v2"
PORTAL_NAME = "your_portal_name"  # Settings > Portal

def salesiq_get(endpoint, access_token, params=None):
    response = requests.get(
        f"{SALESIQ_BASE}/{PORTAL_NAME}/{endpoint}",
        headers={"Authorization": f"Zoho-oauthtoken {access_token}"},
        params=params or {},
    )
    response.raise_for_status()
    return response.json()
```

### Chat history

`from_time` and `to_time` are unix timestamps in milliseconds.

```python
def get_recent_chats(access_token, from_time, to_time, page=1):
    return salesiq_get("chats", access_token, params={
        "from": from_time,
        "to": to_time,
        "type": "ended",
        "page": page,
        "limit": 100,
        "sortby": "created_time",
        "sortorder": "desc",
    })

def get_chat_transcript(access_token, chat_id):
    return salesiq_get(f"chats/{chat_id}/messages", access_token)
```

### Online operators

```python
def get_online_operators(access_token):
    return salesiq_get("operators", access_token, params={"status": "online"}).get("data", [])
```

## Webhooks

SalesIQ sends chat events to your server as they happen, so you don't need to poll the REST API.

### Events

You register the endpoint under Settings > Developer > Webhooks.

| Event | Fires when |
|---|---|
| `chat.started` | a visitor starts a chat |
| `chat.assigned` | an operator is assigned |
| `chat.message.received` | the visitor sends a message |
| `chat.ended` | the chat is closed by either side |
| `chat.rated` | the visitor submits a CSAT rating |
| `visitor.identified` | identified visitor data changes |

### Example payload (`chat.ended`)

```json
{
  "event": "chat.ended",
  "portal": "yourportalname",
  "data": {
    "chat_id": "cv_7890123456",
    "visitor": {"id": "vis_111222", "name": "Jane Doe", "email": "jane@acmecorp.com"},
    "operator": {"id": "op_445566", "name": "Arun K"},
    "duration": 312,
    "rating": 5,
    "started_time": 1749820800000,
    "ended_time": 1749821112000,
    "missed": false
  }
}
```

### Handler (FastAPI)

Check the `x-zoho-salesiq-signature` header before you trust the body.

```python
import hashlib
import hmac

from fastapi import FastAPI, HTTPException, Request

app = FastAPI()
WEBHOOK_SECRET = "your_salesiq_webhook_secret"

@app.post("/salesiq/webhook")
async def handle_salesiq_event(request: Request):
    body = await request.body()
    signature = request.headers.get("x-zoho-salesiq-signature", "")
    expected = hmac.new(WEBHOOK_SECRET.encode(), body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature):
        raise HTTPException(status_code=401, detail="bad signature")

    event = await request.json()
    if event["event"] == "chat.ended":
        sync_chat_to_crm(event["data"])
    elif event["event"] == "chat.rated":
        store_csat_score(event["data"])

    return {"status": "ok"}
```

## Syncing chats to CRM

SalesIQ has a built-in Zoho CRM integration. It can create or update CRM contacts from chat visitors.

### Dashboard settings

Under Settings > Integrations > Zoho CRM:
- Auto-create Contacts: creates a contact when an identified visitor starts a chat
- Chat History Sync: saves the transcript as a note on the contact
- Lead Conversion: optionally converts the contact to a lead at the `Qualification` stage

### Manual sync

This creates the contact if no contact has that email yet, and updates it otherwise.

```python
def sync_visitor_to_crm(access_token, visitor_id):
    response = requests.post(
        f"{SALESIQ_BASE}/{PORTAL_NAME}/visitors/{visitor_id}/crmsync",
        headers={"Authorization": f"Zoho-oauthtoken {access_token}"},
    )
    return response.json()
```

### Low CSAT follow-up

Once chats are synced, you can query CRM for unhappy customers:

```python
def get_low_csat_contacts(crm_access_token):
    query = """
        SELECT First_Name, Last_Name, Email, Phone
        FROM Contacts
        WHERE SalesIQ_CSAT_Score <= 3 AND SalesIQ_Last_Chat_Date >= '2026-01-01'
        ORDER BY SalesIQ_CSAT_Score ASC
        LIMIT 50
    """
    return search_with_coql(crm_access_token, query)
```
