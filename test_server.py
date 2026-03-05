import requests
import time

try:
    print("Testing connection to http://127.0.0.1:10000")
    response = requests.get("http://127.0.0.1:10000", timeout=5)
    print(f"Status Code: {response.status_code}")
    print(f"Response Headers: {dict(response.headers)}")
    print("Server is responding!")
except requests.exceptions.ConnectionError as e:
    print(f"Connection Error: {e}")
except requests.exceptions.Timeout as e:
    print(f"Timeout Error: {e}")
except Exception as e:
    print(f"Other Error: {e}")