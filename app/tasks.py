import json
import sys
import time
from flask import render_template
from rq import get_current_job
from app import create_app, db
from app.models import User, Task
from app.email import send_email

app = create_app()
app.app_context().push()

def _set_task_progress(progress):
    job = get_current_job()
    if job:
        job.meta['progress'] = progress
        job.save_meta()

        with app.db.connection() as conn:
          task = Task.by_id(conn, job.id)
          User.add_notification(conn, task.user_id, 'task_progress', {'task_id': job.id,
                                                                 'progress': progress})

          if progress >= 100:
            Task.update_complete(conn, job.id, True)

def export_posts(user_id):
    try:
        _set_task_progress(0)
        data = []
        i = 0

        with app.db.connection() as conn:
          total_posts = User.post_count(conn, user_id)
          all_posts = User.all_posts(conn, user_id)

        for post in all_posts:
            data.append({'body': post.body,
                         'timestamp': post.timestamp})
            time.sleep(1)
            i += 1
            _set_task_progress(100 * i // total_posts)

        # send email with data to user - not currently working.
        # Need to configure email/use email service like SendGrid/use SMTP debugging server
        '''
        send_email(
            '[Microblog] Your blog posts',
            sender=app.config['ADMINS'][0], recipients=[user.email],
            text_body=render_template('email/export_posts.txt', user=user),
            html_body=render_template('email/export_posts.html', user=user),
            attachments=[('posts.json', 'application/json',
                          json.dumps({'posts': data}, indent=4))],
            sync=True)
        '''
    except Exception:
        _set_task_progress(100)
        app.logger.error('Unhandled exception', exc_info=sys.exc_info())
    finally:
        _set_task_progress(100)
