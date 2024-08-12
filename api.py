import requests
import os
from dotenv import load_dotenv

load_dotenv()
access_token = os.getenv('access_token')
bot_id = int(os.getenv('bot_id'))
base_url = "https://api.pachca.com/api/shared/v1"
header = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }


def get_users(per=50, page=1, query=None):
    params = {
        "per": per,
        "page": page
    }
    if query:
        params["query"] = query

    response = requests.get(base_url + "/users", headers=header, params=params)
    if response.status_code == 200:
        return response.json().get('data', [])
    else:
        print(f"Failed to get users: {response.status_code}, {response.text}")
        return []


def get_all_users():
    all_users = []
    page = 1
    while True:
        users = get_users(page=page)
        if not users:
            break
        all_users.extend(users)
        page += 1
    return all_users


def get_user_id_by_nickname(nickname: str):
    page = 1
    while True:
        users = get_users(page=page, query=nickname)
        if not users:
            break
        for user in users:
            if user['nickname'] == nickname:
                return user
        page += 1
    return None


# A function to get a user information
def get_user_info(user_id: int):
    response = requests.get(base_url + f"/users/{user_id}", headers=header)
    if response.status_code == 200:
        user_data = response.json().get('data', [])
        return user_data
    else:
        print(f"Failed to get user information: {response.status_code}, {response.text}")
        return []


def get_all_chats():
    all_chats = []
    page = 1
    per_page = 50

    while True:
        params = {
            "per": per_page,
            "page": page
        }
        response = requests.get(base_url + "/chats", headers=header, params=params)
        if response.status_code == 200:
            chats_data = response.json().get('data', [])
            if not chats_data:
                break
            all_chats.extend(chats_data)
            page += 1
        else:
            print(f"Failed to get chats: {response.status_code}, {response.text}")
            break

    return all_chats


# A function for getting info of chat
def get_chat_info(chat_id: int):
    response = requests.get(base_url + f"/chats/{chat_id}", headers=header)
    if response.status_code == 200:
        chat_data = response.json().get('data', [])
        return chat_data
    else:
        print(f"Failed to get chat information: {response.status_code}, {response.text}")
        return []


# A function for getting an array of IDs of users participating in a conversation or channel
def get_chat_members(chat_id: int):
    response = requests.get(base_url + f"/chats/{chat_id}", headers=header)
    if response.status_code == 200:
        chat_data = response.json()
        member_ids = chat_data.get('member_ids', [])
        return member_ids
    else:
        print(f"Failed to get chat members information: {response.status_code}, {response.text}")
        return []


# A function to send message
def send_message(entity_type: str, entity_id: int, text: str):
    params = {
        "message": {
            "entity_type": entity_type,
            "entity_id": entity_id,
            "content": text
        }
    }

    response = requests.post(base_url + "/messages", json=params, headers=header)
    if response.status_code == 201:
        message_data = response.json().get('data', [])
        return message_data

    else:
        print(f"Failed to send message: {response.status_code}, {response.text}")
        return []


# A function to get list of messages
def get_list_of_messages(chat_id: int):
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    params = {
        "chat_id": chat_id
    }

    response = requests.get(base_url + "/messages", json=params, headers=headers)
    if response.status_code == 200:
        message_data = response.json().get('data', [])
        return message_data
    else:
        print(f"Failed to get messages of chat: {response.status_code}, {response.text}")
        return []


# A function to get thread responses
def get_thread_responses(message_id: int):
    response = requests.get(base_url + f"/messages/{message_id}", headers=header)
    if response.status_code == 200:
        threads_data = response.json().get('data', [])
        if threads_data['thread'] is not None:
            answer = get_list_of_messages(threads_data['thread']['chat_id'])
            return answer[0]['content']
        else:
            return None
    else:
        print(f"Failed to get thread responses: {response.status_code}, {response.text}")
        return []
