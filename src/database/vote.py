# src/database/models/vote.py
from datetime import datetime
from typing import Optional

class Vote:
    def __init__(
        self,
        id: Optional[int] = None,
        title: str = "",
        description: str = "",
        created_by: int = 0,
        created_at: Optional[datetime] = None,
        ends_at: Optional[datetime] = None,
        is_active: bool = True
    ):
        self.id = id
        self.title = title
        self.description = description
        self.created_by = created_by
        self.created_at = created_at or datetime.now()
        self.ends_at = ends_at
        self.is_active = is_active