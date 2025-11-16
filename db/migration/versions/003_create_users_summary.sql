ALTER TABLE telegram_users
    ADD COLUMN IF NOT EXISTS summary TEXT DEFAULT 'No information available';

UPDATE telegram_users
    SET summary = 'No information available';

ALTER TABLE telegram_users
    ALTER COLUMN summary SET NOT NULL;
