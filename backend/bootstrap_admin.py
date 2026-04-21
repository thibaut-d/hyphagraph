import asyncio
from app.database import AsyncSessionLocal
from app.startup import bootstrap_admin_user

async def main():
    async with AsyncSessionLocal() as db:
        await bootstrap_admin_user(db)
        print("Admin bootstrap complete.")

asyncio.run(main())
