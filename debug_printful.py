#!/usr/bin/env python3
"""Debug Printful API response structure"""

import requests
import json

ACCESS_TOKEN = "YOUR_PRINTFUL_TOKEN"

headers = {
    'Authorization': f'Bearer {ACCESS_TOKEN}',
    'Content-Type': 'application/json'
}

# Test stores endpoint
print("Testing /v2/stores endpoint...")
response = requests.get('https://api.printful.com/v2/stores', headers=headers)
print(f"Status: {response.status_code}")
print(f"Response:")
print(json.dumps(response.json(), indent=2))
