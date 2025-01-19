from typing import Optional, Dict, Any, List
import asyncpg
from datetime import datetime
from src.utils.logger import get_logger

class TokenService:
    """Service de gestion des tokens utilisateurs"""

    def __init__(self, db_pool: asyncpg.Pool):
        self.db_pool = db_pool
        self.logger = get_logger(__name__)

    async def get_user_tokens(self, discord_user_id: int) -> Optional[Dict[str, Any]]:
        """
        Récupère les tokens d'un utilisateur
        
        Args:
            discord_user_id: ID Discord de l'utilisateur
            
        Returns:
            Dict contenant les tokens ou None si non trouvé
        """
        try:
            async with self.db_pool.acquire() as conn:
                return await conn.fetchrow("""
                    SELECT 
                        id,
                        discord_user_id,
                        access_token,
                        refresh_token,
                        valid_token,
                        created_at,
                        updated_at
                    FROM user_tokens 
                    WHERE discord_user_id = $1
                """, discord_user_id)
        except asyncpg.PostgresError as e:
            self.logger.error(f"Erreur lors de la récupération des tokens: {e}")
            return None

    async def update_access_token(self, discord_user_id: int, access_token: str) -> bool:
        """
        Met à jour ou crée l'access token d'un utilisateur
        
        Args:
            discord_user_id: ID Discord de l'utilisateur
            access_token: Nouveau token d'accès
            
        Returns:
            bool: True si la mise à jour est réussie
        """
        try:
            async with self.db_pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO user_tokens (
                        discord_user_id,
                        access_token,
                        refresh_token,
                        valid_token
                    ) VALUES ($1, $2, '', true)
                    ON CONFLICT (discord_user_id) DO UPDATE
                    SET 
                        access_token = $2,
                        updated_at = CURRENT_TIMESTAMP
                """, discord_user_id, access_token)
                return True
                
        except Exception as e:
            self.logger.error(f"Erreur lors de la mise à jour de l'access token: {e}")
            return False

    async def update_refresh_token(self, discord_user_id: int, refresh_token: str) -> bool:
        """
        Met à jour ou crée le refresh token d'un utilisateur
        
        Args:
            discord_user_id: ID Discord de l'utilisateur
            refresh_token: Nouveau refresh token
            
        Returns:
            bool: True si l'opération est réussie
        """
        try:
            async with self.db_pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO user_tokens (
                        discord_user_id,
                        access_token,
                        refresh_token,
                        valid_token
                    ) VALUES ($1, '', $2, true)
                    ON CONFLICT (discord_user_id) DO UPDATE
                    SET 
                        refresh_token = $2,
                        updated_at = CURRENT_TIMESTAMP
                """, discord_user_id, refresh_token)
                return True
                
        except Exception as e:
            self.logger.error(f"Erreur lors de la mise à jour du refresh token: {e}")
            return False

    async def update_tokens(
        self, 
        discord_user_id: int, 
        access_token: str,
        refresh_token: str
    ) -> bool:
        """
        Met à jour ou crée les tokens d'un utilisateur
        
        Args:
            discord_user_id: ID Discord de l'utilisateur
            access_token: Nouveau token d'accès
            refresh_token: Nouveau refresh token
            
        Returns:
            bool: True si la mise à jour est réussie
        """
        try:
            async with self.db_pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO user_tokens (
                        discord_user_id,
                        access_token,
                        refresh_token,
                        valid_token
                    ) VALUES ($1, $2, $3, true)
                    ON CONFLICT (discord_user_id) DO UPDATE
                    SET 
                        access_token = $2,
                        refresh_token = $3,
                        valid_token = true,
                        updated_at = CURRENT_TIMESTAMP
                """, discord_user_id, access_token, refresh_token)
                return True
                
        except Exception as e:
            self.logger.error(f"Erreur lors de la mise à jour des tokens: {e}")
            return False

    async def remove_user_tokens(self, discord_user_id: int) -> bool:
        """
        Supprime tous les tokens d'un utilisateur
        
        Args:
            discord_user_id: ID Discord de l'utilisateur
            
        Returns:
            bool: True si les tokens ont été supprimés
        """
        try:
            async with self.db_pool.acquire() as conn:
                result = await conn.execute("""
                    DELETE FROM user_tokens
                    WHERE discord_user_id = $1
                """, discord_user_id)
                return result == "DELETE 1"
                
        except Exception as e:
            self.logger.error(f"Erreur lors de la suppression des tokens: {e}")
            return False

    async def get_all_valid_tokens(self) -> List[Dict[str, Any]]:
        """
        Récupère tous les tokens valides
        
        Returns:
            List[Dict]: Liste des tokens valides
        """
        try:
            async with self.db_pool.acquire() as conn:
                return await conn.fetch("""
                    SELECT 
                        discord_user_id,
                        access_token,
                        refresh_token,
                        updated_at
                    FROM user_tokens
                    WHERE valid_token = true
                    ORDER BY updated_at DESC
                """)
        except Exception as e:
            self.logger.error(f"Erreur lors de la récupération des tokens valides: {e}")
            return []

    async def update_token_validity(self, discord_user_id: int, is_valid: bool) -> bool:
        """
        Met à jour la validité des tokens d'un utilisateur
        
        Args:
            discord_user_id: ID Discord de l'utilisateur
            is_valid: Nouvel état de validité
            
        Returns:
            bool: True si la mise à jour est réussie
        """
        try:
            async with self.db_pool.acquire() as conn:
                result = await conn.execute("""
                    UPDATE user_tokens
                    SET 
                        valid_token = $2,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE discord_user_id = $1
                """, discord_user_id, is_valid)
                return result == "UPDATE 1"
                
        except Exception as e:
            self.logger.error(f"Erreur lors de la mise à jour de la validité: {e}")
            return False

    async def get_tokens_stats(self) -> Dict[str, Any]:
        """
        Récupère les statistiques sur les tokens
        
        Returns:
            Dict: Statistiques des tokens
        """
        try:
            async with self.db_pool.acquire() as conn:
                stats = await conn.fetchrow("""
                    SELECT 
                        COUNT(*) as total_tokens,
                        SUM(CASE WHEN valid_token THEN 1 ELSE 0 END) as valid_tokens,
                        SUM(CASE WHEN NOT valid_token THEN 1 ELSE 0 END) as invalid_tokens,
                        COUNT(DISTINCT discord_user_id) as unique_users,
                        MAX(updated_at) as last_update
                    FROM user_tokens
                """)
                return {
                    'total_tokens': stats['total_tokens'],
                    'valid_tokens': stats['valid_tokens'] or 0,
                    'invalid_tokens': stats['invalid_tokens'] or 0,
                    'unique_users': stats['unique_users'],
                    'last_update': stats['last_update']
                }
        except Exception as e:
            self.logger.error(f"Erreur lors de la récupération des statistiques: {e}")
            return {
                'total_tokens': 0,
                'valid_tokens': 0,
                'invalid_tokens': 0,
                'unique_users': 0,
                'last_update': None
            }