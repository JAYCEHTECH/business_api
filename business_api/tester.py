import requests
import json

url = "https://plankton-app-s46li.ondigitalocean.app/generate_token"

payload = json.dumps({
  "username": "hello",
  "user_id": "13424",
  "full_name": "Mike Gyamfi",
  "email": "mike@mike.com"
})
headers = {
  'Content-Type': 'application/json'
}

response = requests.request("POST", url, headers=headers, data=payload)

print(response.text)
