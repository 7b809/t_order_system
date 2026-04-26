import requests

url = "http://13.232.54.10:8000/add"
data = {"a": 10, "b": 5}

print(requests.post(url, json=data).json())