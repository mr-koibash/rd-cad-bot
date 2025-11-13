from typing import Any
from psycopg2.pool import SimpleConnectionPool

from db.base.abstract import AbstractDatabaseManager


class PsqlDatabaseManager(AbstractDatabaseManager):
    def __init__(self, dbname: str, user: str, password: str, host='localhost', port='5432', minconn=1, maxconn=10):
        self.pool = SimpleConnectionPool(
            minconn,
            maxconn,
            dbname=dbname,
            user=user,
            password=password,
            host=host,
            port=port
        )

    def execute_query(self, query: str, params=None) -> list[Any]:
        conn = self.pool.getconn()
        try:
            with conn.cursor() as cursor:
                cursor.execute(query, params)
                return cursor.fetchall()
        finally:
            self.pool.putconn(conn)

    def execute_update_query(self, query: str, params=None) -> None:
        conn = self.pool.getconn()
        try:
            with conn.cursor() as cursor:
                cursor.execute(query, params)
                conn.commit()
        finally:
            self.pool.putconn(conn)

    def close(self):
        if self.pool:
            self.pool.closeall()
