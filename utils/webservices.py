import requests
import json


def authenticate_user(email: str, password: str) -> bool:
    url = 'https://realstate-bot-license-manager.herokuapp.com/verify_user'
    payload = {
        "email": email,
        "password": password
    }

    response = requests.post(url, json=payload)
    return json.loads(response.text)['verified']
