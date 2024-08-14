from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional
from contextlib import asynccontextmanager
import pytz
from datetime import datetime
from fastapi.middleware.cors import CORSMiddleware

from webhook_handler import router as webhook_router
from handle_standup import *


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    asyncio.create_task(main_loop())
    yield
    await close_db()


app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(webhook_router)


@app.get("/")
async def read_root():
    return {"message": "Server is running"}


async def main_loop() -> None:
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
