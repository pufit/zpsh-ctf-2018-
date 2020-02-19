from flask import *
import pymysql
from config import *
from .google_sheets import GoogleSheet
import datetime
import secret_key

main = Blueprint('main', __name__, template_folder='templates', static_folder='static')

google_sheet = GoogleSheet()


# Приветствую тебя, юный хакер! Ты далеко зашёл, но тебя всё равно ждёт провал.
# Теперь ты сам можешь убедиться, что этот сайт абсолютно невзламываемый.
# Из соображений безопасности я удалил несколько файлов, так что теперь ты точно
# здесь ничего не найдёшь!
# Удачи :)

class Cursor(pymysql.cursors.Cursor):
    def __init__(self, database):
        super().__init__(database)

    def execute(self, sql, args=None):
        db.ping()
        msg = []
        for s in sql.split(';'):
            if s.strip():
                try:
                    super().execute(s)
                    msg.append(('success', s))
                except Exception as ex:
                    print(ex)
                    msg.append(('error', s + '<br>' + str(ex)))
        if not len(msg):
            return []
        if msg[0][0] == 'error':
            return msg
        return msg[1:]


db = pymysql.connect(MYSQL_DATABASE_HOST,
                     MYSQL_DATABASE_USER,
                     MYSQL_DATABASE_PASSWORD,
                     MYSQL_DATABASE_DB,
                     charset='utf8',
                     cursorclass=Cursor)


@main.route('/', methods=['POST', 'GET'])
def lobby():
    db.ping()
    with db.cursor() as cursor:
        if request.method == 'POST':
            if request.form.get('comment_text') and request.form['comment_text'].strip():
                # Собираем SQL запрос для получения комментария
                sql = """
                INSERT INTO `comments` (`user`, `text`, `time`) 
                VALUES ('%s', '%s', '%s');
                """ % (session.get('auth'),
                       request.form['comment_text'].strip(),
                       datetime.datetime.today().strftime("%Y-%m-%d %H:%M:%S"))

                # И отправляем всё это дело
                # Тут совершенно точно не будет SQL инъекции
                for msg in cursor.execute(sql):
                    flash(msg[1], category=msg[0])
                return redirect(url_for("main.lobby"))
        cursor.execute('SELECT * FROM Comments')
        comments = reversed(cursor.fetchall())
        if session.get('auth'):
            sql = """
            UPDATE Users SET
            upd="%s"
            WHERE user="%s"
            """ % (datetime.datetime.today().strftime("%Y-%m-%d %H:%M:%S"), session['auth'])
            cursor.execute(sql)
        db.commit()
    resp = make_response(render_template('base.html',
                                         auth=session.get('auth'),
                                         commands=google_sheet.table,
                                         comments=comments,
                                         end=google_sheet.win))
    if not session.get('auth'):
        resp.set_cookie('password', '')
    return resp


@main.route('/login', methods=['POST', 'GET'])
def sign_in():
    if session.get('auth'):
        return redirect('')
    if request.method == 'GET':
        return render_template('signin.html')
    if request.method == 'POST':
        db.ping()
        cursor = db.cursor()
        user = request.form['login']
        cursor.execute('SELECT * from Users WHERE user="%s"' % user)
        data = cursor.fetchone()
        if data and data[1] == request.form['password']:
            session['auth'] = user
            resp = redirect('')
            resp.set_cookie('password', request.form['password'])
            return resp
        cursor.close()
        return render_template('signin.html', error='Wrong login or password')
    abort(418)


@main.route('/reg', methods=['POST', 'GET'])
def reg():
    if session.get('auth'):
        return redirect('')
    if request.method == 'GET':
        return render_template('reg.html')
    if request.method == 'POST':
        db.ping()
        cursor = db.cursor()
        user = request.form['login']
        password = request.form['password']
        key = request.form['key']
        # Проверяем секретный ключ.
        # Вообще, я люблю цифру 4
        if secret_key.check(key):
            sql = """
            INSERT INTO `users` (`user`, `password`, `reg`) 
            VALUES ('%s', '%s', '%s');
            """ % (user, password, datetime.datetime.today().strftime("%Y-%m-%d %H:%M:%S"))
            cursor.execute(sql)
            session['auth'] = user
            resp = redirect('')
            resp.set_cookie('password', request.form['password'])
            db.commit()
            return resp
        cursor.close()
        return render_template('reg.html', error='Bad key')
    abort(418)


@main.route('/profile')
def profile():
    if not request.args.get('user'):
        abort(404)
    user = request.args['user']
    db.ping()
    with db.cursor() as cursor:
        cursor.execute('SELECT * from Users WHERE user="%s"' % user)
        data = cursor.fetchone()
        if not data:
            abort(404)
    return render_template('pa.html', data=data)


@main.route('/logout')
def logout():
    if session.get('auth'):
        session.pop('auth')
    resp = redirect('/')
    resp.set_cookie('password', '')
    return resp


@main.route('/winner', methods=['GET'])
def winner():
    if session.get('auth') and not google_sheet.win:
        google_sheet.set_score(request.args['team'], WIN_SCORE)
        google_sheet.update()
        return redirect('/')
    elif google_sheet.win:
        return 'Одна из команд уже получила баллы'
    abort(418)


@main.errorhandler(500)
def internal_server_error(_):
    return render_template('500.html'), 500
