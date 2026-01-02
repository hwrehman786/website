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
    posts = db.relationship('Post', backref='author', lazy=True)

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
    published_at = db.Column(db.DateTime, default=datetime.utcnow)
    publish_at = db.Column(db.DateTime, nullable=True)


class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    body = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

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
    page = request.args.get('page', 1, type=int)
    per_page = 8
    now = datetime.utcnow()
    pagination = Post.query.filter(Post.draft==False).filter((Post.publish_at==None) | (Post.publish_at <= now)).order_by(Post.published_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
    return render_template('index.html', posts=pagination, pagination_endpoint='index', pagination_args={})

@app.route('/my_account', methods=['GET', 'POST'])
@login_required
def my_account():
    if request.method == 'POST':
        # handle avatar upload
        file = request.files.get('avatar')
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            # prefix with user id to avoid collisions
            filename = f"u{current_user.id}_" + filename
            save_path = os.path.join(UPLOAD_FOLDER, 'avatars', filename)
            file.save(save_path)
            current_user.avatar_filename = filename
            db.session.commit()
            flash('Avatar updated.')
        else:
            flash('No valid avatar uploaded.')
        return redirect(url_for('my_account'))

    user_posts = Post.query.filter_by(user_id=current_user.id).order_by(Post.published_at.desc()).all()
    return render_template('my_account.html', posts=user_posts)

@app.route('/create_post', methods=['GET', 'POST'])
@login_required
def create_post():
    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        file = request.files.get('image')
        tags = request.form.get('tags', '')
        draft = True if request.form.get('draft') == 'on' else False
        publish_at_str = request.form.get('publish_at')
        publish_at_dt = None
        if publish_at_str:
            try:
                publish_at_dt = datetime.fromisoformat(publish_at_str)
            except Exception:
                publish_at_dt = None
        publish_at_str = request.form.get('publish_at')
        publish_at_dt = None
        if publish_at_str:
            try:
                publish_at_dt = datetime.fromisoformat(publish_at_str)
            except Exception:
                publish_at_dt = None

        image_filename = None
        image_base64 = None
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(save_path)
            image_filename = filename
        elif file:
            image_base64 = base64.b64encode(file.read()).decode('utf-8')

        now = datetime.utcnow()
        final_draft = draft
        published_at_val = None
        if publish_at_dt:
            if publish_at_dt > now:
                final_draft = True
                published_at_val = None
            else:
                published_at_val = publish_at_dt
        else:
            published_at_val = None if final_draft else datetime.utcnow()

        new_post = Post(title=title, content=content, image_data=image_base64, image_filename=image_filename, tags=tags, draft=final_draft, user_id=current_user.id, published_at=published_at_val, publish_at=publish_at_dt)
        db.session.add(new_post)
        db.session.commit()
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
        draft = True if request.form.get('draft') == 'on' else False
        if title:
            post.title = title
        if content:
            post.content = content
        post.tags = tags
        post.draft = draft
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
        # determine published_at based on draft and publish_at
        now = datetime.utcnow()
        if publish_at_dt and publish_at_dt > now:
            post.draft = True
            post.published_at = None
        else:
            post.published_at = None if post.draft else (publish_at_dt if publish_at_dt else datetime.utcnow())
        db.session.commit()
        flash('Post updated.')
        return redirect(url_for('index'))

    return render_template('edit_post.html', post=post)


@app.route('/delete_post/<int:post_id>', methods=['POST'])
@login_required
def delete_post(post_id):
    post = Post.query.get_or_404(post_id)
    if post.user_id != current_user.id:
        flash('You are not authorized to delete this post.')
        return redirect(url_for('index'))
    db.session.delete(post)
    db.session.commit()
    flash('Post deleted.')
    return redirect(url_for('index'))


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

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        # Ensure missing columns exist to avoid runtime query errors
        ensure_publish_at_column()
        ensure_avatar_column()
    # Add host='0.0.0.0' here
    app.run(debug=True, port=5001, host='0.0.0.0')
    