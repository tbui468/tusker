from app import create_app
from app.models import User, Post, Message, Notification, Task

app = create_app()

@app.shell_context_processor
def make_shell_context():
    return {'User': User, 'Post': Post, 'Message': Message, 'Notification': Notification, 'Task': Task}


