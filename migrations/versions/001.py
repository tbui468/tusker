"""initial

Revision ID: 001
Revises: 
Create Date: 2026-11-16 06:37:22.079662

"""
from typing import Sequence, Union
from alembic import op


# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
  op.execute("""CREATE TABLE users (
                  id BIGSERIAL PRIMARY KEY,
                  username TEXT NOT NULL UNIQUE,
                  email TEXT NOT NULL UNIQUE,
                  password_hash TEXT NOT NULL,
                  about_me TEXT,
                  last_seen TIMESTAMPTZ,
                  last_message_read_time TIMESTAMPTZ,
                  token TEXT,
                  token_expiration TIMESTAMPTZ
              );""")

  op.execute("""CREATE TABLE followers (
                  follower_id BIGINT NOT NULL REFERENCES users(id),
                  followed_id BIGINT NOT NULL REFERENCES users(id),
                  PRIMARY KEY (follower_id, followed_id)
              );""")

  op.execute("""CREATE TABLE messages (
                  id BIGSERIAL PRIMARY KEY,
                  sender_id BIGINT NOT NULL REFERENCES users(id),
                  recipient_id BIGINT NOT NULL REFERENCES users(id),
                  body TEXT NOT NULL,
                  timestamp TIMESTAMPTZ NOT NULL
              );""")

  op.execute("""CREATE TABLE notifications (
                  id BIGSERIAL PRIMARY KEY,
                  name TEXT NOT NULL,
                  user_id BIGINT NOT NULL REFERENCES users(id),
                  timestamp FLOAT NOT NULL,
                  payload_json JSONB NOT NULL
              );""")

  op.execute("""CREATE TABLE posts (
                  id BIGSERIAL PRIMARY KEY,
                  body TEXT NOT NULL,
                  timestamp TIMESTAMPTZ NOT NULL,
                  user_id BIGINT NOT NULL REFERENCES users(id),
                  language TEXT
              );""")

  op.execute("""CREATE TABLE tasks (
                  id TEXT PRIMARY KEY,
                  name TEXT NOT NULL,
                  description TEXT,
                  user_id BIGINT NOT NULL REFERENCES users(id),
                  complete BOOLEAN NOT NULL
              );""")


def downgrade() -> None:
  op.execute("DROP TABLE users CASCADE;")
  op.execute("DROP TABLE followers;")
  op.execute("DROP TABLE messages;")
  op.execute("DROP TABLE notifications;")
  op.execute("DROP TABLE posts;")
  op.execute("DROP TABLE tasks;")
