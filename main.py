from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from markupsafe import Markup
import os
import base64
from datetime import datetime
from sqlalchemy import inspect, text
import hashlib
try:
    from markdown import markdown as md_to_html
except Exception:
    md_to_html = None
try:
    import pygments  # optional, used by markdown codehilite
    CODEHILITE_AVAILABLE = True
except Exception:
    CODEHILITE_AVAILABLE = False

app = Flask(__name__)
app.config['SECRET_KEY'] = 'a_secret_key'
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'database.db')

db = SQLAlchemy(app)
migrate = Migrate(app, db)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


def ensure_publish_at_column():
    try:
        insp = inspect(db.engine)
        tables = insp.get_table_names()
        if 'post' not in tables:
            return False
        cols = [c['name'] for c in insp.get_columns('post')]
        if 'publish_at' in cols:
            return True
        # add column (SQLite supports ADD COLUMN)
        with db.engine.connect() as conn:
            conn.execute(text('ALTER TABLE post ADD COLUMN publish_at DATETIME'))
        return True
    except Exception as e:
        app.logger.error('ensure_publish_at_column error: %s', e)
        return False

def ensure_avatar_column():
    try:
        insp = inspect(db.engine)
        tables = insp.get_table_names()
        if 'user' not in tables:
            return False
        cols = [c['name'] for c in insp.get_columns('user')]
        if 'avatar_filename' in cols:
            return True
        # add column for avatar uploads
        with db.engine.connect() as conn:
            conn.execute(text('ALTER TABLE user ADD COLUMN avatar_filename VARCHAR(300)'))
        return True
    except Exception as e:
        app.logger.error('ensure_avatar_column error: %s', e)
        return False


def ensure_bio_column():
    try:
        insp = inspect(db.engine)
        tables = insp.get_table_names()
        if 'user' not in tables:
            return False
        cols = [c['name'] for c in insp.get_columns('user')]
        if 'bio' in cols:
            return True
        # add bio column
        with db.engine.connect() as conn:
            conn.execute(text('ALTER TABLE user ADD COLUMN bio VARCHAR(500)'))
        return True
    except Exception as e:
        app.logger.error('ensure_bio_column error: %s', e)
        return False

def ensure_bio_column():
    try:
        insp = inspect(db.engine)
        tables = insp.get_table_names()
        if 'user' not in tables:
            return False
        cols = [c['name'] for c in insp.get_columns('user')]
        if 'bio' in cols:
            return True
        # add column for user bio
        with db.engine.connect() as conn:
            conn.execute(text('ALTER TABLE user ADD COLUMN bio VARCHAR(500)'))
            conn.commit()
        return True
    except Exception as e:
        app.logger.error('ensure_bio_column error: %s', e)
        return False


# Some Flask installs/environments may not expose `before_first_request` at import time.
# Run schema fix at startup instead (called below in __main__ before running the app).


# Helper filter: show a friendly name (mask email addresses)
def display_name(value):
    if not value:
        return ''
    try:
        s = str(value)
    except Exception:
        return ''
    if '@' in s:
        return s.split('@')[0]
    return s

app.jinja_env.filters['display_name'] = display_name

# Markdown rendering filter
def render_markdown(text):
    if not text:
        return ''
    if md_to_html:
        exts = ['fenced_code']
        if CODEHILITE_AVAILABLE:
            exts.append('codehilite')
        return Markup(md_to_html(text, extensions=exts))
    return Markup('<pre>' + Markup.escape(text) + '</pre>')

app.jinja_env.filters['md'] = render_markdown

# Uploads
UPLOAD_FOLDER = os.path.join(basedir, 'static', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
AVATAR_FOLDER = os.path.join(UPLOAD_FOLDER, 'avatars')
os.makedirs(AVATAR_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
ALLOWED_EXT = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXT

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    avatar_filename = db.Column(db.String(300), nullable=True)
    bio = db.Column(db.String(500), nullable=True)  # User bio/description
    dark_mode = db.Column(db.Boolean, default=False)  # Dark mode preference
    posts = db.relationship('Post', backref='author', lazy=True)
    
    # Followers - users who follow this user
    followers = db.relationship(
        'User', 
        secondary='follow',
        primaryjoin='User.id==Follow.following_id',
        secondaryjoin='User.id==Follow.follower_id',
        backref=db.backref('following_users', lazy='dynamic'),
        lazy='dynamic'
    )
    # Likes, bookmarks, and views
    likes = db.relationship('Like', backref='user', lazy=True, cascade='all, delete-orphan')
    bookmarks = db.relationship('Bookmark', backref='user', lazy=True, cascade='all, delete-orphan')
    post_views = db.relationship('PostView', backref='user', lazy=True, cascade='all, delete-orphan')
    # Notifications and messages
    notifications = db.relationship('Notification', foreign_keys='Notification.user_id', backref='receiver', lazy=True, cascade='all, delete-orphan')
    sent_messages = db.relationship('Message', foreign_keys='Message.sender_id', backref='sent_by', lazy=True, cascade='all, delete-orphan')
    received_messages = db.relationship('Message', foreign_keys='Message.recipient_id', backref='received_by', lazy=True, cascade='all, delete-orphan')
    # Block relationships
    blocked_by = db.relationship('Block', foreign_keys='Block.blocked_id', backref='user_blocked', lazy=True, cascade='all, delete-orphan')
    blocks = db.relationship('Block', foreign_keys='Block.blocker_id', backref='user_blocking', lazy=True, cascade='all, delete-orphan')


class Follow(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    follower_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    following_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    __table_args__ = (db.UniqueConstraint('follower_id', 'following_id', name='unique_follow'),)


class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    image_data = db.Column(db.Text, nullable=True)
    image_filename = db.Column(db.String(300), nullable=True)
    tags = db.Column(db.String(250), nullable=True)
    draft = db.Column(db.Boolean, default=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    published_at = db.Column(db.DateTime, nullable=True)
    publish_at = db.Column(db.DateTime, nullable=True)
    likes = db.relationship('Like', backref='post', lazy=True, cascade='all, delete-orphan')
    views = db.relationship('PostView', backref='post', lazy=True, cascade='all, delete-orphan')


class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    parent_comment_id = db.Column(db.Integer, db.ForeignKey('comment.id'), nullable=True)  # For replies
    body = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    replies = db.relationship('Comment', backref=db.backref('parent', remote_side=[id]), lazy=True)


class Like(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    __table_args__ = (db.UniqueConstraint('post_id', 'user_id', name='unique_post_like'),)


class Bookmark(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    post = db.relationship('Post', backref='bookmarked_by')
    __table_args__ = (db.UniqueConstraint('post_id', 'user_id', name='unique_bookmark'),)


class PostView(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)  # Allow anonymous views
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    __table_args__ = (db.UniqueConstraint('post_id', 'user_id', name='unique_post_view'),)


class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    actor_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # Who triggered it
    type = db.Column(db.String(20), nullable=False)  # 'like', 'comment', 'follow', 'reply'
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=True)
    comment_id = db.Column(db.Integer, db.ForeignKey('comment.id'), nullable=True)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    actor = db.relationship('User', foreign_keys=[actor_id])


class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    recipient_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    body = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    sender = db.relationship('User', foreign_keys=[sender_id], overlaps='sent_messages,sent_by')
    recipient = db.relationship('User', foreign_keys=[recipient_id], overlaps='received_messages,received_by')


class Block(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    blocker_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # User who blocked
    blocked_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)   # User who is blocked
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    blocker = db.relationship('User', foreign_keys=[blocker_id], overlaps='blocks,user_blocking')
    blocked_user = db.relationship('User', foreign_keys=[blocked_id], overlaps='blocked_by,user_blocked')
    __table_args__ = (db.UniqueConstraint('blocker_id', 'blocked_id', name='unique_block'),)


class Collection(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(300), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    items = db.relationship('CollectionItem', backref='collection', lazy=True, cascade='all, delete-orphan')
    user = db.relationship('User', backref='collections')


class CollectionItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    collection_id = db.Column(db.Integer, db.ForeignKey('collection.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    post = db.relationship('Post')
    __table_args__ = (db.UniqueConstraint('collection_id', 'post_id', name='unique_collection_item'),)

# attach comments relationship to Post and user relationship for comments
Post.comments = db.relationship('Comment', backref='post', lazy=True, order_by='Comment.created_at')
User.comments = db.relationship('Comment', backref='author', lazy=True)


@app.context_processor
def utility_processor():
    def avatar_url(user, size=48):
        # prefer uploaded avatar if present
        try:
            if hasattr(user, 'avatar_filename') and getattr(user, 'avatar_filename'):
                return url_for('static', filename='uploads/avatars/' + getattr(user, 'avatar_filename'))
        except Exception:
            pass
        val = ''
        if hasattr(user, 'email') and getattr(user, 'email'):
            val = getattr(user, 'email').strip().lower()
        elif hasattr(user, 'username') and getattr(user, 'username'):
            val = getattr(user, 'username').strip().lower()
        h = hashlib.md5(val.encode('utf-8')).hexdigest()
        return f"https://www.gravatar.com/avatar/{h}?d=identicon&s={size}"
    return dict(avatar_url=avatar_url)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
@login_required
def index():
    feed_type = request.args.get('feed', 'for_you')  # 'for_you' or 'following'
    page = request.args.get('page', 1, type=int)
    per_page = 8
    now = datetime.utcnow()
    
    if feed_type == 'following':
        # Show only posts from users being followed
        following_user_ids = [user.id for user in current_user.following_users]
        if not following_user_ids:
            pagination = db.paginate(db.select(Post).where(False), page=page, per_page=per_page, error_out=False)
        else:
            pagination = Post.query.filter(
                Post.user_id.in_(following_user_ids) &
                (Post.draft == False) &
                ((Post.publish_at == None) | (Post.publish_at <= now))
            ).order_by(Post.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
    else:
        # Show all posts - 'for_you' feed
        pagination = Post.query.filter(
            (Post.draft == False) &
            ((Post.publish_at == None) | (Post.publish_at <= now))
        ).order_by(Post.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
    
    return render_template('index.html', posts=pagination, pagination_endpoint='index', pagination_args={}, feed_type=feed_type)

@app.route('/my_account', methods=['GET', 'POST'])
@login_required
def my_account():
    if request.method == 'POST':
        # handle avatar upload
        file = request.files.get('avatar')
        bio = request.form.get('bio', '').strip()[:500]
        
        if bio:
            current_user.bio = bio
        
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            # prefix with user id to avoid collisions
            filename = f"u{current_user.id}_" + filename
            save_path = os.path.join(UPLOAD_FOLDER, 'avatars', filename)
            file.save(save_path)
            current_user.avatar_filename = filename
            flash('Profile updated.')
        elif bio:
            flash('Bio updated.')
        else:
            flash('No changes made.')
        
        db.session.commit()
        return redirect(url_for('my_account'))

    user_posts = Post.query.filter_by(user_id=current_user.id).order_by(Post.created_at.desc()).all()
    return render_template('my_account.html', posts=user_posts)

@app.route('/create_post', methods=['GET', 'POST'])
@login_required
def create_post():
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        content = request.form.get('content', '').strip()
        
        # Validate required fields
        if not title:
            flash('Please enter a post title.', 'error')
            return render_template('create_post.html')
        if not content:
            flash('Please enter post content.', 'error')
            return render_template('create_post.html')
        
        file = request.files.get('image')
        tags = request.form.get('tags', '').strip()
        # Draft option removed - all posts are published by default
        draft = False
        publish_at_str = request.form.get('publish_at')
        publish_at_dt = None
        if publish_at_str:
            try:
                publish_at_dt = datetime.fromisoformat(publish_at_str)
            except Exception:
                publish_at_dt = None

        image_filename = None
        image_base64 = None
        if file and file.filename and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(save_path)
            image_filename = filename
        elif file and file.filename:
            image_base64 = base64.b64encode(file.read()).decode('utf-8')

        now = datetime.utcnow()
        
        # All posts are published - only scheduled posts are temporarily marked as draft
        final_draft = False
        published_at_value = now  # Always publish immediately
        
        if publish_at_dt and publish_at_dt > now:
            # Scheduled for future - save as draft temporarily
            final_draft = True
            published_at_value = None  # Not published yet
        # else: publish now (final_draft is False, published_at_value is now)
        
        new_post = Post(
            title=title, 
            content=content, 
            image_data=image_base64, 
            image_filename=image_filename, 
            tags=tags, 
            draft=final_draft, 
            user_id=current_user.id, 
            created_at=now,
            published_at=published_at_value,
            publish_at=publish_at_dt
        )
        db.session.add(new_post)
        db.session.commit()
        
        if final_draft:
            flash('Post scheduled! It will be published at the scheduled time.', 'success')
        else:
            flash('Post published successfully!', 'success')
        return redirect(url_for('index'))
    return render_template('create_post.html')


@app.route('/edit_post/<int:post_id>', methods=['GET', 'POST'])
@login_required
def edit_post(post_id):
    post = Post.query.get_or_404(post_id)
    if post.user_id != current_user.id:
        flash('You are not authorized to edit this post.')
        return redirect(url_for('index'))

    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        file = request.files.get('image')
        tags = request.form.get('tags', '')
        # Draft option removed - all posts are published by default
        
        if title:
            post.title = title
        if content:
            post.content = content
        post.tags = tags
        
        # handle publish_at scheduling
        publish_at_str = request.form.get('publish_at')
        publish_at_dt = None
        if publish_at_str:
            try:
                publish_at_dt = datetime.fromisoformat(publish_at_str)
            except Exception:
                publish_at_dt = None
        post.publish_at = publish_at_dt
        
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(save_path)
            post.image_filename = filename
        elif file:
            post.image_data = base64.b64encode(file.read()).decode('utf-8')
        
        # All posts are published - only scheduled posts are temporarily marked as draft
        now = datetime.utcnow()
        if publish_at_dt and publish_at_dt > now:
            post.draft = True
            post.published_at = None
        else:
            post.draft = False
            post.published_at = now
        
        db.session.commit()
        flash('Post updated successfully.', 'success')
        return redirect(url_for('index'))

    return render_template('edit_post.html', post=post)


@app.route('/delete_post/<int:post_id>', methods=['POST'])
@login_required
def delete_post(post_id):
    post = Post.query.get_or_404(post_id)
    if post.user_id != current_user.id:
        flash('You are not authorized to delete this post.', 'error')
        return redirect(url_for('index'))
    
    try:
        # Delete all comments associated with this post first
        Comment.query.filter_by(post_id=post_id).delete()
        # Then delete the post
        db.session.delete(post)
        db.session.commit()
        flash('Post deleted successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting post: {str(e)}', 'error')
    
    return redirect(url_for('my_account'))


@app.route('/search')
def search():
    q = request.args.get('q', '')
    if not q:
        return redirect(url_for('index'))
    page = request.args.get('page', 1, type=int)
    per_page = 8
    now = datetime.utcnow()
    pagination = Post.query.filter((Post.title.ilike(f"%{q}%")) | (Post.content.ilike(f"%{q}%"))).filter(Post.draft==False).filter((Post.publish_at==None) | (Post.publish_at <= now)).order_by(Post.published_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
    return render_template('index.html', posts=pagination, pagination_endpoint='search', pagination_args={'q': q})


@app.route('/tag/<tag>')
def posts_by_tag(tag):
    page = request.args.get('page', 1, type=int)
    per_page = 8
    now = datetime.utcnow()
    pagination = Post.query.filter(Post.tags.ilike(f"%{tag}%"), Post.draft==False).filter((Post.publish_at==None) | (Post.publish_at <= now)).order_by(Post.published_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
    return render_template('index.html', posts=pagination, pagination_endpoint='posts_by_tag', pagination_args={'tag': tag})

@app.route('/api/tags')
def api_tags():
    """Return top tags with counts for tag cloud."""
    try:
        now = datetime.utcnow()
        posts = Post.query.filter(Post.draft==False).filter((Post.publish_at==None) | (Post.publish_at <= now)).all()
        tag_counts = {}
        for post in posts:
            if post.tags:
                for tag in post.tags.split(','):
                    t = tag.strip()
                    if t:
                        tag_counts[t] = tag_counts.get(t, 0) + 1
        # return top 15 tags sorted by count
        sorted_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:15]
        return jsonify({'tags': [{'name': t, 'count': c} for t, c in sorted_tags]})
    except Exception as e:
        return jsonify({'tags': []})



@app.route('/comment/<int:post_id>', methods=['POST'])
@login_required
def create_comment(post_id):
    post = Post.query.get_or_404(post_id)
    body = request.form.get('body', '').strip()
    if not body:
        flash('Comment cannot be empty.')
        return redirect(url_for('index'))
    comment = Comment(post_id=post.id, user_id=current_user.id, body=body)
    db.session.add(comment)
    db.session.commit()
    return redirect(request.referrer or url_for('index'))


@app.route('/delete_comment/<int:comment_id>', methods=['POST'])
@login_required
def delete_comment(comment_id):
    comment = Comment.query.get_or_404(comment_id)
    post = Post.query.get(comment.post_id)
    if comment.user_id != current_user.id and post.user_id != current_user.id:
        flash('Not authorized to delete this comment.')
        return redirect(request.referrer or url_for('index'))
    db.session.delete(comment)
    db.session.commit()
    flash('Comment deleted.')
    return redirect(request.referrer or url_for('index'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        
        if user:
            flash('This username is already taken. Please change your username.')
            return redirect(url_for('register'))
            
        if len(password) != 8:
            flash('Password must be exactly 8 characters long.')
            return redirect(url_for('register'))
            
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        new_user = User(username=username, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('register.html')


@app.route('/check_username')
def check_username():
    username = request.args.get('username', '')
    exists = False
    if username:
        exists = User.query.filter_by(username=username).first() is not None
    return jsonify({'exists': exists})

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password.')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

# Debug route to check database posts
@app.route('/debug/fix-posts')
def debug_fix_posts():
    """Fix posts that are marked as draft but should be published"""
    if not app.debug:
        return "Not available", 404
    
    try:
        # Find all non-draft posts with NULL published_at
        posts_to_fix = Post.query.filter(
            (Post.draft == False) & (Post.published_at == None)
        ).all()
        
        count = 0
        for post in posts_to_fix:
            post.published_at = post.created_at
            count += 1
        
        db.session.commit()
        
        output = f"<h1>✓ Fixed {count} posts</h1>"
        output += f"<p>Posts that were not marked as draft but had no published date now have their published_at set to created_at.</p>"
        output += f"<hr><p><a href='/'>Go to Home</a> | <a href='/debug/posts'>View all posts</a></p>"
        return output
    except Exception as e:
        db.session.rollback()
        return f"<h1>Error: {str(e)}</h1>"

@app.route('/debug/publish-all')
def debug_publish_all():
    """Publish all draft posts immediately"""
    if not app.debug:
        return "Not available", 404
    
    try:
        now = datetime.utcnow()
        # Update all draft posts to be published
        draft_posts = Post.query.filter(Post.draft == True).all()
        
        count = 0
        for post in draft_posts:
            post.draft = False
            post.published_at = post.created_at
            count += 1
        
        db.session.commit()
        
        output = f"<h1>✓ Published {count} draft posts</h1>"
        output += f"<p>All draft posts have been converted to published posts.</p>"
        output += f"<hr><p><a href='/'>Go to Home</a> | <a href='/debug/posts'>View all posts</a></p>"
        return output
    except Exception as e:
        db.session.rollback()
        return f"<h1>Error: {str(e)}</h1>"


@app.route('/follow/<int:user_id>', methods=['POST'])
@login_required
def follow_user(user_id):
    user_to_follow = User.query.get_or_404(user_id)
    
    if user_to_follow.id == current_user.id:
        return jsonify({'error': 'Cannot follow yourself'}), 400
    
    existing = Follow.query.filter_by(
        follower_id=current_user.id,
        following_id=user_id
    ).first()
    
    if existing:
        return jsonify({'error': 'Already following'}), 400
    
    new_follow = Follow(follower_id=current_user.id, following_id=user_id)
    db.session.add(new_follow)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'follower_count': user_to_follow.followers.count()
    })


@app.route('/unfollow/<int:user_id>', methods=['POST'])
@login_required
def unfollow_user(user_id):
    user_to_unfollow = User.query.get_or_404(user_id)
    
    follow = Follow.query.filter_by(
        follower_id=current_user.id,
        following_id=user_id
    ).first_or_404()
    
    db.session.delete(follow)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'follower_count': user_to_unfollow.followers.count()
    })


@app.route('/api/is_following/<int:user_id>')
@login_required
def is_following(user_id):
    following = Follow.query.filter_by(
        follower_id=current_user.id,
        following_id=user_id
    ).first() is not None
    
    return jsonify({'following': following})


@app.route('/api/like/<int:post_id>', methods=['POST'])
@login_required
def like_post(post_id):
    post = Post.query.get_or_404(post_id)
    
    existing_like = Like.query.filter_by(
        post_id=post_id,
        user_id=current_user.id
    ).first()
    
    if existing_like:
        return jsonify({'error': 'Already liked'}), 400
    
    new_like = Like(post_id=post_id, user_id=current_user.id)
    db.session.add(new_like)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'like_count': len(post.likes)
    })


@app.route('/api/unlike/<int:post_id>', methods=['POST'])
@login_required
def unlike_post(post_id):
    post = Post.query.get_or_404(post_id)
    
    like = Like.query.filter_by(
        post_id=post_id,
        user_id=current_user.id
    ).first_or_404()
    
    db.session.delete(like)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'like_count': len(post.likes)
    })


@app.route('/api/is_liked/<int:post_id>')
@login_required
def is_liked(post_id):
    liked = Like.query.filter_by(
        post_id=post_id,
        user_id=current_user.id
    ).first() is not None
    
    post = Post.query.get_or_404(post_id)
    
    return jsonify({
        'liked': liked,
        'like_count': len(post.likes)
    })


@app.route('/api/bookmark/<int:post_id>', methods=['POST'])
@login_required
def bookmark_post(post_id):
    post = Post.query.get_or_404(post_id)
    
    existing = Bookmark.query.filter_by(
        post_id=post_id,
        user_id=current_user.id
    ).first()
    
    if existing:
        return jsonify({'error': 'Already bookmarked'}), 400
    
    bookmark = Bookmark(post_id=post_id, user_id=current_user.id)
    db.session.add(bookmark)
    db.session.commit()
    
    return jsonify({'success': True})


@app.route('/api/unbookmark/<int:post_id>', methods=['POST'])
@login_required
def unbookmark_post(post_id):
    bookmark = Bookmark.query.filter_by(
        post_id=post_id,
        user_id=current_user.id
    ).first_or_404()
    
    db.session.delete(bookmark)
    db.session.commit()
    
    return jsonify({'success': True})


@app.route('/api/is_bookmarked/<int:post_id>')
@login_required
def is_bookmarked(post_id):
    bookmarked = Bookmark.query.filter_by(
        post_id=post_id,
        user_id=current_user.id
    ).first() is not None
    
    return jsonify({'bookmarked': bookmarked})


@app.route('/api/track_view/<int:post_id>', methods=['POST'])
@login_required
def track_view(post_id):
    post = Post.query.get_or_404(post_id)
    
    existing = PostView.query.filter_by(
        post_id=post_id,
        user_id=current_user.id
    ).first()
    
    if not existing:
        view = PostView(post_id=post_id, user_id=current_user.id)
        db.session.add(view)
        db.session.commit()
    
    return jsonify({'view_count': len(post.views)})


@app.route('/bookmarks')
@login_required
def bookmarks():
    page = request.args.get('page', 1, type=int)
    per_page = 8
    
    bookmarks = Bookmark.query.filter_by(user_id=current_user.id).order_by(
        Bookmark.created_at.desc()
    ).paginate(page=page, per_page=per_page, error_out=False)
    
    posts = [b.post for b in bookmarks.items]
    
    # Create a mock paginated object
    class PaginatedPosts:
        def __init__(self, items, page, pages, has_prev, has_next, prev_num, next_num, total):
            self.items = items
            self.page = page
            self.pages = pages
            self.has_prev = has_prev
            self.has_next = has_next
            self.prev_num = prev_num
            self.next_num = next_num
            self.total = total
    
    paginated = PaginatedPosts(
        items=posts,
        page=bookmarks.page,
        pages=bookmarks.pages,
        has_prev=bookmarks.has_prev,
        has_next=bookmarks.has_next,
        prev_num=bookmarks.prev_num,
        next_num=bookmarks.next_num,
        total=bookmarks.total
    )
    
    return render_template('bookmarks.html', posts=paginated, pagination_endpoint='bookmarks', pagination_args={})


@app.route('/profile/<string:username>')
def user_profile(username):
    user = User.query.filter_by(username=username).first_or_404()
    page = request.args.get('page', 1, type=int)
    per_page = 8
    now = datetime.utcnow()
    
    posts = Post.query.filter_by(
        user_id=user.id,
        draft=False
    ).filter(
        (Post.publish_at == None) | (Post.publish_at <= now)
    ).order_by(Post.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
    
    is_following = False
    if current_user.is_authenticated:
        is_following = Follow.query.filter_by(
            follower_id=current_user.id,
            following_id=user.id
        ).first() is not None
    
    return render_template('profile.html', user=user, posts=posts, is_following=is_following, 
                         pagination_endpoint='user_profile', pagination_args={'username': username})


@app.route('/trending')
def trending():
    page = request.args.get('page', 1, type=int)
    per_page = 8
    now = datetime.utcnow()
    
    # Get most liked posts from the last 7 days
    posts = db.session.query(Post).filter(
        (Post.draft == False) &
        ((Post.publish_at == None) | (Post.publish_at <= now))
    ).outerjoin(Like).group_by(Post.id).order_by(
        db.func.count(Like.id).desc()
    ).paginate(page=page, per_page=per_page, error_out=False)
    
    return render_template('trending.html', posts=posts, pagination_endpoint='trending', pagination_args={})


@app.route('/followers')
@login_required
def view_followers():
    user_id = request.args.get('user_id', current_user.id, type=int)
    user = User.query.get_or_404(user_id)
    
    page = request.args.get('page', 1, type=int)
    per_page = 12
    
    followers = user.followers.paginate(page=page, per_page=per_page, error_out=False)
    
    return render_template('followers.html', user=user, followers=followers, is_own_profile=(user_id == current_user.id))


@app.route('/following')
@login_required
def view_following():
    user_id = request.args.get('user_id', current_user.id, type=int)
    user = User.query.get_or_404(user_id)
    
    page = request.args.get('page', 1, type=int)
    per_page = 12
    
    following = user.following_users.paginate(page=page, per_page=per_page, error_out=False)
    
    return render_template('following.html', user=user, following=following, is_own_profile=(user_id == current_user.id))


@app.route('/remove_follower/<int:follower_id>', methods=['POST'])
@login_required
def remove_follower(follower_id):
    follow = Follow.query.filter_by(
        follower_id=follower_id,
        following_id=current_user.id
    ).first_or_404()
    
    db.session.delete(follow)
    db.session.commit()
    
    return jsonify({'success': True})


# ===== NOTIFICATIONS =====
@app.route('/notifications')
@login_required
def notifications():
    page = request.args.get('page', 1, type=int)
    notifs = Notification.query.filter_by(user_id=current_user.id).order_by(
        Notification.created_at.desc()
    ).paginate(page=page, per_page=10, error_out=False)
    
    return render_template('notifications.html', notifications=notifs, pagination_endpoint='notifications', pagination_args={})


@app.route('/api/mark_notification_read/<int:notif_id>', methods=['POST'])
@login_required
def mark_notification_read(notif_id):
    notif = Notification.query.get_or_404(notif_id)
    if notif.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    notif.is_read = True
    db.session.commit()
    
    return jsonify({'success': True})


@app.route('/api/mark_all_read', methods=['POST'])
@login_required
def mark_all_read():
    Notification.query.filter_by(user_id=current_user.id, is_read=False).update({'is_read': True})
    db.session.commit()
    return jsonify({'success': True})


@app.route('/api/unread_count')
@login_required
def unread_count():
    count = Notification.query.filter_by(user_id=current_user.id, is_read=False).count()
    return jsonify({'count': count})


# ===== DIRECT MESSAGES =====
@app.route('/messages')
@login_required
def messages():
    page = request.args.get('page', 1, type=int)
    
    # Get conversations with last message
    conversations = db.session.query(Message).filter(
        (Message.sender_id == current_user.id) | (Message.recipient_id == current_user.id)
    ).order_by(Message.created_at.desc()).paginate(page=page, per_page=15, error_out=False)
    
    return render_template('messages.html', conversations=conversations, pagination_endpoint='messages', pagination_args={})


@app.route('/messages/<int:user_id>')
@login_required
def chat(user_id):
    other_user = User.query.get_or_404(user_id)
    
    # Check if blocked
    is_blocked = Block.query.filter_by(blocker_id=current_user.id, blocked_id=user_id).first() is not None
    is_blocked_by = Block.query.filter_by(blocker_id=user_id, blocked_id=current_user.id).first() is not None
    
    if is_blocked or is_blocked_by:
        return render_template('chat.html', other_user=other_user, messages=[], is_blocked=True)
    
    page = request.args.get('page', 1, type=int)
    msgs = Message.query.filter(
        ((Message.sender_id == current_user.id) & (Message.recipient_id == user_id)) |
        ((Message.sender_id == user_id) & (Message.recipient_id == current_user.id))
    ).order_by(Message.created_at.asc()).paginate(page=page, per_page=50, error_out=False)
    
    # Mark as read
    Message.query.filter_by(sender_id=user_id, recipient_id=current_user.id, is_read=False).update({'is_read': True})
    db.session.commit()
    
    return render_template('chat.html', other_user=other_user, messages=msgs, is_blocked=False, pagination_endpoint='chat', pagination_args={'user_id': user_id})


@app.route('/api/send_message/<int:recipient_id>', methods=['POST'])
@login_required
def send_message(recipient_id):
    recipient = User.query.get_or_404(recipient_id)
    body = request.json.get('body', '').strip()
    
    if not body:
        return jsonify({'error': 'Message cannot be empty'}), 400
    
    # Check if blocked
    is_blocked = Block.query.filter_by(blocker_id=current_user.id, blocked_id=recipient_id).first() is not None
    is_blocked_by = Block.query.filter_by(blocker_id=recipient_id, blocked_id=current_user.id).first() is not None
    
    if is_blocked or is_blocked_by:
        return jsonify({'error': 'Cannot message this user'}), 403
    
    msg = Message(sender_id=current_user.id, recipient_id=recipient_id, body=body)
    db.session.add(msg)
    db.session.commit()
    
    return jsonify({'success': True, 'message_id': msg.id})


# ===== BLOCK/UNBLOCK =====
@app.route('/api/block/<int:user_id>', methods=['POST'])
@login_required
def block_user(user_id):
    if user_id == current_user.id:
        return jsonify({'error': 'Cannot block yourself'}), 400
    
    user_to_block = User.query.get_or_404(user_id)
    
    existing = Block.query.filter_by(blocker_id=current_user.id, blocked_id=user_id).first()
    if existing:
        return jsonify({'error': 'Already blocked'}), 400
    
    block = Block(blocker_id=current_user.id, blocked_id=user_id)
    db.session.add(block)
    db.session.commit()
    
    return jsonify({'success': True})


@app.route('/api/unblock/<int:user_id>', methods=['POST'])
@login_required
def unblock_user(user_id):
    block = Block.query.filter_by(blocker_id=current_user.id, blocked_id=user_id).first_or_404()
    
    db.session.delete(block)
    db.session.commit()
    
    return jsonify({'success': True})


@app.route('/blocked_users')
@login_required
def blocked_users():
    page = request.args.get('page', 1, type=int)
    
    blocks = Block.query.filter_by(blocker_id=current_user.id).order_by(
        Block.created_at.desc()
    ).paginate(page=page, per_page=12, error_out=False)
    
    return render_template('blocked_users.html', blocks=blocks, pagination_endpoint='blocked_users', pagination_args={})


# ===== COLLECTIONS =====
@app.route('/collections')
@login_required
def my_collections():
    collections = Collection.query.filter_by(user_id=current_user.id).order_by(Collection.created_at.desc()).all()
    return render_template('collections.html', collections=collections)


@app.route('/api/create_collection', methods=['POST'])
@login_required
def create_collection():
    name = request.json.get('name', '').strip()
    description = request.json.get('description', '').strip()
    
    if not name or len(name) > 100:
        return jsonify({'error': 'Invalid collection name'}), 400
    
    collection = Collection(user_id=current_user.id, name=name, description=description[:300] if description else None)
    db.session.add(collection)
    db.session.commit()
    
    return jsonify({'success': True, 'collection_id': collection.id})


@app.route('/api/add_to_collection/<int:collection_id>/<int:post_id>', methods=['POST'])
@login_required
def add_to_collection(collection_id, post_id):
    collection = Collection.query.get_or_404(collection_id)
    
    if collection.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    Post.query.get_or_404(post_id)
    
    existing = CollectionItem.query.filter_by(collection_id=collection_id, post_id=post_id).first()
    if existing:
        return jsonify({'error': 'Already in collection'}), 400
    
    item = CollectionItem(collection_id=collection_id, post_id=post_id)
    db.session.add(item)
    db.session.commit()
    
    return jsonify({'success': True})


@app.route('/api/remove_from_collection/<int:item_id>', methods=['POST'])
@login_required
def remove_from_collection(item_id):
    item = CollectionItem.query.get_or_404(item_id)
    collection = item.collection
    
    if collection.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    db.session.delete(item)
    db.session.commit()
    
    return jsonify({'success': True})


# ===== COMMENT REPLIES =====
@app.route('/api/reply/<int:comment_id>', methods=['POST'])
@login_required
def reply_comment(comment_id):
    parent_comment = Comment.query.get_or_404(comment_id)
    body = request.json.get('body', '').strip()
    
    if not body:
        return jsonify({'error': 'Reply cannot be empty'}), 400
    
    reply = Comment(
        author_id=current_user.id,
        post_id=parent_comment.post_id,
        body=body,
        parent_comment_id=comment_id
    )
    
    db.session.add(reply)
    db.session.commit()
    
    # Create notification
    if parent_comment.author_id != current_user.id:
        notif = Notification(
            user_id=parent_comment.author_id,
            actor_id=current_user.id,
            type='reply',
            comment_id=reply.id,
            post_id=parent_comment.post_id
        )
        db.session.add(notif)
        db.session.commit()
    
    return jsonify({'success': True, 'reply_id': reply.id})


# ===== USER RECOMMENDATIONS =====
@app.route('/recommendations')
@login_required
def recommendations():
    # Get users the current user doesn't follow
    following_ids = db.session.query(Follow.followed_id).filter_by(follower_id=current_user.id).all()
    following_ids = [f[0] for f in following_ids] + [current_user.id]
    
    # Get recommendations: users with most followers, excluding following
    recommended_users = User.query.filter(
        User.id.notin_(following_ids)
    ).order_by(
        User.followers.count().desc()
    ).limit(20).all()
    
    return render_template('recommendations.html', recommended_users=recommended_users)


# ===== POST ANALYTICS =====
@app.route('/analytics')
@login_required
def analytics():
    # Get current user's posts with stats
    posts = Post.query.filter_by(author_id=current_user.id).order_by(Post.created_at.desc()).all()
    
    analytics_data = []
    for post in posts:
        analytics_data.append({
            'post': post,
            'likes': post.likes.count(),
            'comments': post.comments.count(),
            'views': post.views.count(),
            'engagement_rate': (post.likes.count() + post.comments.count()) / max(post.views.count(), 1) * 100 if post.views.count() > 0 else 0
        })
    
    # Sort by engagement
    analytics_data.sort(key=lambda x: x['engagement_rate'], reverse=True)
    
    total_likes = sum(a['likes'] for a in analytics_data)
    total_views = sum(a['views'] for a in analytics_data)
    total_comments = sum(a['comments'] for a in analytics_data)
    
    return render_template('analytics.html', 
        analytics=analytics_data,
        total_likes=total_likes,
        total_views=total_views,
        total_comments=total_comments,
        avg_engagement=sum(a['engagement_rate'] for a in analytics_data) / max(len(analytics_data), 1)
    )


# ===== DARK MODE =====
@app.route('/api/toggle_dark_mode', methods=['POST'])
@login_required
def toggle_dark_mode():
    current_user.dark_mode = not current_user.dark_mode
    db.session.commit()
    return jsonify({'success': True, 'dark_mode': current_user.dark_mode})


# ===== SHARE POST =====
@app.route('/api/share_post/<int:post_id>', methods=['GET'])
@login_required
def share_post(post_id):
    post = Post.query.get_or_404(post_id)
    share_url = request.host_url + f'post/{post_id}'
    
    return jsonify({
        'success': True,
        'share_url': share_url,
        'title': post.content[:50] + '...',
        'description': post.content[:100] + '...'
    })


@app.route('/debug/posts')
def debug_posts():
    """Debug route to check all posts in database - REMOVE IN PRODUCTION"""
    if not app.debug:
        return "Not available", 404
    
    all_posts = Post.query.all()
    output = "<h1>All Posts in Database</h1>"
    output += f"<p>Total posts: {len(all_posts)}</p>"
    output += "<table border='1' style='margin:20px;border-collapse:collapse'>"
    output += "<tr style='background:#f0f0f0'><th style='padding:8px'>ID</th><th style='padding:8px'>Title</th><th style='padding:8px'>User</th><th style='padding:8px'>Draft</th><th style='padding:8px'>Published At</th><th style='padding:8px'>Publish At</th><th style='padding:8px'>Created At</th></tr>"
    
    for post in all_posts:
        bg = "#ffe6e6" if post.draft else "#e6ffe6"
        output += f"<tr style='background:{bg}'>"
        output += f"<td style='padding:8px'>{post.id}</td>"
        output += f"<td style='padding:8px'>{post.title}</td>"
        output += f"<td style='padding:8px'>{post.author.username}</td>"
        output += f"<td style='padding:8px'><strong>{'DRAFT' if post.draft else 'PUBLISHED'}</strong></td>"
        output += f"<td style='padding:8px'>{post.published_at if post.published_at else '<span style=\"color:red\">NULL</span>'}</td>"
        output += f"<td style='padding:8px'>{post.publish_at if post.publish_at else 'NULL'}</td>"
        output += f"<td style='padding:8px'>{post.created_at}</td>"
        output += "</tr>"
    
    output += "</table>"
    output += f"<hr><h2>Posts that should appear in home feed:</h2>"
    now = datetime.utcnow()
    visible_posts = Post.query.filter(
        (Post.draft == False) &
        ((Post.publish_at == None) | (Post.publish_at <= now))
    ).all()
    output += f"<p>Visible posts: {len(visible_posts)}</p>"
    for post in visible_posts:
        output += f"<p>✓ {post.title} by {post.author.username}</p>"
    
    return output

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        # Ensure missing columns exist to avoid runtime query errors
        ensure_publish_at_column()
        ensure_avatar_column()
        ensure_bio_column()
        
        # Fix existing posts with NULL published_at and draft=False
        # These should have been published
        try:
            from sqlalchemy import text
            db.session.execute(text("""
                UPDATE post 
                SET published_at = created_at 
                WHERE published_at IS NULL AND draft = 0 AND created_at IS NOT NULL
            """))
            db.session.commit()
            print("✓ Fixed existing posts with NULL published_at")
        except Exception as e:
            print(f"Note: Could not auto-fix posts: {e}")
    # Add host='0.0.0.0' here
    app.run(debug=True, port=5001, host='0.0.0.0')
    