import os
import requests
from pprint import pprint
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

load_dotenv()

STRAWBERRY_URL = os.environ.get('STRAWBERRY_URL')
STRAWBERRY_TOKEN = os.environ.get('STRAWBERRY_TOKEN')


def prepare_params(params, prev=""):
    ret = ""
    if isinstance(params, dict):
        for key, value in params.items():
            if isinstance(value, dict):
                if prev:
                    key = "{0}[{1}]".format(prev, key)
                ret += prepare_params(value, key)
            elif (isinstance(value, list) or isinstance(value, tuple)) and len(
                    value
            ) > 0:
                for offset, val in enumerate(value):
                    if isinstance(val, dict):
                        ret += prepare_params(
                            val, "{0}[{1}][{2}]".format(prev, key, offset)
                        )
                    else:
                        if prev:
                            ret += "{0}[{1}][{2}]={3}&".format(prev, key, offset, val)
                        else:
                            ret += "{0}[{1}]={2}&".format(key, offset, val)
            else:
                if prev:
                    ret += "{0}[{1}]={2}&".format(prev, key, value)
                else:
                    ret += "{0}={1}&".format(key, value)
    return ret


def get_amocrm_notes(url, token, params={}, select=[], grouped=True):
    header = {'Authorization': f"Bearer {token}"}
    resp = requests.get(url + 'leads/notes', headers=header, params=prepare_params(params))
    if resp.status_code == 401:
        return {'unauthorized': True}
    elif resp.status_code == 204:
        if grouped:
            return dict()
        return []
    r = resp.json()['_embedded']['notes']

    while resp.json()['_links'].get('next', False):
        resp = requests.get(resp.json()['_links']['next']['href'], headers=header)
        r.extend(resp.json()['_embedded']['notes'])

    if not select and not grouped:
        return r
    if select:
        r = [{key: val for key, val in i.items() if key in select} for i in r]

    if grouped:
        grouped_data = {}
        for i in r:
            if i['entity_id'] not in grouped_data:
                grouped_data[i['entity_id']] = []
            grouped_data[i['entity_id']].append(1)
        return grouped_data

    return r


def get_amocrm_staff(token, url, select=[]):
    header = {'Authorization': f"Bearer {token}"}
    resp = requests.get(url + 'users', headers=header)
    if resp.status_code == 401:
        return {'unauthorized': True}
    r = resp.json()['_embedded']['users']

    while resp.json()['_links'].get('next', False):
        resp = requests.get(resp.json()['_links']['next']['href'], headers=header)
        r.extend(resp.json()['_embedded']['users'])
    if not select:
        return r

    r = [{key: val for key, val in i.items() if key in select} for i in r]
    return r


def get_lead_by_id(lead_id: int):
    url = f'{STRAWBERRY_URL}leads/{lead_id}'
    header = {'Authorization': f"Bearer {STRAWBERRY_TOKEN}"}
    resp = requests.get(url, headers=header)
    lead = resp.json()
    return lead['price'] if lead['price'] else 0


def get_amocrm_calls(url, token, start_date, end_date):
    date_filter = {
        'from': datetime.strptime(start_date, '%Y-%m-%d').timestamp(),
        'to': datetime.strptime(end_date, '%Y-%m-%d').timestamp()
    }
    calls = get_amocrm_notes(url, token,
                             params={'filter': {'updated_at': date_filter, 'note_type': ['call_in', 'call_out']}},
                             grouped=False)
    if isinstance(calls, dict) and calls.get('unauthorized'):
        return {'unauthorized': True}
    users = get_amocrm_staff(token, url)

    grouped = {}
    for i in calls:
        i['diff'] = i['params']['duration']
        dt = datetime.fromtimestamp(i['created_at'], timezone.utc)
        i['created_at'] = dt.astimezone()
        for u in users:
            if i['responsible_user_id'] == u['id']:
                i['responsible_user'] = u['name']

                if i['responsible_user'] not in grouped:
                    grouped[i['responsible_user']] = []
                grouped[i['responsible_user']].append(i)

    return grouped


def sorted_datas():
    start_date = (datetime.now() - timedelta(days=2)).strftime('%Y-%m-%d')
    end_date = datetime.now().strftime('%Y-%m-%d')
    url = STRAWBERRY_URL
    token = STRAWBERRY_TOKEN
    calls = get_amocrm_calls(url, token, start_date, end_date)
    temp_data = []
    for name, data in calls.items():
        all_duration, call_in, call_out, balance, yes, no = 0, 0, 0, 0, 0, 0
        balance_count = 0
        for i in data:
            yes += 1 if i['diff'] > 0 else 0
            no += 1 if i['diff'] == 0 else 0
            balance_lead = get_lead_by_id(i['entity_id'])
            balance += balance_lead
            if balance_lead != 0:
                balance_count += 1
            all_duration += i['diff']
        conversion = 0
        if balance_count != 0 and yes != 0:
            conversion = round((balance_count * 100) / yes, 2)
        plan = 100 - (yes + no) if 100 >= yes + no else 0

        temp_data.append({
            'name': name,
            'all_calls': yes + no,
            'all_duration': all_duration,
            'conversion': conversion,
            'success': yes,
            'no_success': no,
            'plan': plan,
            'balance': balance,
            'balance_count': balance_count
        })
    return temp_data

