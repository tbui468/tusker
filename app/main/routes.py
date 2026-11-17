from flask import render_template, flash, redirect, url_for, request, g, current_app
from app.main.forms import EditProfileForm, EmptyForm, PostForm, MessageForm
from app.errors.handlers import not_found_error
from flask_login import current_user, login_user, logout_user, login_required
from app.main import bp
from app.models import Post, User, Message, Task
from urllib.parse import urlsplit
from datetime import datetime, timezone
from flask_babel import _, get_locale
from langdetect import detect, LangDetectException
from app.translate import translate

#TODO may want to inject User/Task here also since most templates require them
@bp.context_processor
def inject_globals():
  if current_user.is_authenticated:
    with current_app.db.connection() as conn:
      return { "unread_message_count": User.unread_message_count(conn, current_user.id) }

  return { "unread_message_count": 0 }

@bp.route('/', methods=['GET', 'POST'])
@bp.route('/index', methods=['GET', 'POST'])
@login_required
def index():
    form = PostForm()
    if form.validate_on_submit():
        try:
          language = detect(form.post.data)
        except LangDetectException:
          language = ''
  
        with current_app.db.connection() as conn:
          Post.create(conn, form.post.data, current_user.id, language)
        flash(_('Your post is now live!'))
        return redirect(url_for('main.index'))

    page = request.args.get('page', 1, type=int)
    with current_app.db.connection() as conn:
      items, has_next, next_num, has_prev, prev_num = User.following_posts(conn, current_user.id, page, current_app.config['POSTS_PER_PAGE'])

    next_url = url_for('main.index', page=next_num) \
        if has_next else None
    prev_url = url_for('main.index', page=prev_num) \
        if has_prev else None
    return render_template('main/index.html', title='Home', form=form,
                           posts=items, next_url=next_url,
                           prev_url=prev_url, User=User, Task=Task)

@bp.route('/explore')
@login_required
def explore():
    page = request.args.get('page', 1, type=int)
    with current_app.db.connection() as conn:
      items, has_next, next_num, has_prev, prev_num = Post.recent_posts(conn, page, current_app.config['POSTS_PER_PAGE'])

    next_url = url_for('main.explore', page=next_num) \
        if has_next else None
    prev_url = url_for('main.explore', page=prev_num) \
        if has_prev else None
    return render_template('main/index.html', title='Explore',
                           posts=items, next_url=next_url,
                           prev_url=prev_url, User=User, Task=Task)

@bp.route('/user/<username>')
@login_required
def user(username):
    page = request.args.get('page', 1, type=int)

    with current_app.db.connection() as conn:
      user = User.by_username(conn, username)
      if not user:
        return not_found_error("username not found")

      items, has_next, next_num, has_prev, prev_num = User.paginated_posts(conn, user.id, page, current_app.config['POSTS_PER_PAGE'])

      followers_count = User.followers_count(conn, user.id)
      following_count = User.following_count(conn, user.id)
      is_following = User.is_following(conn, current_user.id, user.id)

    next_url = url_for('main.user', username=user.username, page=next_num) \
        if has_next else None
    prev_url = url_for('main.user', username=user.username, page=prev_num) \
        if has_prev else None

    form = EmptyForm()
    return render_template('main/user.html', user=user, posts=items,
                           next_url=next_url, prev_url=prev_url, form=form, User=User, Task=Task,
                           followers_count=followers_count, following_count=following_count, is_following=is_following)

@bp.route('/user/<username>/popup')
@login_required
def user_popup(username):
    with current_app.db.connection() as conn:
      user = User.by_username(conn, username)
      if not user:
        return not_found_error("username not found")

      followers_count = User.followers_count(conn, user.id)
      following_count = User.following_count(conn, user.id)
      is_following = User.is_following(conn, current_user.id, user.id)

    form = EmptyForm()
    return render_template('main/user_popup.html', user=user, form=form, User=User, 
                           followers_count=followers_count, following_count=following_count, is_following=is_following)

@bp.before_request
def before_request():
    if current_user.is_authenticated:
      with current_app.db.connection() as conn:
        User.update_last_seen(conn, current_user.id, datetime.now(timezone.utc))
    g.locale = str(get_locale())

@bp.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    form = EditProfileForm(current_user.username)
    if form.validate_on_submit():
        with current_app.db.connection() as conn:
          User.update_username(conn, current_user.id, form.username.data)
          User.update_about_me(conn, current_user.id, form.about_me.data)
        flash('Your changes have been saved.')
        return redirect(url_for('main.edit_profile'))
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.about_me.data = current_user.about_me
    return render_template('main/edit_profile.html', title='Edit Profile',
                           form=form, User=User, Task=Task)

@bp.route('/follow/<username>', methods=['POST'])
@login_required
def follow(username):
  form = EmptyForm()
  if form.validate_on_submit():
    with current_app.db.connection() as conn:
      user  = User.by_username(conn, username)
      if not user:
          flash(_('User %(username)s not found.', username=username))
          return redirect(url_for('main.index'))
      if user == current_user:
          flash('You cannot follow yourself!')
          return redirect(url_for('main.user', username=username))
      User.follow(conn, current_user.id, user.id)

    flash(f'You are following {username}!')
    return redirect(url_for('main.user', username=username))
  else:
    return redirect(url_for('main.index'))


@bp.route('/unfollow/<username>', methods=['POST'])
@login_required
def unfollow(username):
  form = EmptyForm()
  if form.validate_on_submit():
    with current_app.db.connection() as conn:
      user = User.by_username(conn, username)
      if not user:
          flash(f'User {username} not found.')
          return redirect(url_for('main.index'))
      if user == current_user:
          flash('You cannot unfollow yourself!')
          return redirect(url_for('main.user', username=username))
      User.unfollow(conn, current_user.id, user.id)

    flash(f'You are not following {username}.')
    return redirect(url_for('main.user', username=username))
  else:
    return redirect(url_for('main.index'))


@bp.route('/translate', methods=['POST'])
@login_required
def translate_text():
    data = request.get_json()
    return {'text': translate(data['text'],
                              data['source_language'],
                              data['dest_language'])}

@bp.route('/send_message/<recipient>', methods=['GET', 'POST'])
@login_required
def send_message(recipient):
  with current_app.db.connection() as conn:
    user = User.by_username(conn, recipient)
    if not user:
      return not_found_error("username not found")

    form = MessageForm()
    if form.validate_on_submit():
      Message.create(conn, current_user.id, user.id, form.message.data)
      User.add_notification(conn, user.id, 'unread_message_count', User.unread_message_count(conn, user.id))
      flash(_('Your message has been sent.'))
      return redirect(url_for('main.user', username=recipient))

  return render_template('send_message.html', title=_('Send Message'),
                         form=form, recipient=recipient, User=User, Task=Task)

@bp.route('/messages')
@login_required
def messages():
    page = request.args.get('page', 1, type=int)

    with current_app.db.connection() as conn:
      User.update_last_message_read_time(conn, current_user.id, datetime.now(timezone.utc))
      User.add_notification(conn, current_user.id, 'unread_message_count', 0)
      items, has_next, next_num, has_prev, prev_num = User.messages_received(conn, current_user.id, page, current_app.config['POSTS_PER_PAGE'])

    next_url = url_for('main.messages', page=next_num) \
        if has_next else None
    prev_url = url_for('main.messages', page=prev_num) \
        if has_prev else None
    return render_template('main/messages.html', 
                           messages=items, next_url=next_url,
                           prev_url=prev_url, User=User, Task=Task)


@bp.route('/notifications')
@login_required
def notifications():
    since = request.args.get('since', 0.0, type=float)

    with current_app.db.connection() as conn:
      notifications = User.notifications(conn, current_user.id, since)

    return [{
        'name': n.name,
        'data': n.payload_json,
        'timestamp': n.timestamp
    } for n in notifications]

@bp.route('/export_posts')
@login_required
def export_posts():
    if User.get_task_in_progress(current_user.id, 'export_posts'):
        flash(_('An export task is currently in progress'))
    else:
      with current_app.db.connection() as conn:
        User.launch_task(conn, current_user.id, 'export_posts', _('Exporting posts...'))

    return redirect(url_for('main.user', username=current_user.username))
