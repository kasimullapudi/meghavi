import requests

resp = requests.get("https://meghavi-kiosk-api.onrender.com/api/videos/get-all")
print("fetching complete")
data = resp.json()
print(data)