from dataclasses import dataclass
from datetime import datetime


@dataclass
class User:
    id: int
    first_name: str
    created_at: datetime

    @classmethod
    def from_db_row(cls, row):
        return cls(id=row[0], first_name=row[1], created_at=row[2])


@dataclass
class UserDialog:
    message: str
    is_user_input: bool
    created_at: datetime

    @classmethod
    def from_db_row(cls, row):
        return cls(message=row[0], is_user_input=row[1], created_at=row[2])
