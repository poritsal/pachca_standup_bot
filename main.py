from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional
from contextlib import asynccontextmanager

import pytz
from datetime import datetime
import re

import asyncio
from handle_standup import *

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    asyncio.create_task(main_loop())
    yield
    await close_db()


app = FastAPI(lifespan=lifespan)


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


@app.get("/")
async def read_root():
    return {"message": "Server is running"}


@app.post("/webhook")
async def handle_webhook(event: WebhookEvent):
    content = event.content
    chat = get_chat_info(event.chat_id)

    if content.startswith("/standup-sick"):
        if chat['owner_id'] != bot_id:
            return
        user_id = event.user_id

        async with SessionLocal() as session:
            query = select(StudentOrm).where(StudentOrm.incapable.in_(["болеет", "отдыхает"]))
            result = await session.execute(query)
            incapable_students = {student.student_id: student.incapable for student in result.scalars().all()}

            if user_id not in incapable_students:
                stmt = update(StudentOrm).where(StudentOrm.student_id == user_id).values(incapable="болеет")
                await session.execute(stmt)
                await session.commit()

                sick_message = "Надеюсь на твое скорейшее выздоровление. Напиши /standup-return, когда вернешься и захочешь принять участие в следующем стендапе."
                send_message("user", user_id, sick_message)
            else:
                send_message("user", user_id, "Вероятно ты уже болеешь или отдыхаешь, напиши /standup-return и повтори запрос")

    elif content.startswith("/standup-rest"):
        if chat['owner_id'] != bot_id:
            return
        user_id = event.user_id

        async with SessionLocal() as session:
            query = select(StudentOrm).where(StudentOrm.incapable.in_(["болеет", "отдыхает"]))
            result = await session.execute(query)
            incapable_students = {student.student_id: student.incapable for student in result.scalars().all()}

            if user_id not in incapable_students:
                stmt = update(StudentOrm).where(StudentOrm.student_id == user_id).values(incapable="отдыхает")
                await session.execute(stmt)
                await session.commit()

                rest_message = "Приятного тебе отдыха. Напиши /standup-return, когда вернешься и захочешь принять участие в следующем стендапе."
                send_message("user", user_id, rest_message)
            else:
                send_message("user", user_id, "Вероятно ты уже болеешь или отдыхаешь, напиши /standup-return и повтори запрос")

    elif content.startswith("/standup-return"):
        if chat['owner_id'] != bot_id:
            return
        user_id = event.user_id

        async with SessionLocal() as session:
            query = select(StudentOrm).where(StudentOrm.incapable.in_(["болеет", "отдыхает"]))
            result = await session.execute(query)
            incapable_students = {student.student_id: student.incapable for student in result.scalars().all()}

            if user_id in incapable_students:
                stmt = update(StudentOrm).where(StudentOrm.student_id == user_id).values(incapable="")
                await session.execute(stmt)
                await session.commit()

                sick_message = "Отлично, буду ждать твоих ответов в комментариях."
                send_message("user", user_id, sick_message)

    elif content.startswith("/standup-ignore"):
        if chat['owner_id'] == bot_id:
            return

        if get_user_info(event.user_id)['role'] != 'admin':
            send_message('discussion', event.entity_id, "Возможность редактирования стендапов есть только у администратора")
            return

        nicknames = content.split()[1:]
        chat_id = event.entity_id

        async with SessionLocal() as session:
            query = select(ChatOrm).where(ChatOrm.chat_id == chat_id)
            result = await session.execute(query)
            chat_record = result.scalars().first()

            ignore_members = []

            if nicknames:
                if not chat_record:
                    send_message("discussion", chat_id, "Чат не найден в базе данных.")
                    return
                ignore_message = "Игнорируемые пользователи чата:\n"
                for nickname in nicknames:
                    user = get_user_id_by_nickname(nickname[1:])
                    if not user:
                        send_message("discussion", chat_id, f"Пользователь '{nickname}' не найден, повторите запрос")
                        return
                    ignore_message += f"{user['first_name']} {user['last_name']}\n"
                    ignore_members.append(user['id'])

                stmt = update(ChatOrm).where(ChatOrm.chat_id == chat_id).values(ignore_members=ignore_members)
                await session.execute(stmt)
                await session.commit()

                send_message("discussion", chat_id, ignore_message)
            else:
                send_message("discussion", chat_id, "Неправильный формат ввода, пример: '/standup-ignore @nickname1 @nickname2'")

    elif content.startswith("/standup-schedule"):
        if chat['owner_id'] == bot_id:
            return

        if get_user_info(event.user_id)['role'] != 'admin':
            send_message('discussion', event.entity_id, "Возможность редактирования стендапов есть только у администратора")
            return

        schedule = content.split()[1:]
        chat_id = event.entity_id

        if len(schedule) % 2 != 0:
            send_message("discussion", chat_id, "Неправильный формат расписания. Пожалуйста, укажите пары день-время.")
            return

        time_pattern = re.compile(r'^([01]?[0-9]|2[0-3]):([0-5][0-9])$')
        days_dict = {"понедельник": "monday", "вторник": "tuesday", "среда": "wednesday", "четверг": "thursday", "пятница": "friday", "суббота": "saturday", "воскресенье": "sunday"}
        new_schedule = []

        for i in range(0, len(schedule), 2):
            day = schedule[i].lower()
            time = schedule[i + 1]
            if day not in days_dict:
                send_message("discussion", chat_id, "Неправильное написание дня недели. Вот возможные варианты: понедельник, вторник, среда, четверг, пятница, суббота, воскресенье")
                return
            if not time_pattern.match(time):
                send_message("discussion", chat_id, f"Неправильный формат времени: {time}. Пожалуйста, используйте HH:MM.")
                return
            datetime.strptime(time, "%H:%M")
            new_schedule.append((day, time))

        async with SessionLocal() as session:
            query = select(ChatOrm).where(ChatOrm.chat_id == chat_id)
            result = await session.execute(query)
            chat_record = result.scalars().first()

            if not chat_record:
                send_message("discussion", chat_id, "Чат не найден в базе данных.")
                return

            await session.execute(
                update(ChatOrm)
                .where(ChatOrm.chat_id == chat_id)
                .values(schedule_of_chat=new_schedule)
            )
            await session.commit()

            schedule_message = f"**Расписание для стендапов установлено:**\n"
            for day, time in new_schedule:
                schedule_message += f"{day} {time}\n"

            schedule_message += f"\n**Ограничение по времени {chat_record.limit} минут**\n\n"

            schedule_message += "**Участники:\n**"
            ignore = chat_record.ignore_members if chat_record.ignore_members else []

            for member in chat_record.member_ids:
                if (member not in ignore) and (member != bot_id):
                    user_info = get_user_info(member)
                    schedule_message += f"{user_info['first_name']} {user_info['last_name']}\n"

            send_message("discussion", chat_id, schedule_message)

    elif content.startswith("/standup-limit"):
        if chat['owner_id'] == bot_id:
            return

        if get_user_info(event.user_id)['role'] != 'admin':
            send_message('discussion', event.entity_id, "Возможность редактирования стендапов есть только у администратора")
            return

        chat_id = event.entity_id
        try:
            time_limit = int(content.split()[1])
        except (IndexError, ValueError):
            send_message("discussion", chat_id, "Неправильный формат команды. Используйте /standup-limit <минуты>.")
            return

        async with SessionLocal() as session:
            query = select(ChatOrm).where(ChatOrm.chat_id == chat_id)
            result = await session.execute(query)
            chat_record = result.scalars().first()

            if not chat_record:
                send_message("discussion", chat_id, "Чат не найден в базе данных.")
                return

            chat_record.limit = time_limit
            session.add(chat_record)
            await session.commit()
            send_message("discussion", chat_id, f"Ограничение времени на стендап установлено: {time_limit} минут.")

    elif content.startswith("/standup-pause"):
        if chat['owner_id'] == bot_id:
            return

        if get_user_info(event.user_id)['role'] != 'admin':
            send_message('discussion', event.entity_id, "Возможность редактирования стендапов есть только у администратора")
            return

        chat_id = event.entity_id

        async with SessionLocal() as session:
            query = select(ChatOrm).where(ChatOrm.chat_id == chat_id)
            result = await session.execute(query)
            chat_record = result.scalars().first()

            if not chat_record:
                await send_message("discussion", chat_id, "Чат не найден в базе данных.")
                return

            if chat_record.pause:
                chat_record.pause = False
                send_message("discussion", chat_id, f"Стендапы возобновлены")
            else:
                chat_record.pause = True
                send_message("discussion", chat_id, f"Стендапы приостановлены, используй /standup-pause, чтобы возобновить работу бота")

            session.add(chat_record)
            await session.commit()

    elif content.startswith("/standup-help"):
        if chat['owner_id'] != bot_id:
            help_message = (
                "Используйте:\n"
                "/standup-pause, чтобы приостановить стендапы в этом чате.\n"
                "/standup-ignore, чтобы назначить руководителей для стендапов.\n"
                "/standup-limit, чтобы установить ограничение по времени на стендап. Формат: /standup-limit <минуты>.\n"
                "/standup-schedule, чтобы установить расписание стендапов. Формат: /standup-schedule <день> <время> ...\n"
                "/standup-delete, чтобы удалить информацию о стендапах в этом чате.\n"
            )
            send_message("discussion", event.entity_id, help_message)
        else:
            user_help_message = (
                "Используйте:\n"
                "/standup-sick, чтобы сообщить, что вы заболели.\n"
                "/standup-rest, чтобы сообщить, что вы отдыхаете.\n"
                "/standup-return, чтобы сообщить, что вы вернулись к работе."
            )
            send_message("user", event.entity_id, user_help_message)

    elif content.startswith("/standup-delete"):
        if chat['owner_id'] == bot_id:
            return

        if get_user_info(event.user_id)['role'] != 'admin':
            send_message('discussion', event.entity_id, "Возможность редактирования стендапов есть только у администратора")
            return

        chat_id = event.entity_id
        async with SessionLocal() as session:
            query = select(ChatOrm).where(ChatOrm.chat_id == chat_id)
            result = await session.execute(query)
            chat_record = result.scalars().first()

            if not chat_record:
                send_message("discussion", chat_id, "Чат не найден в базе данных.")
                return

            await session.execute(
                update(ChatOrm)
                .where(ChatOrm.chat_id == chat_id)
                .values(
                    schedule_of_chat=[],
                    ignore_members=[],
                    limit=60,
                    pause=False
                )
            )
            await session.commit()

            send_message("discussion", chat_id, f"Стендапы удалены, используйте /standup-schedule, /standup-limit, /standup-head для восстановления работы")


async def main_loop():
    tz = pytz.timezone('Europe/Moscow')
    days_dict = {"понедельник": "monday", "вторник": "tuesday", "среда": "wednesday", "четверг": "thursday", "пятница": "friday", "суббота": "saturday", "воскресенье": "sunday"}

    while True:
        current_time = datetime.now(tz)
        await handle_first_contact_with_chat()
        await sync_students_with_api()

        async with SessionLocal() as session:
            chats = await get_all_chats_from_db(session)

            for chat in chats:
                if chat.pause:
                    continue

                for schedule in chat.schedule_of_chat:
                    day, time = schedule
                    schedule_time = datetime.strptime(time, "%H:%M").time()

                    if current_time.strftime("%A").lower() == days_dict[day] and current_time.time().hour == schedule_time.hour and current_time.time().minute == schedule_time.minute:
                        await handle_standup(chat)
                        asyncio.create_task(handle_answers(chat, chat.limit * 60))

        await asyncio.sleep(60)