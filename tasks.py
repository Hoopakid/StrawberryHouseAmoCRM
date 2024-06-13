import os
import requests

from celery import Celery
from celery.schedules import crontab
from dotenv import load_dotenv
from datetime import datetime, timedelta

from utils import fetch_photo_and_save, fetch_xlsx_data_and_save

load_dotenv()

app = Celery(
    'tasks',
    broker='redis://redis_strawberry:6379',
    backend='redis://redis_strawberry:6379'
)

app.conf.beat_schedule = {
    'send_message': {
        'task': 'tasks.send_message_to_user',
        'schedule': crontab(hour=4, minute=0)
    }
}

BOT_TOKEN = os.environ.get('BOT_TOKEN')
MBI_CHAT_ID = os.environ.get('MBI_CHAT_ID')
SHER_CHAT_ID = os.environ.get('SHER_CHAT_ID')

chat_ids = [int(MBI_CHAT_ID), int(SHER_CHAT_ID)]


@app.task()
def send_message_to_user():
    url = f'https://api.telegram.org/bot{BOT_TOKEN}'
    fetch = fetch_xlsx_data_and_save()
    if fetch == True:
        yesterday = (datetime.now() - timedelta(days=361)).date()
        for chat_id in chat_ids:
            with open('calls.xlsx', 'rb') as photo:
                requests.post(url + '/sendDocument',
                              data={'chat_id': chat_id, 'caption': f"{yesterday} kungi sotuvlar ro'yhati"},
                              files={'document': photo})
        return True
    else:
        return False
