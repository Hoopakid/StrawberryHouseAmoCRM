import os
import requests
from dotenv import load_dotenv

load_dotenv()

HOST_URL = os.environ.get('HOST_URL')


def fetch_photo_and_save():
    url = f'{HOST_URL}/scrapped-photo'
    response = requests.get(url)

    if response.status_code == 200:
        with open('calls.png', 'wb') as file:
            file.write(response.content)
    else:
        return False
    return True
