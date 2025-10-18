from flask import Flask, render_template, request, redirect, url_for, session
import bcrypt
import sqlite3
import sys
import secrets
import string
from flask_socketio import SocketIO, emit, join_room

print('some debug', file=sys.stderr)

app = Flask(__name__)
socketio = SocketIO(app)

app.secret_key = "/,z}i't\9UGrtMK(<y2lECF]Vb}B2naL]0a2S:7=?MOdYc]D^y"

@app.route('/')
def index():
    return render_template("index.html")


@app.route('/login', methods=['GET', 'POST'])
def login():
    #bere input ze stranky
    if request.method == 'POST':
        usEm = request.form['username']
        password = request.form['password']
        #heslo ze starnky => bytes
        user_bytes = password.encode('utf-8')
        try:
            conn = sqlite3.connect('users.db')
            cursor = conn.cursor()
            #hleda heslo bud pro username ci email
            cursor.execute("SELECT password FROM users WHERE email=? OR username=?",(usEm, usEm))
            #vysledek se popripadne ulozi sem
            result = cursor.fetchone()
            cursor.execute("SELECT username FROM users WHERE email=? OR username=?",(usEm,usEm))
            username = cursor.fetchone()
            #a kdyz to najde heslo k danému username ci email tak ho zkontroluje
            if result:
                db_pass = result[0]
                if isinstance(db_pass, str):
                    db_pass = db_pass.encode('utf-8')
                #kdyz je spravne posle uzivatele na userPage
                if bcrypt.checkpw(user_bytes, db_pass):
                    session['username'] = username[0]
                    return redirect(url_for("userPage", username = session['username']))
                else:
                    return render_template("login.html", login_errors="Incorrect password.")
            else:
                return render_template("login.html", login_errors="Invalid username or e-mail.")
        except Exception as e:
            return f"Something went wrong: {e}"
        finally:
            conn.close()
    else:
        return render_template("login.html")
    
@app.route('/register', methods = ['GET','POST'])
def register():
    #bere input ze stranky
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        name = request.form['name']
        surname = request.form['surname']
        email = request.form['email']
        dob = request.form['dob']

        #hash hesla
        password_bytes = password.encode('utf-8')
        salt = bcrypt.gensalt()
        hash = bcrypt.hashpw(password_bytes, salt).decode('utf-8')
        
        #zapsani do db pokud user neexistuje (username ci email)
        try:
            conn = sqlite3.connect('users.db')
            cursor = conn.cursor()
            cursor.execute("SELECT username FROM users WHERE username=?", (username,))
            existing_user = cursor.fetchone()
            cursor.execute("SELECT email FROM users WHERE email=?", (email,))
            existing_email = cursor.fetchone()

            #vypisuje chyby (kdyz uz username/email je pouzit)
            reg_errors = []
            if existing_user:
                print('username in use')
                reg_errors.append("Username is already taken.")
            if existing_email:
                print('email in use')
                reg_errors.append("Email is already in use.")
            if reg_errors:
                return render_template("register.html", reg_errors = reg_errors)
            #kdyz nejsou zadne chyby tak input ze stranky zapise do db
            else:
                cursor.execute("INSERT INTO users (username, password, name, surname, email, dob) VALUES (?, ?, ?, ?, ?, ?)", (username, hash, name, surname, email, dob))
                conn.commit()
                
                return redirect(url_for("login"))
        finally:
            conn.close()
    return render_template("register.html")

@app.route('/user/<username>')
def userPage(username):
    if 'username' not in session:
        return redirect(url_for("login"))
    if session['username'] != username:
        errorH = ["Unauthorized"]
        return render_template("error.html", errorH = errorH) , 403
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute("SELECT username FROM users WHERE username=?", (username,))
    username_data = cursor.fetchone()
    conn.close()
    return render_template('userPage.html', username_data=username_data)

@app.route('/streaming')
def streaming():
    return render_template('stream.html')

@app.route('/chatting')
def chatting():
    return render_template('chat.html')

@app.route('/sell')
def sell():
    return render_template('sell.html')

@app.route('/draw/<room_ID>')
def draw(room_ID):
    return render_template('draw.html', room_ID=room_ID)

draw_history = {}
@app.route('/create',methods=['GET','POST'])
def create():
    if request.method == 'POST':
    #input ze stranky
        name = request.form['name']
        password = request.form['password']
        if not password:
            is_public = True
        else:
            is_public = False
    #hash hesla
        password_bytes = password.encode('utf-8')
        salt = bcrypt.gensalt()
        hash = bcrypt.hashpw(password_bytes, salt).decode('utf-8')
    #generuje room_ID
        def generate_roomID(length=8):
            chars = string.ascii_uppercase + string.digits  # ABC... + 0-9
            return ''.join(secrets.choice(chars) for _ in range(length))
        room_ID = generate_roomID()
        try:
            conn = sqlite3.connect('rooms.db')
            cursor = conn.cursor()
            
            cursor.execute("INSERT INTO rooms (name, password, room_ID, is_public) VALUES (?, ?, ?, ?)", (name, hash, room_ID, is_public))
            conn.commit()
            print(f"Room created: {name} / {room_ID}")
            
        finally:
            conn.close()
        return redirect(url_for("draw", room_ID=room_ID))
    return render_template("drawCreate.html")

@app.route('/join', methods=['GET'])
def join():
    return render_template('drawJoin.html')

@app.route('/join/public')
def public():
    try:
        conn = sqlite3.connect('rooms.db')
        cursor = conn.cursor()
        cursor.execute("SELECT name, room_ID FROM rooms WHERE is_public = TRUE")
        rooms = cursor.fetchall()
        conn.commit()
    finally:
        conn.close()
    return render_template("drawJoinPublic.html", rooms=rooms)

@app.route('/join/private')
def private():
    try:
        conn = sqlite3.connect('rooms.db')
        cursor = conn.cursor()
        cursor.execute("SELECT name, room_ID FROM rooms WHERE is_public = FALSE")
        rooms = cursor.fetchall()
        conn.commit()
    finally:
        conn.close()
    return render_template("drawJoinPrivate.html", rooms=rooms)

@app.route('/option')
def option():
    return render_template('drawOption.html')

@socketio.on('join_room')
def handle_join(data):
    room = data['room']
    join_room(room)
    print(f"Client joined room {room}")
    if room in draw_history:
        emit('draw_history', draw_history[room], to=request.sid)


@socketio.on('draw')
def handle_draw(data):
    room = data['room']
    if room not in draw_history:
        draw_history[room] = []
    draw_history[room].append(data)
    emit('draw', data, to=room, skip_sid=request.sid) #odelar ostatnim lidem

if __name__ == "__main__":
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)