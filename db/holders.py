from configparser import SectionProxy

from db.managers import PsqlDatabaseManager
from db.repositories import UsersRepository, UserDialogRepository

class DbRepositoriesHolder:
    def __init__(self, app_name: str, db_config: SectionProxy):
        db = PsqlDatabaseManager(
            db_config['dbname'],
            db_config['username'],
            db_config['password'],
            db_config['host'],
            db_config['port'],
            db_config['minimum_pool_size'],
            db_config['maximum_pool_size']
        )

        self.users = UsersRepository(db, app_name=app_name)
        self.user_messages = UserDialogRepository(db, app_name=app_name)
