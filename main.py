from functools import wraps

from flask import Flask, render_template, redirect, url_for, flash, request, abort
from flask_bootstrap import Bootstrap5
from flask_ckeditor import CKEditor
from datetime import date
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user, login_manager
from forms import CreatePostForm, RegisterForm, LoginForm, CommentForm
from flask_gravatar import Gravatar

# https://www.geeksforgeeks.org/deploy-python-flask-app-on-heroku/

app = Flask(__name__)
app.config['SECRET_KEY'] = '8BYkEfBA6O6donzWlSihBXox7C0sKR6b'
ckeditor = CKEditor(app)
Bootstrap5(app)

##CONNECT TO DB
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///blog.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)

##CONFIGURE TABLES

class BlogPost(db.Model):
    __tablename__ = "blog_posts"
    id = db.Column(db.Integer, primary_key=True)
    author = db.Column(db.String(250), nullable=False)
    title = db.Column(db.String(250), unique=True, nullable=False)
    subtitle = db.Column(db.String(250), nullable=False)
    date = db.Column(db.String(250), nullable=False)
    body = db.Column(db.Text, nullable=False)
    img_url = db.Column(db.String(250), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)


class Comment(db.Model):
    __tablename__ = "comment"
    id = db.Column(db.Integer, primary_key=True)
    comment = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('blog_posts.id'), nullable=False)


class User(UserMixin, db.Model):
    __tablename__ = "user"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    name = db.Column(db.String(1000))
    posts = db.relationship('BlogPost', backref='user', lazy=True)
    comments = db.relationship('Comment', backref='user', lazy=True)

def admin_only(func):
    @wraps(func)
    def check_user(*args, **kargs):
        if current_user is None:
            return abort(403, "Not authorized")
        if current_user.id == 1:
          return func(*args, **kargs)
        else:
            return abort(403, "Only Admin")



    return check_user

@app.route('/')
def get_all_posts():
    posts = db.session.execute(db.select(BlogPost)).scalars()
    return render_template("index.html", all_posts=posts)


@login_manager.user_loader
def load_user(user_id):
    user = db.session.execute(db.select(User).filter_by(id=user_id)).first()
    if user is None:
        return None

    return user[0]

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if request.method == "POST":
        is_valid = form.validate_on_submit()
        if is_valid:

            user = User()
            user.email = form.data['email']
            data_user = db.session.execute(db.select(User).filter_by(email=user.email)).first()
            if data_user != None:
                flash('User already registered with that email')
                return render_template("register.html", form=form)
            user.password = generate_password_hash(form.data['password'], method='pbkdf2:sha256', salt_length=8)
            user.name = form.data['name']
            db.session.add(user)
            db.session.commit()

            login_user(user)
            return redirect(url_for('get_all_posts'))
    return render_template("register.html", form=form)


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if request.method == "POST":
        if form.validate_on_submit():
            email = form.data['email']
            password = form.data['password']
            data_user = db.session.execute(db.select(User).filter_by(email=email)).first()
            if data_user != None:
                user = data_user[0]
                if check_password_hash(user.password, password):
                    login_user(user)
                    flash('Logged in successfully.')
                    return redirect(url_for('get_all_posts'))
                else:
                    flash('Password incorrect please try again')
            else:
                flash('User not found please try again')

    return render_template("login.html", form=form)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('get_all_posts'))


@app.route("/post/<int:post_id>")
def show_post(post_id):
    comment_form = CommentForm()
    requested_post = BlogPost.query.get(post_id)
    #comments = db.session.execute(db.select(Comment).filter_by(post_id=post_id)).scalars()
    comments = db.session.query(Comment, User).filter(Comment.post_id == post_id, Comment.user_id == User.id).all()
    return render_template("post.html", post=requested_post, form = comment_form, comments=comments)


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/contact")
def contact():
    return render_template("contact.html")


@app.route("/new-post", methods=['GET', 'POST'])
@login_required
@admin_only
def add_new_post():
    form = CreatePostForm()
    if form.validate_on_submit():
        new_post = BlogPost(
            title=form.title.data,
            subtitle=form.subtitle.data,
            body=form.body.data,
            img_url=form.img_url.data,
            author=current_user.name,
            date=date.today().strftime("%B %d, %Y"),
            user_id=current_user.id,
        )
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for("get_all_posts"))
    return render_template("make-post.html", form=form)


@app.route("/edit-post/<int:post_id>", methods=['GET', 'POST'])
@login_required
@admin_only
def edit_post(post_id):
    post = BlogPost.query.get(post_id)
    edit_form = CreatePostForm(
        title=post.title,
        subtitle=post.subtitle,
        img_url=post.img_url,
        author=post.author,
        body=post.body
    )


    if edit_form.validate_on_submit():
        post.title = edit_form.title.data
        post.subtitle = edit_form.subtitle.data
        post.img_url = edit_form.img_url.data
        post.body = edit_form.body.data
        db.session.commit()
        return redirect(url_for("show_post", post_id=post.id))

    return render_template("make-post.html", form=edit_form)


@app.route("/delete/<int:post_id>")
@login_required
@admin_only
def delete_post(post_id):
    post_to_delete = BlogPost.query.get(post_id)
    db.session.delete(post_to_delete)
    db.session.commit()
    return redirect(url_for('get_all_posts'))

@app.route("/comment/<int:post_id>", methods=['POST'])
@login_required
def add_comment(post_id):
    form = CommentForm()
    if form.validate_on_submit():
        new_comment = Comment(
            comment=form.comment.data,
            user_id=current_user.id,
            post_id=post_id,
        )
        db.session.add(new_comment)
        db.session.commit()
        return redirect(url_for("show_post", post_id=post_id))

    return redirect(url_for('get_all_posts'))


if __name__ == "__main__":
    #app.run(host='0.0.0.0', port=5000)
    app.run(debug=True)
