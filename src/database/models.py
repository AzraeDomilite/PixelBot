from datetime import datetime
from typing import Optional, Dict, Any

class UserToken:
    """Modèle représentant les tokens d'un utilisateur dans la base de données"""
    
    def __init__(
        self,
        discord_user_id: int,
        access_token: str = "",
        refresh_token: str = "",
        valid_token: bool = True,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        id: Optional[int] = None
    ):
        self.id = id
        self.discord_user_id = discord_user_id
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.valid_token = valid_token
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at or datetime.now()

    @classmethod
    def from_db(cls, record: Dict[str, Any]) -> 'UserToken':
        """Crée une instance à partir d'un enregistrement de la base de données"""
        return cls(
            id=record['id'],
            discord_user_id=record['discord_user_id'],
            access_token=record['access_token'],
            refresh_token=record['refresh_token'],
            valid_token=record['valid_token'],
            created_at=record['created_at'],
            updated_at=record['updated_at']
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convertit l'instance en dictionnaire"""
        return {
            'id': self.id,
            'discord_user_id': self.discord_user_id,
            'access_token': self.access_token,
            'refresh_token': self.refresh_token,
            'valid_token': self.valid_token,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }

    @property
    def is_complete(self) -> bool:
        """Vérifie si les deux tokens sont présents"""
        return bool(self.access_token and self.refresh_token)