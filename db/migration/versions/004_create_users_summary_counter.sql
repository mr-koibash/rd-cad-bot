ALTER TABLE telegram_users
    ADD COLUMN IF NOT EXISTS unsummated_messages_counter BIGINT NOT NULL DEFAULT 0;
