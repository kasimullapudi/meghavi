import requests
import json
response = requests.head("https://meghavi-kiosk-api.onrender.com/api/videos/download-all")
metadata = response.headers.get('X-zip-metadata')
total_size = json.loads(metadata).get('totalSize') if metadata else None
print(f"totalSize: {total_size}" if total_size else "Metadata header not found")
