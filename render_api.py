import urllib.request
import json

API_KEY = "rnd_9JWyPl0FwNKVCBnndIf95egtYdZc"

# Step 1: List services and find correct ID
req = urllib.request.Request(
    "https://api.render.com/v1/services",
    headers={"Authorization": f"Bearer {API_KEY}", "Accept": "application/json"}
)
with urllib.request.urlopen(req) as r:
    data = json.loads(r.read().decode())

service_id = None
for item in data:
    s = item.get("service", {})
    if s.get("name") == "insta-watermark-bot":
        service_id = s.get("id")
        print(f"Found service: {s.get('name')} | ID: {service_id}")
        break

if not service_id:
    print("Service not found!")
    exit(1)

# Step 2: Set environment variables
env_vars = [
    {"key": "BOT_TOKEN", "value": "8607432390:AAFCXj4h9XQ_VYQ2_7CCpNyg0IEP4ZR612k"}
]
payload = json.dumps(env_vars).encode()
req2 = urllib.request.Request(
    f"https://api.render.com/v1/services/{service_id}/env-vars",
    data=payload,
    method="PUT",
    headers={
        "Authorization": f"Bearer {API_KEY}",
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
)
try:
    with urllib.request.urlopen(req2) as r:
        resp = json.loads(r.read().decode())
        print("Env vars set successfully:", resp)
except Exception as e:
    print("Error setting env vars:", e)

# Step 3: Trigger manual deploy
req3 = urllib.request.Request(
    f"https://api.render.com/v1/services/{service_id}/deploys",
    data=b"{}",
    method="POST",
    headers={
        "Authorization": f"Bearer {API_KEY}",
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
)
try:
    with urllib.request.urlopen(req3) as r:
        deploy = json.loads(r.read().decode())
        print("Deploy triggered! Deploy ID:", deploy.get("id"), "Status:", deploy.get("status"))
except Exception as e:
    print("Error triggering deploy:", e)
