import requests

from config import BACKEND_URL


def get_user(user_id, tg_username, affiliate=None):
    request_url = BACKEND_URL + 'clients/{}/'.format(user_id)
    body = {
        'user_id': user_id,
        'tg_username': tg_username,
        'affiliate': affiliate,
    }
    resp = requests.get(request_url, data=body)
    return resp.json()


def get_tasks(user_id):
    request_url = BACKEND_URL + 'tasks/'.format(user_id)
    body = {
        'user_id': user_id,
    }
    resp = requests.get(request_url, data=body)
    if not resp.ok:
        return []
    return resp.json()


def register_task(user_id, task_id):
    request_url = BACKEND_URL + 'tasks/{}/'.format(task_id)
    body = {
        'user_id': user_id,
    }
    resp = requests.get(request_url, data=body)
    return resp.ok


def send_proof_request(user_id, task_id, text_proof=None, image_proof=None):
    request_url = BACKEND_URL + 'proof/create/'
    body = {
        'client_id': user_id,
        'task_id': task_id,
        'text_answer': text_proof,
    }
    file = {'image_answer': ('test.jpg', image_proof, 'app/jpg', {'Content-Disposition': 'attachment'})}

    resp = requests.post(request_url, data=body, files=file)
    return resp.ok


def send_withdrawal_request(user_id, amount):
    request_url = BACKEND_URL + 'clients/withdrawal/'
    body = {
        'client': user_id,
        'withdrawal_sum': amount,
    }
    resp = requests.post(request_url, data=body)
    return resp.ok


def update_user(user_id, wallet_id, discord_username):
    request_url = BACKEND_URL + 'clients/{}/update/'.format(user_id)
    body = {

        'wallet': wallet_id,
        'discord_username': discord_username,
        'welcome_passed': True,
    }
    resp = requests.put(request_url, data=body)
    return resp.ok
