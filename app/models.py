from app import login
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timezone, timedelta
from typing import Optional, Any
from flask_login import UserMixin
from hashlib import md5
from time import time
import jwt
import json
from time import time
import redis
import rq
from flask import current_app, url_for
import secrets
from dataclasses import dataclass

@login.user_loader
def load_user(id):
  with current_app.db.connection() as conn:
    return User.by_id(conn, int(id))


@dataclass
class Task:
  id: str | None = None
  name: str | None = None
  description: str | None = None
  user_id: int | None = None
  complete: bool | None = None 

  @staticmethod
  def create(conn, id, name, description, user_id):
    with conn.cursor() as cur:
      cur.execute("""
                    INSERT INTO tasks(id, name, description, user_id, complete) 
                    VALUES(%s, %s, %s, %s, %s)
                  """, (id, name, description, user_id, False))

 
  @staticmethod
  def by_id(conn, id): 
    with conn.cursor() as cur:
      row = cur.execute("""
                          SELECT id, name, description, user_id, complete
                          FROM tasks
                          WHERE id = %s
                        """, (id,)).fetchone()

    if not row:
      return None

    task = Task(id=row[0], name=row[1], description=row[2], user_id=row[3], complete=row[4])
    return task

  @staticmethod
  def update_complete(conn, id, complete):
    with conn.cursor() as cur:
      cur.execute("""
                    UPDATE tasks SET complete = %s
                    WHERE tasks.id = %s
                  """, (complete, id))

  @staticmethod
  def get_rq_job(id):
      try:
          rq_job = rq.job.Job.fetch(id, connection=current_app.redis)
      except (redis.exceptions.RedisError, rq.exceptions.NoSuchJobError):
          return None
      return rq_job

  @staticmethod
  def get_progress(id):
    job = Task.get_rq_job(id)
    return job.meta.get('progress', 0) if job is not None else 100

@dataclass(eq=False)
class User(UserMixin):
  id: int | None = None
  username: str | None = None
  email: str | None = None                
  password_hash: str | None = None        
  about_me: str | None = None             
  last_seen: datetime | None = None            
  last_message_read_time: datetime | None = None
  token: str | None = None                
  token_expiration: datetime | None = None     

  def __eq__(self, other):
    return self.username == other.username

  @staticmethod
  def create(conn, username, email, password):
    password_hash = generate_password_hash(password)
    with conn.cursor() as cur:
      cur.execute("""
                    INSERT INTO users(username, email, password_hash) 
                    VALUES(%s, %s, %s)
                  """, (username, email, password_hash))
  @staticmethod
  def by_username(conn, username):
    with conn.cursor() as cur:
      row = cur.execute("""
                        SELECT id, username, email, about_me, last_seen, last_message_read_time, token, token_expiration 
                        FROM users
                        WHERE username = %s
                       """, (username,)).fetchone()

      if not row:
        return None

      user = User(id=row[0], username=row[1], email=row[2], about_me=row[3], last_seen=row[4], last_message_read_time=row[5], token=row[6], token_expiration=row[7])
      return user

  @staticmethod
  def by_email(conn, email):
    with conn.cursor() as cur:
      row = cur.execute("""
                          SELECT id, username, email, about_me, last_seen, last_message_read_time, token, token_expiration 
                          FROM users
                          WHERE email = %s
                        """, (email,)).fetchone()

      if not row:
        return None

      user = User(id=row[0], username=row[1], email=row[2], about_me=row[3], last_seen=row[4], last_message_read_time=row[5], token=row[6], token_expiration=row[7])
      return user

  @staticmethod
  def by_id(conn, id):
    with conn.cursor() as cur:
      row = cur.execute("""
                          SELECT id, username, email, about_me, last_seen, last_message_read_time, token, token_expiration 
                          FROM users
                          WHERE id = %s
                        """, (id,)).fetchone()

    if not row:
      return None

    user = User(id=row[0], username=row[1], email=row[2], about_me=row[3], last_seen=row[4], last_message_read_time=row[5], token=row[6], token_expiration=row[7])
    return user

  @staticmethod
  def update_username(conn, id, username):
    with conn.cursor() as cur:
      cur.execute("""
                    UPDATE users SET username = %s
                    WHERE id = %s
                  """, (username, id))

  @staticmethod
  def update_password(conn, id, username):
    with conn.cursor() as cur:
      cur.execute("""
                    UPDATE users SET password = %s
                    WHERE id = %s
                  """, (id, username))

  @staticmethod
  def update_about_me(conn, id, about_me):
    with conn.cursor() as cur:
      cur.execute("""
                    UPDATE users SET about_me = %s
                    WHERE id = %s
                  """, (about_me, id))

  @staticmethod
  def update_email(conn, id, new_email):
    with conn.cursor() as cur:
      cur.execute("""
                    UPDATE users SET email = :email
                    WHERE id = :id
                  """, (new_email, id))

  @staticmethod
  def update_last_seen(conn, id, last_seen):
    with conn.cursor() as cur:
      cur.execute("""
                      UPDATE users SET last_seen = %s
                      WHERE id = %s
                  """, (last_seen, id))


  @staticmethod
  def authenticate(conn, username, password):
    with conn.cursor() as cur:
      row = cur.execute("""
                          SELECT id, username, email, about_me, last_seen, last_message_read_time, token, token_expiration, password_hash
                          FROM users
                          WHERE username = %s
                        """, (username,)).fetchone()

      if row is None:
        return None

      password_hash = row[8]
      if not check_password_hash(password_hash, password):
        return None

      user = User(id=row[0], username=row[1], email=row[2], about_me=row[3], last_seen=row[4], last_message_read_time=row[5], token=row[6], token_expiration=row[7])
      return user

  @staticmethod
  def avatar(email, size):
      digest = md5(email.lower().encode('utf-8')).hexdigest()
      return f'https://www.gravatar.com/avatar/{digest}?d=identicon&s={size}'

  @staticmethod
  def follow(conn, follower_id, followed_id):
    with conn.cursor() as cur:
      cur.execute("""
                    INSERT INTO followers(follower_id, followed_id) 
                    VALUES(%s, %s)
                  """, (follower_id, followed_id))

  @staticmethod
  def unfollow(conn, follower_id, followed_id):
    with conn.cursor() as cur:
      cur.execute("""
                    DELETE FROM followers 
                    WHERE follower_id = %s AND followed_id = %s
                  """, (follower_id, followed_id))

  @staticmethod
  def is_following(conn, follower_id, followed_id):
    with conn.cursor() as cur:
      cur.execute("""
                  SELECT EXISTS(
                    SELECT 1 FROM followers 
                    WHERE follower_id = %s 
                      AND followed_id = %s
                  )
                  """, (follower_id, followed_id))

      return cur.fetchone()[0]

  @staticmethod
  def followers_count(conn, user_id):
    with conn.cursor() as cur:
      cur.execute("""
                    SELECT COUNT(*) FROM followers 
                    WHERE followed_id = %s
                  """, (user_id,))

      return cur.fetchone()[0]

  @staticmethod
  def following_count(conn, user_id):
    with conn.cursor() as cur:
      cur.execute("""
                    SELECT COUNT(*) FROM followers 
                    WHERE follower_id = %s
                  """, (user_id,))

      return cur.fetchone()[0]

  @staticmethod
  def unread_message_count(conn, user_id):
    with conn.cursor() as cur:
      cur.execute("""SELECT COUNT(*) 
                       FROM messages
                       JOIN users ON users.id = messages.recipient_id
                     WHERE users.id = %s
                      AND (users.last_message_read_time IS NULL OR users.last_message_read_time < messages.timestamp)
                  """, (user_id,))

      return cur.fetchone()[0]

  @staticmethod
  def add_notification(conn, user_id, ntf_name, ntf_data):
    with conn.cursor() as cur:
      Notification.delete_by_name(conn, ntf_name, user_id)
      Notification.create(conn, ntf_name, user_id, json.dumps(ntf_data))

  @staticmethod
  def launch_task(conn, user_id, task_name, task_description, *args, **kwargs):
    rq_job = current_app.task_queue.enqueue(f'app.tasks.{task_name}', user_id,
                                            *args, **kwargs)

    Task.create(conn, rq_job.id, task_name, task_description, user_id) 

  @staticmethod
  def get_tasks_in_progress(user_id):
    with current_app.db.connection() as conn:
      with conn.cursor() as cur:
        rows = cur.execute("""
                             SELECT id, name, user_id, description, complete
                             FROM tasks
                             WHERE user_id = %s AND complete = FALSE
                           """, (user_id,)).fetchall()

    tasks = []
    for row in rows:
      task = Task(id=row[0], name=row[1], user_id=row[2], description=row[3], complete=row[4])
      tasks.append(task)

    return tasks

  @staticmethod
  def get_task_in_progress(user_id, task_name):
    with current_app.db.connection() as conn:
      with conn.cursor() as cur:
        row = cur.execute("""
                            SELECT id, name, user_id, description, complete
                            FROM tasks
                            WHERE user_id = %s AND complete = FALSE AND name = %s
                          """, (user_id, task_name)).fetchone()

    if row is None:
      return None

    return Task(id=row[0], name=row[1], user_id=row[2], description=row[3], complete=row[4])

  @staticmethod
  def post_count(conn, user_id):
    with conn.cursor() as cur:
      cur.execute("""
                    SELECT COUNT(*)
                    FROM posts
                    WHERE user_id = %s
                  """, (user_id,))

      return cur.fetchone()[0]

  @staticmethod
  def all_posts(conn, user_id):
    with conn.cursor() as cur:
      rows = cur.execute("""
                            SELECT body, timestamp
                            FROM posts
                            WHERE user_id = %s
                            ORDER BY timestamp ASC
                        """, (user_id,)).fetchall()

    posts = []
    for row in rows:
      posts.append(Post(body=row[0], timestamp=row[1]))

    return posts

  @staticmethod
  def paginated_posts(conn, user_id, page_idx, posts_per_page):
    offset = (page_idx - 1) * posts_per_page

    with conn.cursor() as cur:
      rows = cur.execute("""
                          SELECT posts.id, posts.body, posts.timestamp, posts.language, posts.user_id, users.username, users.email 
                            FROM posts
                            JOIN users ON posts.user_id = users.id
                          WHERE users.id = %s
                          ORDER BY posts.timestamp DESC
                          LIMIT %s
                          OFFSET %s
                         """, (user_id, posts_per_page + 1, offset)).fetchall()

    has_next = len(rows) > posts_per_page
    has_prev = offset > 0

    results = []
    for i in range(min(posts_per_page, len(rows))):
      row = rows[i]
      author = User(id=row[4], username=row[5], email=row[6])
      post = Post(id=row[0], body=row[1], timestamp=row[2], language=row[3], author=author)
      results.append(post)

    return results, has_next, page_idx + 1, has_prev, page_idx - 1

  @staticmethod
  def following_posts(conn, user_id, page_idx, posts_per_page):
    offset = (page_idx - 1) * posts_per_page

    with conn.cursor() as cur:
      rows = cur.execute("""
                            SELECT posts.id, posts.body, posts.timestamp, posts.language, posts.user_id, users.username, users.email FROM posts
                              JOIN users ON posts.user_id = users.id
                              JOIN followers ON followers.followed_id = users.id
                              WHERE followers.follower_id = %s

                            UNION

                            SELECT posts.id, posts.body, posts.timestamp, posts.language, posts.user_id, users.username, users.email FROM posts
                              JOIN users ON posts.user_id = users.id
                              WHERE users.id = %s

                            ORDER BY timestamp DESC
                            LIMIT %s
                            OFFSET %s
                          """, (user_id, user_id, posts_per_page + 1, offset)).fetchall()

    has_next = len(rows) > posts_per_page
    has_prev = offset > 0

    results = []
    for i in range(min(posts_per_page, len(rows))):
      row = rows[i]
      author = User(id=row[4], username=row[5], email=row[6])
      post = Post(id=row[0], body=row[1], timestamp=row[2], language=row[3], author=author)
      results.append(post)

    return results, has_next, page_idx + 1, has_prev, page_idx - 1

  @staticmethod
  def messages_received(conn, user_id, page_idx, posts_per_page):
    offset = (page_idx - 1) * posts_per_page

    with conn.cursor() as cur:
      rows = cur.execute("""
                            SELECT messages.id, messages.body, messages.timestamp, users.id, users.username, users.email 
                              FROM messages
                              JOIN users ON messages.sender_id = users.id
                            WHERE messages.recipient_id = %s
                            ORDER BY messages.timestamp DESC
                            LIMIT %s
                            OFFSET %s
                        """, (user_id, posts_per_page + 1, offset)).fetchall()

    has_next = len(rows) > posts_per_page
    has_prev = offset > 0

    results = []
    for i in range(min(posts_per_page, len(rows))):
      row = rows[i]
      author = User(id=row[3], username=row[4], email=row[5])
      message = Message(id=row[0], body=row[1], timestamp=row[2], author=author)
      results.append(message)

    return results, has_next, page_idx + 1, has_prev, page_idx - 1

  @staticmethod
  def update_last_message_read_time(conn, user_id, new_timestamp):
    with conn.cursor() as cur:
      cur.execute("""
                    UPDATE users SET last_message_read_time = %s
                    WHERE id = %s
                  """, (new_timestamp, user_id))

  @staticmethod
  def notifications(conn, user_id, since):
    with conn.cursor() as cur:
      rows = cur.execute("""
      SELECT name, payload_json, timestamp
        FROM notifications
        WHERE user_id = %s AND timestamp > %s
      """, (user_id, since)).fetchall()

    notifications = []

    for row in rows:
      n = Notification(name=row[0], payload_json=row[1], timestamp=row[2])
      notifications.append(n)

    return notifications

  @staticmethod
  def get_reset_password_token(user_id, expires_in=600):
      return jwt.encode(
          {'reset_password': user_id, 'exp': time() + expires_in},
          current_app.config['SECRET_KEY'], algorithm='HS256')

  @staticmethod
  def verify_reset_password_token(conn, token):
      try:
          id = jwt.decode(token, current_app.config['SECRET_KEY'],
                          algorithms=['HS256'])['reset_password']
      except:
          return

      return User.by_id(conn, id)

@dataclass
class Message:
  id: int | None = None
  body: str | None = None
  timestamp: datetime | None = None
  author: User | None = None #sender

  @staticmethod
  def create(conn, sender_id, recipient_id, body):
    #TODO should make timestamp insertion automatic on database server side
    with conn.cursor() as cur:
      cur.execute("""
                    INSERT INTO messages(sender_id, recipient_id, body, timestamp) 
                    VALUES(%s, %s, %s, %s)
                  """, (sender_id, recipient_id, body, datetime.now(timezone.utc)))

@dataclass
class Notification:
  id: int | None = None
  name: str | None = None
  user_id: int | None = None
  timestamp: float | None = None
  payload_json: dict[str, Any] | None = None

  @staticmethod
  def create(conn, name, user_id, payload_json):
    #TODO should make timestamp insertion automatic on database server side
    with conn.cursor() as cur:
      cur.execute("""
                    INSERT INTO notifications(name, user_id, timestamp, payload_json) 
                    VALUES(%s, %s, %s, %s)
                  """, (name, user_id, time(), payload_json))

  @staticmethod
  def delete_by_name(conn, ntf_name, user_id):
    #TODO should make timestamp insertion automatic on database server side
    with conn.cursor() as cur:
      cur.execute("""
                    DELETE FROM notifications
                    WHERE name = %s AND user_id = %s
                  """, (ntf_name, user_id))

@dataclass
class Post:
  id: int | None = None
  body: str | None = None
  timestamp: datetime | None = None
  author: User | None = None
  language: str | None = None 

  @staticmethod
  def create(conn, body, user_id, language):
      #TODO should make timestamp insertion automatic on database server side
    with conn.cursor() as cur:
      cur.execute("""
                    INSERT INTO posts(body, user_id, timestamp, language) 
                    VALUES(%s, %s, %s, %s)
                  """, (body, user_id, datetime.now(timezone.utc), language))


  @staticmethod
  def recent_posts(conn, page_idx, posts_per_page):
    offset = (page_idx - 1) * posts_per_page

    with conn.cursor() as cur:
      rows = cur.execute("""
                          SELECT posts.id, posts.body, posts.timestamp, posts.language, posts.user_id, users.username, users.email 
                            FROM posts
                            JOIN users ON posts.user_id = users.id
                          ORDER BY posts.timestamp DESC
                          LIMIT %s
                          OFFSET %s
                        """, (posts_per_page + 1, offset)).fetchall()

    has_next = len(rows) > posts_per_page
    has_prev = offset > 0

    results = []
    for i in range(min(posts_per_page, len(rows))):
      row = rows[i]
      author = User(id=row[4], username=row[5], email=row[6])
      post = Post(id=row[0], body=row[1], timestamp=row[2], language=row[3], author=author)
      results.append(post)

    return results, has_next, page_idx + 1, has_prev, page_idx - 1

