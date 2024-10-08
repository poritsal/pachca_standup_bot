from database import *
from api import *
import asyncio

message_ids = {}  # {chat_id: {member_id: message_id}}
student_of_chat = {}  # {chat_id: [member1_id, member2_id]} reviewed students


async def handle_first_contact_with_user(user_id: int) -> None:
    async with SessionLocal() as session:
        query = select(StudentOrm).where(StudentOrm.student_id == user_id)
        result = await session.execute(query)
        student = result.scalars().first()
        user_info = get_user_info(user_id)

        if not student:
            if user_info['bot'] == False:
                welcome_message = (
                    "Я бот для проведения стендап-отчетов. Пожалуйста, отвечай на мои следующие сообщения в комментариях (в тредах).\n"
                    "Ты можешь редактировать ответ в течение отведенного на стендап времени, в случае нескольких сообщений в комментариях будет отправлено последнее.\n"
                    "Если ты заболел или ушёл в отпуск, напиши **/standup-sick** или **/standup-rest** соответственно.\n\n"
                    "**Формат ответа на стендапы:**\n"
                    "1) текст\n"
                    "2) текст\n"
                    "3) текст\n"
                    "4) текст\n"
                )
                send_message("user", user_id, welcome_message)

                new_student = StudentOrm(student_id=user_id, first_name=user_info['first_name'], last_name=user_info['last_name'], nickname=user_info['nickname'], incapable="")
                session.add(new_student)
                await session.commit()
        else:
            if student.first_name != user_info['first_name'] or student.last_name != ['last_name'] or student.nickname != ['nickname']:
                await session.execute(
                    update(StudentOrm)
                    .where(StudentOrm.student_id == user_id)
                    .values(
                        first_name=user_info['first_name'],
                        last_name=user_info['last_name'],
                        nickname=user_info['nickname']
                    )
                )
                await session.commit()


# A function for interviewing students of chat
async def handle_standup(chat: Sequence[ChatOrm]) -> None:
    if chat.owner_id == bot_id:
        return

    async with SessionLocal() as session:
        query = select(StudentOrm).where(StudentOrm.incapable.in_(["болеет", "отдыхает"]))
        result = await session.execute(query)
        incapable_students = [student.student_id for student in result.scalars().all()]

    for member in chat.member_ids:
        if member not in chat.ignore_members and member != bot_id and member not in incapable_students:
            await handle_first_contact_with_user(member)
            student_of_chat.setdefault(chat.chat_id, []).append(member)
            standup_message = (f"**Напиши в комментариях (в треде) стендап-отчет для проекта '{chat.name}':**\n"
                               f"1) Что было сделано?\n"
                               f"2) Какие планы до следующего стендапа?\n"
                               f"3) Какие трудности возникли?\n"
                               f"4) Нужно ли с кем-то связаться для их решения?")
            message_data = send_message("user", member, standup_message)
            if message_data:
                message_ids.setdefault(chat.chat_id, {})[member] = message_data['id']


# get answers on standup messages
async def handle_answers(chat: Sequence[ChatOrm], time: int) -> None:
    chat_id = chat.chat_id
    members = student_of_chat[chat_id]
    late_student = []
    students_with_incorrect_answer = {}

    await asyncio.sleep(time)

    async with SessionLocal() as session:
        query = select(StudentOrm).where(StudentOrm.incapable.in_(["болеет", "отдыхает"]))
        result = await session.execute(query)
        incapable_students = {student.student_id: student.incapable for student in result.scalars().all()}

    for member in members:
        if member in message_ids[chat_id] and member not in incapable_students:
            answer = get_thread_responses(message_ids[chat_id][member])

            if answer is None:
                late_student.append(member)
                continue

            async with SessionLocal() as session_ui:
                user_info = await get_student_from_db(session_ui, member)

            answers = answer.split('\n')
            if len(answers) != 4:
                students_with_incorrect_answer[member] = answer
                continue

            message_content = (
                f"Стендап пользователя **'{user_info.first_name} {user_info.last_name}'**:\n\n"
                f"**1: Что было сделано?**\n{answers[0][2:]}\n"
                f"**2: Какие планы до следующего стендапа?**\n{answers[1][2:]}\n"
                f"**3: Какие трудности возникли?**\n{answers[2][2:]}\n"
                f"**4: Нужно ли с кем-то связаться для их решения?**\n{answers[3][2:]}"
            )
            send_message("discussion", chat_id, message_content)

    for member in students_with_incorrect_answer:
        async with SessionLocal() as session_ui:
            user_info = await get_student_from_db(session_ui, member)
        incorrect_content = (f"Стендап пользователя **'{user_info.first_name} {user_info.last_name}'**:\n\n"
                            f"{students_with_incorrect_answer[member]}\n")
        send_message("discussion", chat_id, incorrect_content)

    message_content = ""

    for member in late_student:
        async with SessionLocal() as session_ui:
            user_info = await get_student_from_db(session_ui, member)
        message_content += f"Пользователь '{user_info.first_name} {user_info.last_name}' опоздал\n"

    for member in chat.member_ids:
        if member in incapable_students and member not in chat.ignore_members:
            async with SessionLocal() as session_ui:
                user_info = await get_student_from_db(session_ui, member)
            message_content += f"Пользователь '{user_info.first_name} {user_info.last_name}' {incapable_students[member]}\n"

    if message_content != "":
        send_message("discussion", chat_id, message_content)

    student_of_chat.pop(chat_id)
    message_ids.pop(chat_id)


# welcome message to chat
async def handle_first_contact_with_chat() -> None:
    async with SessionLocal() as session:
        api_chats = get_all_chats()
        db_chats = await get_all_chats_from_db(session)

        db_chats_dict = {chat.chat_id: chat for chat in db_chats}

        for chat in api_chats:
            chat_id = chat['id']
            if (chat['owner_id'] != bot_id) and (chat_id not in db_chats_dict):
                input_message = (
                    "Я бот для проведения стендап-отчетов. Давайте настроим необходимые параметры:\n\n"
                    "**1. Игнорируемые пользователи:**\n"
                    "   Пожалуйста, укажите имена пользователей, которые не будут опрашиваться. Нужно написать сообщение, начинающееся с **/standup-ignore** и указать имена пользователей через пробел. Пример: '/standup-ignore @nickname1 @nickname2'\n"
                    "**2. Ограничение времени на стендап:**\n"
                    "   Установите максимальное время (в минутах), которое может занимать каждый стендап, с помощью команды **/standup-limit**. Пример: '/standup-limit 60'\n"
                    "**3. Расписание стендапов:**\n"
                    "   Укажите время, когда будут проводиться стендапы, используя команду **/standup-schedule**. Формат ввода: '/standup-schedule <день> <время>'. Пример: '/standup-schedule понедельник 18:00 среда 18:00 пятница 18:00'.\n"
                    "Для приостановки или возобновления стендапов в этом чате, используйте команду **/standup-pause**. Для удаления информацию о стендапах используйте **/standup-delete**. Для вызова справки используйте **/standup-help**\n\n"
                    "**Сейчас установлено стандартное расписание для стендапов:**\n"
                    "понедельник 18:00\n"
                    "среда 18:00\n"
                    "пятница 18:00\n\n"
                    "**Ограничение по времени 360 минут**"
                )
                send_message("discussion", chat_id, input_message)
                student_ids = [student for student in chat['member_ids'] if get_user_info(student)['bot'] == False]

                new_chat = ChatOrm(
                    chat_id=chat_id,
                    name=chat['name'],
                    owner_id=chat['owner_id'],
                    member_ids=student_ids,
                    pause=False,
                    limit=360,
                    ignore_members=[],
                    schedule_of_chat=[('понедельник', '18:00'), ('среда', '18:00'), ('пятница', '18:00')]
                )
                session.add(new_chat)
                await session.commit()

            elif chat['owner_id'] != bot_id:
                student_ids = [student for student in chat['member_ids'] if get_user_info(student)['bot'] == False]
                if db_chats_dict[chat_id].name != chat['name'] or db_chats_dict[chat_id].member_ids != student_ids:
                    await session.execute(
                        update(ChatOrm)
                        .where(ChatOrm.chat_id == chat_id)
                        .values(
                            name=chat['name'],
                            member_ids=student_ids
                        )
                    )
                    await session.commit()

        if api_chats:
            api_chat_ids = {chat['id'] for chat in api_chats}

            for db_chat in db_chats:
                if db_chat.chat_id not in api_chat_ids:
                    await session.execute(
                        delete(ChatOrm).where(ChatOrm.chat_id == db_chat.chat_id)
                    )
                    await session.commit()

        await session.commit()


async def sync_students_with_api() -> None:
    async with SessionLocal() as session:
        students_from_api = get_all_users()
        if students_from_api:
            api_student_ids = [student['id'] for student in students_from_api if get_user_info(student['id'])['bot'] == False]

            result = await session.execute(select(StudentOrm))
            students_from_db = result.scalars().all()
            api_students_from_db = [student.student_id for student in students_from_db]

            for student_id in api_students_from_db:
                if student_id not in api_student_ids:
                    await session.execute(delete(StudentOrm).where(StudentOrm.student_id == student_id))

            await session.commit()
