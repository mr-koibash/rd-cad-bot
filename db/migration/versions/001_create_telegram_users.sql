CREATE TABLE telegram_users (
    id BIGINT PRIMARY KEY,
    first_name TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
