import asyncio
import requests
import os
from dotenv import load_dotenv

load_dotenv()
access_token = os.getenv('access_token')
bot_id = int(os.getenv('bot_id'))
base_url = "https://api.pachca.com/api/shared/v1"


incapable_student = {}  # {user_id: status} sick rest
student_of_chat = {}  # {chat_id: [member1_id, member2_id]} reviewed students
heads_of_chat = {}  # {chat_id: [member1_id, member2_id]}
message_ids = {}  # {chat_id: {member_id: message_id}}
student_contacts = set()  # get welcome message to student
chat_contacts = set()  # get welcome message to chat
schedule_of_chats = {}  # {chat_id: [(day1, time1), (day2, time2)]}
time_limit_of_chats = {}  # {chat_id: limit}
paused_chats = []


def get_list_of_users():
    headers = {
        "Authorization": f"Bearer {access_token}"
    }

    response = requests.get(base_url + "/users", headers=headers)
    if response.status_code == 200:
        users_data = response.json().get('data', [])
        return users_data
    else:
        print(f"Failed to get users: {response.status_code}, {response.text}")
        return []


def get_users(per=50, page=1, query=None):
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    params = {
        "per": per,
        "page": page
    }
    if query:
        params["query"] = query

    response = requests.get(base_url + "/users", headers=headers, params=params)
    if response.status_code == 200:
        return response.json().get('data', [])
    else:
        print(f"Failed to get users: {response.status_code}, {response.text}")
        return []


def get_user_id_by_nickname(nickname):
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
def get_user_info(user_id):
    header = {
        "Authorization": f"Bearer {access_token}"
    }

    response = requests.get(base_url + f"/users/{user_id}", headers=header)
    if response.status_code == 200:
        user_data = response.json().get('data', [])
        return user_data
    else:
        print(f"Failed to get user information: {response.status_code}, {response.text}")
        return []


def get_all_chats():
    headers = {
        "Authorization": f"Bearer {access_token}"
    }

    all_chats = []
    page = 1
    per_page = 50

    while True:
        params = {
            "per": per_page,
            "page": page
        }
        response = requests.get(base_url + "/chats", headers=headers, params=params)
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
def get_chat_info(chat_id):
    header = {
        "Authorization": f"Bearer {access_token}"
    }

    response = requests.get(base_url + f"/chats/{chat_id}", headers=header)
    if response.status_code == 200:
        chat_data = response.json().get('data', [])
        return chat_data
    else:
        print(f"Failed to get chat information: {response.status_code}, {response.text}")
        return []


# A function for getting an array of IDs of users participating in a conversation or channel
def get_chat_members(chat_id):
    header = {
        "Authorization": f"Bearer {access_token}"
    }

    response = requests.get(base_url + f"/chats/{chat_id}", headers=header)
    if response.status_code == 200:
        chat_data = response.json()
        member_ids = chat_data.get('member_ids', [])
        return member_ids
    else:
        print(f"Failed to get chat members information: {response.status_code}, {response.text}")
        return []


# A function to send message
def send_message(entity_type, entity_id, text):
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    params = {
        "message": {
            "entity_type": entity_type,
            "entity_id": entity_id,
            "content": text
        }
    }

    response = requests.post(base_url + "/messages", json=params, headers=headers)
    if response.status_code == 201:
        message_data = response.json().get('data', [])
        return message_data

    else:
        print(f"Failed to send message to student: {response.status_code}, {response.text}")
        return []


# A function to get list of messages
def get_list_of_messages(chat_id):
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
def get_thread_responses(message_id):
    headers = {
        "Authorization": f"Bearer {access_token}"
    }

    response = requests.get(base_url + f"/messages/{message_id}", headers=headers)
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


# Function to check and send welcome message if first contact через бота
def handle_first_contact_with_user(user_id):
    if user_id not in student_contacts:
        welcome_message = (
            "Я бот для проведения стендап-отчетов. Пожалуйста, отвечай на мои следующие сообщения в комментариях в течение часа.\n"
            "Если ты заболел или ушёл в отпуск, напиши /sick или /rest соответственно."
        )
        send_message("user", user_id, welcome_message)
        student_contacts.add(user_id)


# A function for interviewing students of chat
def handle_standup(chat_id):
    chat = get_chat_info(chat_id)

    if chat['owner_id'] == bot_id:
        return

    heads = heads_of_chat[chat_id] if chat_id in heads_of_chat else []
    for member in chat['member_ids']:
        if (member not in heads) and (member != bot_id) and (member not in incapable_student):
            handle_first_contact_with_user(member)
            student_of_chat.setdefault(chat_id, []).append(member)
            standup_message = f"Напиши стендап-отчет для следующего проекта '{chat['name']}':\n1) Что было сделано?\n2) Какие планы до следующего стендапа?\n3) Какие трудности возникли?\n4) Нужно ли с кем-то связаться для их решения?"
            message_data = send_message("user", member, standup_message)
            if message_data:
                message_ids.setdefault(chat_id, {})[member] = message_data['id']


# get answers on standup messages
async def handle_answers(chat_id, time):
    members = student_of_chat[chat_id]
    message_content = ""
    late_student = []

    await asyncio.sleep(time)

    for member in members:
        if member in message_ids[chat_id] and member not in incapable_student:
            answer = get_thread_responses(message_ids[chat_id][member])
            if answer is not None:
                user_info = get_user_info(member)
                message_content += f"Стендап пользователя '{user_info['first_name']} {user_info['last_name']}':\n{answer}\n"
            else:
                late_student.append(member)

    for member in late_student:
        user_info = get_user_info(member)
        message_content += f"Пользователь '{user_info['first_name']} {user_info['last_name']}' опоздал\n"

    heads = heads_of_chat[chat_id]
    for member in get_chat_members(chat_id):
        if member in incapable_student and member not in heads:
            user_info = get_user_info(member)
            message_content += f"Пользователь '{user_info['first_name']} {user_info['last_name']}' {incapable_student[member]}\n"

    if message_content != "":
        send_message("discussion", chat_id, message_content)

    student_of_chat.pop(chat_id)
    message_ids.pop(chat_id)


# welcome message to chat
def handle_first_contact_with_chat():
    chats = get_all_chats()
    for chat in chats:
        if (chat['owner_id'] != bot_id) and (chat['id'] not in chat_contacts):
            chat_contacts.add(chat['id'])
            input_message = (
                "Я бот для проведения стендап-отчетов. Давайте настроим необходимые параметры:\n\n"
                "1. Руководители стендапов:\n"
                "   Пожалуйста, укажите имена пользователей, которые будут руководителями стендапов (не будут опрашиваться). Нужно написать сообщение, начинающееся с /head и указать имена пользователей через пробел. Пример: '/head @nickname1 @nickname2')\n"
                "2. Ограничение времени на стендап:\n"
                "   Установите максимальное время (в минутах), которое может занимать каждый стендап, с помощью команды /limit. Пример: '/limit 60'\n"
                "3. Расписание стендапов:\n"
                "   Укажите время, когда будут проводиться стендапы, используя команду /schedule. Формат ввода: /schedule <день> <время>. Пример: /schedule понедельник 18:00 среда 18:00 пятница 18:00.\n\n"
                "Чтобы приостановить или возобновить стендапы в этом чате, используйте команду /pause.\n"
                "Для вызова справки используйте /help"
            )
            send_message("discussion", chat['id'], input_message)







