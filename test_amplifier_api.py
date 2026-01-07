#!/usr/bin/env python3
"""
Test script to discover Amplifier API endpoints and document them
"""

import requests
import json

API_KEY = "YOUR_AMPLIFIER_API_KEY"

# Common base URLs for APIs
possible_bases = [
    "https://api.amplifier.com",
    "https://amplifier.com/api",
    "https://api.getamplifier.com",
    "https://app.amplifier.com/api"
]

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

# Also try with API key in different formats
alt_headers = [
    {"X-API-Key": API_KEY, "Content-Type": "application/json"},
    {"api-key": API_KEY, "Content-Type": "application/json"},
]

print("=" * 70)
print("AMPLIFIER API DISCOVERY")
print("=" * 70)
print()

# Try to discover the base URL
for base_url in possible_bases:
    print(f"Testing base URL: {base_url}")

    # Try common endpoints
    test_endpoints = [
        "/",
        "/v1",
        "/api",
        "/status",
        "/health"
    ]

    for endpoint in test_endpoints:
        url = base_url + endpoint

        # Try with Bearer token
        try:
            response = requests.get(url, headers=headers, timeout=5)
            if response.status_code != 404:
                print(f"  ✓ {url} - Status: {response.status_code}")
                print(f"    Response: {response.text[:200]}")
                print()
        except Exception as e:
            pass

        # Try with alternate headers
        for alt_header in alt_headers:
            try:
                response = requests.get(url, headers=alt_header, timeout=5)
                if response.status_code != 404:
                    print(f"  ✓ {url} (alt header) - Status: {response.status_code}")
                    print(f"    Response: {response.text[:200]}")
                    print()
            except Exception as e:
                pass

    print()

print("\nNote: If no endpoints were discovered, the API might use a different")
print("base URL or authentication method. Please check the Amplifier dashboard")
print("or support documentation for the correct API base URL.")
