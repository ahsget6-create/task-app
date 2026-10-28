from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = 'my-secret-key-saas-task-app'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///tasks.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# إعداد نظام تسجيل الدخول (Flask-Login)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


# 1. نموذج المستخدمين (User Model)
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), default='employee')  # admin أو employee
    tasks = db.relationship('Task', backref='assigned_user', lazy=True)


# 2. نموذج المهام (Task Model)
class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(50), default='todo')  # todo, in_progress, done
    priority = db.Column(db.String(20), default='medium')  # high, medium, low
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)  # ربط المهمة بالموظف


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# تسجيل دخول تلقائي للأدمن لفتح الموقع مباشرة بدون صفحة دخول
@app.before_request
def auto_login_admin():
    if not current_user.is_authenticated:
        admin_user = User.query.filter_by(username='admin').first()
        if admin_user:
            login_user(admin_user)


# إنشاء الجداول وتوفير حساب أدمن افتراضي
with app.app_context():
    db.create_all()
    if not User.query.filter_by(username='admin').first():
        hashed_pw = generate_password_hash('admin123', method='pbkdf2:sha256')
        admin_user = User(username='admin', password=hashed_pw, role='admin')
        db.session.add(admin_user)
        db.session.commit()


# --- الروابط (Routes) ---

# 1. صفحة تسجيل الدخول
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('index'))
        else:
            flash('اسم المستخدم أو كلمة المرور غير صحيحة')

    return render_template('login.html')


# 2. تسجيل الخروج
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


# 3. الصفحة الرئيسية
@app.route('/')
@login_required
def index():
    if current_user.role == 'admin':
        # الأدمن يرى كل المهام
        todo_tasks = Task.query.filter_by(status='todo').all()
        in_progress_tasks = Task.query.filter_by(status='in_progress').all()
        done_tasks = Task.query.filter_by(status='done').all()
    else:
        # الموظف يرى فقط المهام المخصصة له
        todo_tasks = Task.query.filter_by(status='todo', user_id=current_user.id).all()
        in_progress_tasks = Task.query.filter_by(status='in_progress', user_id=current_user.id).all()
        done_tasks = Task.query.filter_by(status='done', user_id=current_user.id).all()

    employees = User.query.filter_by(role='employee').all()
    return render_template('index.html',
                           todo=todo_tasks,
                           in_progress=in_progress_tasks,
                           done=done_tasks,
                           employees=employees)


# 4. إضافة مهمة وتخصيصها
@app.route('/add_task', methods=['POST'])
@login_required
def add_task():
    title = request.form.get('title')
    description = request.form.get('description')
    priority = request.form.get('priority', 'medium')
    assigned_to_id = request.form.get('assigned_to')

    if title:
        assigned_user = assigned_to_id if assigned_to_id else current_user.id
        new_task = Task(title=title, description=description, priority=priority, status='todo', user_id=assigned_user)
        db.session.add(new_task)
        db.session.commit()

    return redirect(url_for('index'))


# 5. تحديث حالة المهمة
@app.route('/update_status/<int:task_id>/<new_status>')
@login_required
def update_status(task_id, new_status):
    task = Task.query.get_or_404(task_id)
    if new_status in ['todo', 'in_progress', 'done']:
        task.status = new_status
        db.session.commit()
    return redirect(url_for('index'))


# 6. حذف مهمة
@app.route('/delete_task/<int:task_id>')
@login_required
def delete_task(task_id):
    task = Task.query.get_or_404(task_id)
    db.session.delete(task)
    db.session.commit()
    return redirect(url_for('index'))


# 7. لوحة الأدمن
@app.route('/admin')
@login_required
def admin():
    if current_user.role != 'admin':
        return redirect(url_for('index'))

    total_tasks = Task.query.count()
    todo_count = Task.query.filter_by(status='todo').count()
    in_progress_count = Task.query.filter_by(status='in_progress').count()
    done_count = Task.query.filter_by(status='done').count()
    employees_count = User.query.filter_by(role='employee').count()

    return render_template('admin.html',
                           total=total_tasks,
                           todo=todo_count,
                           in_progress=in_progress_count,
                           done=done_count,
                           employees_count=employees_count)


import os

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)