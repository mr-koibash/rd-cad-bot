CREATE TABLE telegram_user_dialog (
    id SERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES telegram_users(id),
    message TEXT,
    is_user_input BOOLEAN,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_user_dialog_user_id ON telegram_user_dialog(user_id);
