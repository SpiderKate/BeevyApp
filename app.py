from flask import Flask, render_template, request, redirect, url_for, session, flash, g
import bcrypt
import sqlite3
import sys
import secrets
import string
import os
import uuid
from werkzeug.utils import secure_filename
from flask_socketio import SocketIO, emit, join_room
from datetime import timedelta, datetime

now = datetime.now()


STATIC_ROOT = "static"
AVATAR_UPLOAD_FOLDER = "uploads/avatar"
UPLOAD_FOLDER = "uploads/shop"
def save_uploaded_file(file, subfolder):
    filename = f"{uuid.uuid4().hex}_{secure_filename(file.filename)}"

    relative_path = os.path.join(subfolder, filename).replace("\\", "/")
    full_path = os.path.join(STATIC_ROOT, relative_path)

    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    file.save(full_path)

    return relative_path

print('some debug', file=sys.stderr)

app = Flask(__name__)
socketio = SocketIO(app)

app.secret_key = "/,z}it9UGrtMK(<y2lECF]Vb}B2naL]0a2S:7=?MOdYc]D^y"
app.permanent_session_lifetime = timedelta(days=7)

@app.route('/')
def index():
    return render_template("index.html")


@app.route('/login', methods=['GET', 'POST'])
def login():
    #bere input ze stranky
    login_errors = []
    if request.method == 'POST':
        usEm = request.form['username']
        password = request.form['password']
        #heslo ze starnky => bytes
        user_bytes = password.encode('utf-8')
        try:
            conn = sqlite3.connect('beevy.db')
            cursor = conn.cursor()
            #hleda heslo bud pro username ci email
            cursor.execute("SELECT password,username,last_login_at,id FROM users WHERE email=? OR username=?",(usEm, usEm))
            #vysledek se popripadne ulozi sem
            result = cursor.fetchone()
            #a kdyz to najde heslo k danému username ci email tak ho zkontroluje
            if result:
                db_pass = result[0]
                if isinstance(db_pass, str):
                    db_pass = db_pass.encode('utf-8')
                #kdyz je spravne posle uzivatele na userPage
                if bcrypt.checkpw(user_bytes, db_pass):
                    session.permanent = True
                    session['username'] = result[1]
                    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    cursor.execute("UPDATE users SET last_login_at=? WHERE id=?",(now,result[3]))
                    print("Rows updated:", cursor.rowcount)

                    conn.commit()
                    
                    return redirect(url_for("userPage", username = session['username']))
                else:
                    login_errors.append("Incorrect password")
            else:
                login_errors.append("Invalid username or e-mail")
        except Exception as e:
            return f"Something went wrong: {e}"
        finally:
            conn.close()
    else:
        return render_template("login.html")
    if login_errors:
        return render_template("login.html", login_errors=login_errors)
    
    
@app.route('/register', methods = ['GET','POST'])
def register():
    #bere input ze stranky
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        name = request.form['name'].capitalize()
        surname = request.form['surname'].capitalize()
        email = request.form['email']
        dob = request.form['dob']

        #hash hesla
        hash = None if not password else bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        #zapsani do db pokud user neexistuje (username ci email)
        try:
            conn = sqlite3.connect('beevy.db')
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

#userpage
@app.route('/<username>',methods=["GET","POST"])
def userPage(username):
    if 'username' not in session: #kontroluje jestli je vytvorena session
        return redirect(url_for("login"))
    if session['username'] != username: #kontroluje zda uzivatel vstupuje na svoji stranku (na svuj session) 
        errorH = ["Unauthorized"]
        return render_template("error.html", errorH = errorH) , 403
    conn = sqlite3.connect('beevy.db')
    cursor = conn.cursor()
    cursor.execute("SELECT username FROM users WHERE username=?", (username,))
    username_data = cursor.fetchone()
    conn.close()
    return render_template('userPage.html', username_data=username_data)

@app.route('/join/<room_ID>', methods=['GET','POST'])
def join_room_page(room_ID):
    errorH = []
    if 'username' not in session: #kontroluje user je prihlasen
        errorH = ["Log in is needed to draw."]
        return render_template("error.html",errorH=errorH), 403
    try:
        conn = sqlite3.connect("beevy.db")
        cursor = conn.cursor()
        cursor.execute("SELECT name, password, is_public FROM rooms WHERE room_ID =?",(room_ID,))
        room = cursor.fetchone()
    finally:
        conn.close()
    if not room:
        errorH = ["Room not found"]
        return render_template("error.html", errorH = errorH) , 404
    room_name, password_hash, room_type = room
    if room_type == True:
        session.setdefault('verified_rooms', []).append(room_ID)
        return redirect(url_for('draw', room_ID=room_ID))
    if request.method == 'POST':
        entered_password = request.form['password']
        if password_hash and bcrypt.checkpw(entered_password.encode('utf-8'), password_hash.encode('utf-8')):
            session.setdefault('verified_rooms', []).append(room_ID)
            return redirect(url_for('draw', room_ID=room_ID))
        else:
            return render_template('roomPassword.html', error="Wrong password!", room_ID=room_ID)
    return render_template('roomPassword.html', room_ID=room_ID)

@app.route('/draw/<room_ID>')
def draw(room_ID):
    verified_rooms = session.get('verified_rooms', [])
    errorH = []
    if 'username' not in session: #kontroluje user je prihlasen
        errorH = ["Log in first to draw."]
        return render_template("login.html",errorH=errorH)
    try:
        conn = sqlite3.connect("beevy.db")
        cursor = conn.cursor()
        cursor.execute("SELECT is_public FROM rooms WHERE room_ID =?",(room_ID,))
        result = cursor.fetchone()
    finally:
        conn.close()
    
    if not result:
        errorH = ["Room not found"]
        return render_template("error.html", errorH = errorH) , 404

    room_type = result[0]
    if room_type == 'private' and room_ID not in verified_rooms:
        return redirect(url_for('join_room_page', room_ID=room_ID))
    return render_template('draw.html',room_ID=room_ID)

draw_history = {}
@app.route('/create',methods=['GET','POST'])
def create():
    username = session.get('username')
    errorH = []
    if 'username' not in session: #kontroluje user je prihlasen
        errorH = ["Log in first to draw."]
        return render_template("login.html",errorH=errorH), 403
    if request.method == 'POST':
    #input ze stranky 
        name = request.form['name']
        password = request.form['password']
        

        if not password:
            is_public = True
        else:
            is_public = False
    #hash hesla
        hash = None if not password else bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    #generuje room_ID
        def generate_roomID(length=8):
            chars = string.ascii_uppercase + string.digits  # ABC... + 0-9
            return ''.join(secrets.choice(chars) for _ in range(length))
        room_ID = generate_roomID()
        try:
            conn = sqlite3.connect('beevy.db')
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM users WHERE username = ?;",(username,))
            User_ID = cursor.fetchone()
            cursor.execute("INSERT INTO rooms (name, password, room_ID, is_public, User_ID) VALUES (?, ?, ?, ?, ?)", (name, hash, room_ID, is_public, User_ID[0]))
            conn.commit()
            print(f"Room created: {name} / {room_ID}")
            
        finally:
            conn.close()
        return redirect(url_for("draw", room_ID=room_ID))
    return render_template("drawCreate.html")

@app.route('/join', methods=['GET'])
def join():
    errorH = []
    if 'username' not in session: #kontroluje user je prihlasen
        errorH = ["Log in first to draw."]
        return render_template("login.html",errorH=errorH), 403
    return render_template('drawJoin.html')

#vypisuje vytvorene public rooms linky
@app.route('/join/public')
def public():
    errorH = []
    if 'username' not in session: #kontroluje user je prihlasen
        errorH = ["Log in first to draw."]
        return render_template("login.html",errorH=errorH), 403
    try:
        conn = sqlite3.connect('beevy.db')
        cursor = conn.cursor()
        cursor.execute("SELECT name, room_ID FROM rooms WHERE is_public = TRUE")
        rooms = cursor.fetchall()
    finally:
        conn.close()
    return render_template("drawJoinPublic.html", rooms=rooms)

#vypisuje vytvorene private rooms jako linky
@app.route('/join/private')
def private():
    errorH = []
    if 'username' not in session: #kontroluje user je prihlasen
        errorH = ["Log in first to draw."]
        return render_template("login.html",errorH=errorH), 403
    try:
        conn = sqlite3.connect('beevy.db')
        cursor = conn.cursor()
        cursor.execute("SELECT name, room_ID FROM rooms WHERE is_public = FALSE")
        rooms = cursor.fetchall()
    finally:
        conn.close()
    return render_template("drawJoinPrivate.html", rooms=rooms)

@app.route('/option')
def option():
    errorH = []
    if 'username' not in session: #kontroluje user je prihlasen
        errorH = ["Log in first to draw."]
        return render_template("login.html",errorH=errorH), 403
    return render_template('drawOption.html')

#settings
@app.route('/<username>/settings')
def settings(username):
    if 'username' not in session: #kontroluje jestli je vytvorena session
        errorH = ["Login first to access settings"]
        return render_template("login.html",errorH=errorH), 403
    if session['username'] != username: #kontroluje zda uzivatel vstupuje na svoji stranku (na svuj session) 
        errorH = ["Unauthorized"]
        return render_template("error.html", errorH = errorH) , 403
    return render_template("settings.html")


@app.route("/<username>/settings/profile", methods=["GET", "POST"])
def settings_profile(username):
    if "username" not in session:
        errorH = ["Login first to access settings"]
        return render_template("login.html", errorH=errorH), 403

    if session["username"] != username:
        return render_template("error.html", errorH=["Unauthorized"]), 403

    conn = sqlite3.connect("beevy.db")
    cursor = conn.cursor()

    cursor.execute(
        "SELECT id, username, bio, avatar_path FROM users WHERE username=?",
        (username,)
    )
    user = cursor.fetchone()
    if not user:
        conn.close()
        return "User not found", 404

    if request.method == "POST":
        new_username = request.form.get("username")
        new_bio = request.form.get("bio")
        avatar = request.files.get("avatar")

        avatar_path = user[3]  # default: keep old avatar

        if avatar and avatar.filename:
            # Save avatar in AVATAR_UPLOAD_FOLDER
            avatar_path = save_uploaded_file(avatar, AVATAR_UPLOAD_FOLDER)

        cursor.execute(
            """
            UPDATE users
            SET username = ?, bio = ?, avatar_path = ?
            WHERE id = ?
            """,
            (new_username, new_bio, avatar_path, user[0])
        )
        conn.commit()
        conn.close()

        # Update session username if changed
        session["username"] = new_username

        return {"avatar_path": avatar_path}, 200

    conn.close()
    return render_template("settingsProfile.html", user=user)



@app.route("/<username>/settings/account", methods=["GET","POST"])
def settingsAccount(username):
    if 'username' not in session: #kontroluje jestli je vytvorena session
        errorH = ["Login first to access settings"]
        return render_template("login.html",errorH=errorH), 403
    if session['username'] != username: #kontroluje zda uzivatel vstupuje na svoji stranku (na svuj session) 
        errorH = ["Unauthorized"]
        return render_template("error.html", errorH = errorH) , 403
    conn = sqlite3.connect("beevy.db")
    cursor = conn.cursor()

    cursor.execute("SELECT id, email, language, theme, default_brush_size, notifications FROM users WHERE username=?",(username,))
    user = cursor.fetchone()

    if not user:
        conn.close()
        return "User not found", 
    
    
    if request.method == "POST":
        new_email = request.form.get("email")
        new_language = request.form.get("language")
        new_theme = request.form.get("theme")
        new_brush = request.form.get("brush")
        new_not = 1 if request.form.get("not") else 0  # handle checkbox

        cursor.execute(
            """
            UPDATE users
            SET email = ?, language = ?, theme = ?, default_brush_size = ?, notifications = ?
            WHERE id = ?
            """,
            (new_email, new_language, new_theme, new_brush, new_not, user[0])
        )
        conn.commit()
        conn.close()

        return {
            "email": new_email,
            "language": new_language,
            "theme": new_theme,
            "brush": new_brush,
            "notifications": new_not
        }, 200
    conn.close()
    return render_template("settingsAccount.html", user=user)


@app.route("/<username>/settings/security", methods=["GET","POST"])
def settingsSecurity(username):
    error = []
    if 'username' not in session: #kontroluje jestli je vytvorena session
        errorH = ["Login first to access settings"]
        return render_template("login.html",errorH=errorH), 403
    if session['username'] != username: #kontroluje zda uzivatel vstupuje na svoji stranku (na svuj session) 
        errorH = ["Unauthorized"]
        return render_template("error.html", errorH = errorH) , 403
    
    conn = sqlite3.connect('beevy.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, email, password, last_login_at FROM users WHERE username=?",(username,))
    user = cursor.fetchone()
    if not user:
        conn.close()
        return "User not found", 404

    if request.method == "POST":
        curPassword = request.form.get('curPassword')
        newPassword = request.form.get('newPassword')
        newPassword2 = request.form.get('newPassword2')

        if not newPassword:
            error = ["New password cannot be empty."]
            return render_template("settingsSecurity.html", error=error, user=user)
        if not bcrypt.checkpw(curPassword.encode('utf-8'),user[3].encode('utf-8')):
            error = ["Current password is incorrect."]
            return render_template("settingsSecurity.html", error=error, user=user)
        if (newPassword!=newPassword2):
            error = ["Passwords do not match."]
            return render_template("settingsSecurity.html",error=error,user=user)
        
        newHash = bcrypt.hashpw(newPassword.encode('utf-8'),bcrypt.gensalt()).decode('utf-8')

        cursor.execute("UPDATE users SET password=? WHERE id=?",(newHash,user[0]))
        conn.commit()
        conn.close()
        return render_template("settingsSecurity.html", user=user)
    conn.close()
    return render_template("settingsSecurity.html", user=user)

@app.route('/<username>/settings/logout',methods=["GET","POST"])
def settingsLogout(username):
    if 'username' not in session: #kontroluje jestli je vytvorena session
        return redirect(url_for("login"))
    if session['username'] != username: #kontroluje zda uzivatel vstupuje na svoji stranku (na svuj session) 
        errorH = ["Unauthorized"]
        return render_template("error.html", errorH = errorH) , 403
    if request.method == "POST":
        session.clear()
        return redirect(url_for("index"))
    return render_template("settingsLogout.html")

@app.route("/<username>/settings/delete")
def settingsDelete(username):
    if 'username' not in session: #kontroluje jestli je vytvorena session
        errorH = ["Login first to access settings"]
        return render_template("login.html",errorH=errorH), 403
    if session['username'] != username: #kontroluje zda uzivatel vstupuje na svoji stranku (na svuj session) 
        errorH = ["Unauthorized"]
        return render_template("error.html", errorH = errorH) , 403
    return render_template("settingsDelete.html")



@app.route('/shop')
def shop():
    errorH = []
    if 'username' not in session:  # kontroluje user je prihlasen
        errorH = ["Log in first to visit shop."]
        return render_template("login.html", errorH=errorH), 403

    conn = sqlite3.connect("beevy.db")
    cursor = conn.cursor()
    cursor.execute("""
        SELECT art.id, art.title, art.price, art.thumbnail_path, users.username
        FROM art
        JOIN users ON art.user_ID = users.id
    """)
    items = cursor.fetchall()
    conn.close()

    # items now include the thumbnail path as item[3]
    return render_template("shop.html", items=items)


@app.route('/shop/<int:art_id>')
def art_detail(art_id):
    errorH = []
    if 'username' not in session:  # kontroluje user je prihlasen
        errorH = ["Log in first to visit shop."]
        return render_template("login.html", errorH=errorH), 403

    conn = sqlite3.connect("beevy.db")
    cursor = conn.cursor()
    cursor.execute("""
        SELECT art.*, users.username
        FROM art
        JOIN users ON art.user_ID = users.id
        WHERE art.id = ?
    """, (art_id,))
    item = cursor.fetchone()
    print(f"Item: {item}")
    conn.close()

    if not item:
        return "Item not found", 404

    # split examples_path into a list for HTML display
    examples_list = item[7].split(",") if item[7] else []

    return render_template("art_detail.html", item=item, examples_list=examples_list)


@app.route("/create_art", methods=["GET", "POST"])
def create_art():
    errorH = []
    username = session.get("username")
    if 'username' not in session:  # kontroluje user je prihlasen
        errorH = ["Log in first to create commissions/art."]
        return render_template("login.html", errorH=errorH), 403

    if request.method == "POST":
        title = request.form["title"]
        description = request.form["description"]
        tat = request.form["tat"]
        price = request.form["price"]
        art_type = request.form["type"]
        slots = request.form.get("slots")
        thumb = request.files["thumbnail"]
        examples = request.files.getlist("examples")
        username = session.get("username")

        # uloží thumbnail
        thumb_path = save_uploaded_file(thumb, UPLOAD_FOLDER)

        examples_paths = []
        for ex in examples:
            if ex.filename:
                ex_path = save_uploaded_file(ex, UPLOAD_FOLDER)
                examples_paths.append(ex_path)

        examples_paths_str = ",".join(examples_paths)


        try:
            conn = sqlite3.connect("beevy.db")
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM users WHERE username = ?",(username,))
            user_row = cursor.fetchone()
            if not user_row:
                return "User not found", 400
            user_id = user_row[0]

            cursor.execute("""
                INSERT INTO art 
                (title, description, tat, price, type, slots, thumbnail_path, examples_path, user_ID)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (title, description, tat, price, art_type, slots, thumb_path, examples_paths_str, user_id))
            conn.commit()
        finally:
            conn.close()

        return redirect("/shop")

    return render_template("create_art.html")

@app.before_request
def load_logged_in_user():
    g.avatar_path = None
    username = session.get('username')
    if username:
        conn = sqlite3.connect('beevy.db')
        cursor = conn.cursor()
        cursor.execute("SELECT avatar_path FROM users WHERE username=?", (username,))
        row = cursor.fetchone()
        conn.close()
        if row and row[0]:
            g.avatar_path = row[0]






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
    socketio.run(app, debug=True, use_reloader=False)