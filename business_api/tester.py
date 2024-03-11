import requests
import json

url = "https://merchant.cloudhubgh.com/api/initiate_ishare"

payload = json.dumps({
  "receiver": "0272266444",
  "data_volume": 50,
  "reference": "test123",
  "amount": "10"
})
headers = {
  'Content-Type': 'application/json',
  'Authorization': 'Bearer 0v2NKQiUI7nrzjnStHu2oZFpv9AWHB3SdAH',
  'Cookie': '__cf_bm=Bf8t2R8snbWLvEKIqdp0ZN_eRALZ.hA_kcTb7eF7ST0-1710142966-1.0.1.1-sJ6qz6fHDJ9iBKvqrG58ALS5_p8jbgQHN7PMqlXKYBR9FP2JA_K0AHxsIADbea2fCry97fwBoYhV4wBYkoMWow'
}

response = requests.request("POST", url, headers=headers, data=payload)

print(response.text)
