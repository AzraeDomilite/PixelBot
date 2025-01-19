import asyncpg
from typing import Optional, List, Dict, Any
from src.utils.logger import get_logger
from src.utils.config import Config

logger = get_logger(__name__)

class Database:
    def __init__(self, pool: asyncpg.Pool):
        self._pool = pool

    @property
    def pool(self) -> asyncpg.Pool:
        """Retourne le pool de connexions à la base de données"""
        return self._pool

    @classmethod
    async def create(cls, config: Config) -> 'Database':
        """Crée une instance de la base de données avec un pool de connexions"""
        try:
            pool = await asyncpg.create_pool(
                host=config.database.host,
                port=config.database.port,
                user=config.database.user,
                password=config.database.password,
                database=config.database.name
            )
            db = cls(pool)
            await db.initialize_database()
            return db
        except Exception as e:
            logger.error(f"Erreur lors de la création du pool de connexions: {e}")
            raise

    async def initialize_database(self) -> None:
        """Initialise la structure de la base de données"""
        try:
            async with self._pool.acquire() as conn:
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS user_tokens (
                        id SERIAL PRIMARY KEY,
                        discord_user_id BIGINT NOT NULL UNIQUE,
                        access_token VARCHAR(255) NOT NULL,
                        refresh_token VARCHAR(255) NOT NULL,
                        valid_token BOOLEAN DEFAULT true,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                    );
                    
                    CREATE TABLE IF NOT EXISTS votes (
                        id SERIAL PRIMARY KEY,
                        title VARCHAR(255) NOT NULL,
                        image_name VARCHAR(255) NOT NULL,
                        description TEXT,
                        image_url VARCHAR(512),
                        json_data JSONB,
                        channel_id BIGINT,
                        message_id BIGINT,
                        created_by BIGINT NOT NULL,
                        coord_x INTEGER,           -- Ajout de cette colonne
                        coord_z INTEGER,           -- Ajout de cette colonne
                        vote_count INT DEFAULT 0,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                        is_active BOOLEAN DEFAULT true
                    );
                    
                    CREATE INDEX IF NOT EXISTS idx_user_tokens_discord_user_id 
                        ON user_tokens(discord_user_id);
                    
                    CREATE INDEX IF NOT EXISTS idx_user_tokens_valid_token 
                        ON user_tokens(valid_token);

                    CREATE TABLE IF NOT EXISTS votes_pattern (
                        id SERIAL PRIMARY KEY,
                        title VARCHAR(255) NOT NULL,
                        image_name VARCHAR(255) NOT NULL,
                        image_url VARCHAR(512),
                        json_data JSONB,
                        coord_x INTEGER,
                        coord_z INTEGER,
                        vote_count INTEGER,
                        original_vote_id INTEGER REFERENCES votes(id),
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                    );
                """)
                logger.info("Base de données initialisée avec succès")
                
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation de la base de données: {e}")
            raise

    async def close(self) -> None:
        """Ferme le pool de connexions"""
        if self._pool:
            await self._pool.close()