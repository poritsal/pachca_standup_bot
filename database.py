from sqlalchemy import Column, Integer, String, Boolean, JSON, MetaData
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.future import select
from sqlalchemy.orm import sessionmaker
from sqlalchemy import update
import asyncpg
import greenlet
import os
from dotenv import load_dotenv

Base = declarative_base()


class ChatOrm(Base):
    __tablename__ = 'chats'

    chat_id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    owner_id = Column(Integer)
    member_ids = Column(JSON)  # JSON list of member ids
    pause = Column(Boolean, default=False)
    limit = Column(Integer, default=60)
    ignore_members = Column(JSON)
    schedule_of_chat = Column(JSON)  # JSON list of (day, time) pairs


class StudentOrm(Base):
    __tablename__ = 'students'

    student_id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String)
    last_name = Column(String)
    nickname = Column(String)
    incapable = Column(String)

    load_dotenv()
# postgresql+asyncpg://postgres:1234@localhost:5432/standup
DATABASE_URL = f"postgresql+asyncpg://{os.getenv('DB_USER')}:{os.getenv('DB_PASS')}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
engine = create_async_engine(DATABASE_URL, echo=True)
SessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)


# chat
async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db():
    await engine.dispose()


async def get_chat_from_db(db: AsyncSession, chat_id: int):
    result = await db.execute(select(ChatOrm).where(ChatOrm.chat_id == chat_id))
    return result.scalars().first()


async def get_all_chats_from_db(session: AsyncSession):
    result = await session.execute(select(ChatOrm))
    return result.scalars().all()


async def create_chat(db: AsyncSession, chat: ChatOrm):
    db.add(chat)
    await db.commit()
    await db.refresh(chat)
    return chat


async def update_chat(db: AsyncSession, chat_id: int, chat_data: dict):
    chat = await get_chat_from_db(db, chat_id)
    for key, value in chat_data.items():
        setattr(chat, key, value)
    await db.commit()
    return chat


async def delete_chat(db: AsyncSession, chat_id: int):
    chat = await get_chat_from_db(db, chat_id)
    await db.delete(chat)
    await db.commit()
    return chat


# student
async def get_student_from_db(db: AsyncSession, student_id: int):
    result = await db.execute(select(StudentOrm).where(StudentOrm.student_id == student_id))
    return result.scalars().first()

async def create_student(db: AsyncSession, student: StudentOrm):
    db.add(student)
    await db.commit()
    await db.refresh(student)
    return student


async def update_student(db: AsyncSession, student_id: int, student_data: dict):
    student = await get_student_from_db(db, student_id)
    for key, value in student_data.items():
        setattr(student, key, value)
    await db.commit()
    return student


async def delete_student(db: AsyncSession, student_id: int):
    student = await get_student_from_db(db, student_id)
    await db.delete(student)
    await db.commit()
    return student
