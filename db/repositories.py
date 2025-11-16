from db.base.wrappers import repository
from db.entities import UserDialog, User
from db.managers import PsqlDatabaseManager


@repository()
class UsersRepository:
    def __init__(self, db: PsqlDatabaseManager, *args, **kwargs):
        self._db = db

    def add_user(self, user_id: int, first_name: str):
        query = (
            'INSERT INTO telegram_users (id, first_name, created_at) '
            'VALUES (%s, %s, CURRENT_TIMESTAMP);'
        )
        self._db.execute_update_query(query, (user_id, first_name))

    def get_user(self, user_id: int):
        query = (
            'SELECT id, first_name, created_at, summary, unsummated_messages_counter FROM telegram_users '
            'WHERE id = %s;'
        )
        rows = self._db.execute_query(query, (user_id,))
        if rows:
            return [User.from_db_row(row) for row in rows][0]

    def get_summary_by_id(self, user_id: int) -> str:
        query = (
            'SELECT summary FROM telegram_users '
            'WHERE id = %s;'
        )
        rows = self._db.execute_query(query, (user_id,))
        if rows:
            return rows[0][0]

    def update_summary_by_id(self, user_id: int, summary: str):
        query = (
            'UPDATE telegram_users SET summary = %s '
            'WHERE id = %s;'
        )
        self._db.execute_update_query(query, (summary, user_id))

    def get_unsummated_counter_by_id(self, user_id: int) -> int:
        query = (
            'SELECT unsummated_messages_counter FROM telegram_users '
            'WHERE id = %s;'
        )
        rows = self._db.execute_query(query, (user_id,))
        if rows:
            return rows[0][0]

    def update_unsummated_counter_by_id(self, user_id: int, counter: str):
        query = (
            'UPDATE telegram_users SET unsummated_messages_counter = %s '
            'WHERE id = %s;'
        )
        self._db.execute_update_query(query, (counter, user_id))


@repository()
class UserDialogRepository:
    def __init__(self, db: PsqlDatabaseManager, *args, **kwargs):
        self._db = db

    def add_user_message(self, user_id: int, message: str, is_user_input: bool, message_type: str = 'TEXT'):
        query = (
            'INSERT INTO telegram_user_dialog (user_id, message, is_user_input, type, created_at) '
            'VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP);'
        )
        self._db.execute_update_query(query, (user_id, message, is_user_input, message_type))

    def get_user_messages(self, user_id: int, limit: int = 10) -> list[UserDialog] | None:
        query = (
            'SELECT message, is_user_input, type, created_at '
            'FROM telegram_user_dialog '
            'WHERE user_id = %s '
            'ORDER BY created_at DESC '
            'LIMIT %s'
        )
        rows = self._db.execute_query(query, (user_id, limit))
        if rows:
            return [UserDialog.from_db_row(row) for row in rows]

    def delete_user_messages(self, user_id: int) -> None:
        query = (
            'DELETE FROM telegram_user_dialog WHERE user_id = %s;'
        )
        self._db.execute_update_query(query, (user_id,))
