import asyncio
import asyncpg
from src.database.database import get_connection

async def init_database():
    conn = await get_connection()
    # Créer les tables
    await conn.close()

if __name__ == "__main__":
    asyncio.run(init_database())
