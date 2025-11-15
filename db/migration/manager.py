from pathlib import Path
from db.managers import PsqlDatabaseManager


class MigrationManager:
    def __init__(self, db: PsqlDatabaseManager):
        self._db = db
        self._migrations_dir = Path(__file__).parent / 'versions'
        self._init_migrations_table()

    def _init_migrations_table(self):
        query = """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version TEXT PRIMARY KEY,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """
        self._db.execute_update_query(query)

    def get_applied_migrations(self) -> set[str]:
        query = "SELECT version FROM schema_migrations;"
        rows = self._db.execute_query(query)
        return {row[0] for row in rows}

    def apply_migration(self, version: str, sql: str):
        self._db.execute_update_query(sql)

        # write version
        query = "INSERT INTO schema_migrations (version) VALUES (%s);"
        self._db.execute_update_query(query, (version,))

    def migrate(self):
        applied = self.get_applied_migrations()

        # read migration files
        for migration_file in sorted(self._migrations_dir.glob('*.sql')):
            version = migration_file.stem

            if version not in applied:
                print(f"Applying migration: {version}")
                sql = migration_file.read_text()
                self.apply_migration(version, sql)
                print(f"✓ Applied: {version}")