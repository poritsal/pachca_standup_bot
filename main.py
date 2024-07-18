import pytz
from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional
from api import *
from datetime import datetime
import asyncio
import re
from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(app: FastAPI):
    asyncio.create_task(main_loop())
    yield

app = FastAPI(lifespan=lifespan)


@app.get("/")
async def read_root():
    return {"message": "Server is running"}


class WebhookEvent(BaseModel):
    type: str
    id: int
    event: str
    entity_type: str
    entity_id: int
    content: str
    user_id: int
    created_at: str
    chat_id: int
    thread: Optional[dict] = None


@app.post("/webhook")
async def handle_webhook(event: WebhookEvent):
    content = event.content
    chat = get_chat_info(event.chat_id)

    if content.startswith("/sick"):
        if chat['owner_id'] != bot_id:
            return
        user_id = event.user_id
        if user_id not in incapable_student:
            incapable_student[user_id] = "болеет"
            sick_message = "Надеюсь на твое скорейшее выздоровление. Напиши /return, когда вернешься и захочешь принять участие в следующем стендапе."
            send_message("user", user_id, sick_message)
        else:
            send_message("user", user_id, "Вероятно ты уже болеешь или отдыхаешь, напиши /return и повтори запрос")

    elif content.startswith("/rest"):
        if chat['owner_id'] != bot_id:
            return
        user_id = event.user_id
        if user_id not in incapable_student:
            incapable_student[user_id] = "отдыхает"
            rest_message = "Приятного тебе отдыха. Напиши /return, когда вернешься и захочешь принять участие в следующем стендапе."
            send_message("user", user_id, rest_message)
        else:
            send_message("user", user_id, "Вероятно ты уже болеешь или отдыхаешь, напиши /return и повтори запрос")

    elif content.startswith("/return"):
        if chat['owner_id'] != bot_id:
            return
        user_id = event.user_id
        if user_id in incapable_student:
            return_message = "Отлично, буду ждать твоих ответов в комментариях."
            send_message("user", user_id, return_message)
            if user_id in incapable_student:
                incapable_student.pop(user_id)

    elif content.startswith("/heads"):
        if chat['owner_id'] == bot_id:
            return
        nicknames = content.split()[1:]
        chat_id = event.entity_id

        if nicknames:
            if chat_id in heads_of_chat:
                heads_of_chat.pop(chat_id)
            heads_message = "Руководителями чата назначены:\n"
            for nickname in nicknames:
                user = get_user_id_by_nickname(nickname[1:])
                if not user:
                    send_message("disscussion", chat_id, f"Пользователь '{nickname}' не найден, повторите запрос")
                    return
                heads_message += f"{user['first_name']} {user['last_name']}\n"
                heads_of_chat.setdefault(chat_id, []).append(user['id'])
            send_message("discussion", chat_id, heads_message)
        else:
            send_message("discussion", chat_id, "Неправильный формат ввод, пример: '/head @nickname1 @nickname2'")

    elif content.startswith("/schedule"):
        if chat['owner_id'] == bot_id:
            return

        schedule = content.split()[1:]
        chat_id = event.entity_id

        if chat_id in schedule_of_chats:
            schedule_of_chats.pop(chat_id)

        if len(schedule) % 2 != 0:
            send_message("discussion", chat_id, "Неправильный формат расписания. Пожалуйста, укажите пары день-время.")
            return

        time_pattern = re.compile(r'^([01]?[0-9]|2[0-3]):([0-5][0-9])$')

        for i in range(0, len(schedule), 2):
            day = schedule[i].lower()
            time = schedule[i + 1]
            days_dict = {"понедельник": "monday", "вторник": "tuesday", "среда": "wednesday", "четверг": "thursday", "пятница": "friday", "суббота": "saturday", "воскресенье": "sunday"}
            if day not in days_dict:
                send_message("discussion", chat_id, "Неправильное написание дня недели. Вот возможные варианты: понедельник, вторник, среда, четверг, пятница, суббота, воскресенье")
                return
            if not time_pattern.match(time):
                send_message("discussion", chat_id, f"Неправильный формат времени: {time}. Пожалуйста, используйте HH:MM.")
                return
            datetime.strptime(time, "%H:%M")
            schedule_of_chats.setdefault(chat_id, []).append((day, time))

        schedule_message = f"Расписание для стендапов установлено:\n"
        for day, time in schedule_of_chats[chat_id]:
            schedule_message += f"{day} {time}\n"

        send_message("discussion", chat_id, schedule_message)

    elif content.startswith("/limit"):
        if chat['owner_id'] == bot_id:
            return

        chat_id = event.entity_id
        try:
            time_limit = int(content.split()[1])
            time_limit_of_chats[chat_id] = time_limit
            send_message("discussion", chat_id, f"Ограничение времени на стендап установлено: {time_limit} минут.")
        except (IndexError, ValueError):
            send_message("discussion", chat_id, "Неправильный формат команды. Используйте /limit <минуты>.")

    elif content.startswith("/pause"):
        if chat['owner_id'] == bot_id:
            return
        if event.entity_id in paused_chats:
            paused_chats.remove(event.entity_id)
            send_message("discussion", event.entity_id, f"Стендапы возобновлены")
        else:
            paused_chats.append(event.entity_id)
            send_message("discussion", event.entity_id, f"Стендапы приостановлены, используй /pause, чтобы возобновить работу бота")

    elif content.startswith("/help"):
        if chat['owner_id'] != bot_id:
            help_message = (
                "Используйте:\n"
                "/pause, чтобы приостановить стендапы в этом чате.\n"
                "/head, чтобы назначить руководителей для стендапов.\n"
                "/limit, чтобы установить ограничение по времени на стендап. Формат: /limit <минуты>.\n"
                "/schedule, чтобы установить расписание стендапов. Формат: /schedule <день> <время> ...\n"
                "/delete, чтобы удалить информацию о стендапах в этом чате.\n"
            )
            send_message("discussion", event.entity_id, help_message)
        else:
            user_help_message = (
                "Используйте:\n"
                "/sick, чтобы сообщить, что вы заболели.\n"
                "/rest, чтобы сообщить, что вы отдыхаете.\n"
                "/return, чтобы сообщить, что вы вернулись к работе."
            )
            send_message("user", event.entity_id, user_help_message)

    elif content.startswith("/delete"):
        if chat['owner_id'] == bot_id:
            return
        chat_id = event.entity_id
        if chat_id in schedule_of_chats:
            schedule_of_chats.pop(event.entity_id)
        if chat_id in heads_of_chat:
            heads_of_chat.pop(event.entity_id)
        if chat_id in time_limit_of_chats:
            time_limit_of_chats.pop(event.entity_id)
        if chat_id in paused_chats:
            paused_chats.remove(event.entity_id)

        send_message("discussion", event.entity_id, f"Стендапы удалены, используйте /schdule /limit /head для восстановления работы")


async def main_loop():
    tz = pytz.timezone('Europe/Moscow')
    days_dict = {"понедельник": "monday", "вторник": "tuesday", "среда": "wednesday", "четверг": "thursday", "пятница": "friday", "суббота": "saturday", "воскресенье": "sunday"}
    while True:
        current_time = datetime.now(tz)
        handle_first_contact_with_chat()

        for chat_id, schedule in schedule_of_chats.items():
            if chat_id in paused_chats:
                continue

            for day, time in schedule:
                schedule_time = datetime.strptime(time, "%H:%M").time()
                if current_time.strftime("%A").lower() == days_dict[day] and current_time.time().hour == schedule_time.hour and current_time.time().minute == schedule_time.minute:
                    handle_standup(chat_id)

                    if chat_id in time_limit_of_chats:
                        limit = time_limit_of_chats[chat_id]
                        asyncio.create_task(handle_answers(chat_id, limit * 60))
                    else:
                        asyncio.create_task(handle_answers(chat_id, 3600))

        await asyncio.sleep(60)


if __name__ == '__main__':
    schedule_of_chats = {10044727: [('среда', '18:51')]}
    asyncio.run(main_loop())
    # import uvicorn
    # uvicorn.run(app, host="127.0.0.1", port=8000)