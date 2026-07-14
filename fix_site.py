import asyncio
from sqlalchemy import text
from app.db.session import async_session_factory

async def fix():
    async with async_session_factory() as db:
        await db.execute(text("UPDATE websites SET status='failed' WHERE status='pending'"))
        await db.commit()
        print("Fixed")

asyncio.run(fix())
