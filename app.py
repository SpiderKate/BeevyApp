from flask import Flask, render_template, request, redirect, url_for, session, flash, g, send_file, abort
import bcrypt
import sqlite3
import sys
import secrets
import string
import os
import shutil
import uuid, os
from io import BytesIO
from werkzeug.utils import secure_filename
from flask_socketio import SocketIO, emit, join_room
from datetime import timedelta, datetime
from PIL import Image, ImageDraw, ImageFont
from PIL.PngImagePlugin import PngInfo

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

def generate_deleted_username(length=8):
    """
    Generates a unique placeholder username for deleted users.
    Example: Deleted_User_A1B2C3D4
    """
    chars = string.ascii_uppercase + string.digits  # A-Z + 0-9
    random_part = ''.join(secrets.choice(chars) for _ in range(length))
    return f"Deleted_User_{random_part}"
def get_unique_deleted_username(cursor):
    while True:
        username = generate_deleted_username()
        cursor.execute("SELECT 1 FROM users WHERE username=?", (username,))
        if not cursor.fetchone():
            return username

def watermark_text(src_path, dest_path, text):
    """Add semi-transparent text watermark"""
    img = Image.open(src_path).convert("RGBA")
    watermark = Image.new("RGBA", img.size)
    draw = ImageDraw.Draw(watermark)

    font_size = max(img.size) // 15
    try:
        font = ImageFont.truetype("arial.ttf", font_size)
    except:
        font = ImageFont.load_default()

    # Position centered using textbbox
    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]

    w, h = img.size
    draw.text(
        ((w - text_w) // 2, (h - text_h) // 2),
        text,
        fill=(255, 255, 255, 80),
        font=font
    )
    result = Image.alpha_composite(img, watermark)
    result.convert("RGB").save(dest_path)



now = datetime.now()

print('some debug', file=sys.stderr)

app = Flask(__name__)
socketio = SocketIO(app)

app.secret_key = "/,z}it9UGrtMK(<y2lECF]Vb}B2naL]0a2S:7=?MOdYc]D^y"
app.permanent_session_lifetime = timedelta(days=7)

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

@app.route('/')
def index():
    return render_template("index.html", page="index")


@app.route('/login', methods=['GET', 'POST'])
def login():
    login_errors = []
    # Only flash if they are visiting GET /login
    if 'username' in session and request.method == 'GET':
        flash("You are already logged in.", "info")
        return redirect(url_for("userPage", username=session['username']))
    if request.method == 'POST':
        #bere input ze stranky
        usEm = request.form['username']
        password = request.form['password']
        #heslo ze starnky => bytes
        user_bytes = password.encode('utf-8')
        try:
            conn = sqlite3.connect('beevy.db')
            cursor = conn.cursor()
            #hleda heslo bud pro username ci email
            cursor.execute("SELECT password,username,last_login_at,id, deleted FROM users WHERE email=? OR username=?",(usEm, usEm))
            #vysledek se popripadne ulozi sem
            result = cursor.fetchone()
            
            #a kdyz to najde heslo k danému username ci email tak ho zkontroluje
            if result:
                db_pass = result[0]
                if isinstance(result[0], str): #chexks if its a string
                    db_pass = result[0].encode('utf-8') #converts the string to bytes
                    
                #kdyz je spravne posle uzivatele na userPage
                if result[4]:
                    flash("This account has been deleted. You can restore it if you want.", "info")
                    return redirect(url_for("login"))
                if bcrypt.checkpw(user_bytes, db_pass):
                    session.permanent = True
                    session['username'] = result[1]
                    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    cursor.execute("UPDATE users SET last_login_at=? WHERE id=?",(now,result[3]))
                    #print("Rows updated:", cursor.rowcount)
                    conn.commit()
                    flash("Succesfully logged in.","success")
                    return redirect(url_for("userPage", username=session['username']))
                else:
                    login_errors.append("Incorrect username/e-mail or password")
            else:
                login_errors.append("Incorrect username/e-mail or password")
            for err in login_errors:
                flash(err,"error")
            return redirect(url_for("login", page="login"))
        except Exception as e:
            flash(f"Something went wrong: {e}", "error")
            return redirect(url_for("index"))
        finally:
            conn.close()
    else:
        return render_template("login.html", page="login")
    
    
@app.route('/register', methods = ['GET','POST'])
def register():
    # Only flash if they are visiting GET /login
    if 'username' in session and request.method == 'GET':
        flash("You are already registered.", "info")
        return redirect(url_for("userPage", username=session['username']))
    #bere input ze stranky
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        name = request.form['name'].capitalize()
        surname = request.form['surname'].capitalize()
        email = request.form['email']
        dob = request.form['dob']

        if len(username)>20:
            flash("Username is too long.","error")
            return render_template("register.html")
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
            if not existing_email and not existing_user:
                cursor.execute("INSERT INTO users (username, password, name, surname, email, dob) VALUES (?, ?, ?, ?, ?, ?)", (username, hash, name, surname, email, dob))
                conn.commit()
                flash("Registration was successful.","success")
                return redirect(url_for("login", page="login"))
            if existing_user:
                print('username in use')
                flash("Username is already taken.","error")
                a = 1
            if existing_email:
                print('email in use')
                flash("Email is already in use.","error")
                a = 1
            #kdyz nejsou zadne chyby tak input ze stranky zapise do db
            if a==1:
                return redirect(url_for("register", page="register"))
        finally:
            conn.close()
    return render_template("register.html", page="register")        

@app.route("/recover", methods=["GET", "POST"])
def recover_account():
    if request.method == "POST":
        email = request.form.get("email")
        new_username = request.form.get("username")
        password = request.form.get("password")

        if not email or not password:
            flash("Please enter your email and password.", "error")
            return render_template("recover.html")

        conn = sqlite3.connect("beevy.db")
        cursor = conn.cursor()

        try:
            cursor.execute("""
                SELECT id, password, deleted, recovery_username
                FROM users 
                WHERE email = ?
            """, (email,))
            user = cursor.fetchone()

            if not user:
                flash(
                    "If an account with this email exists, you can recover it.",
                    "info"
                )
                return render_template("recover.html")

            user_id, password_hash, deleted, recovery_username = user
            if not bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8")):
                flash("Invalid email or password.", "error")
                return render_template("recover.html")
            
            if deleted == 0:
                flash("This account is already active.", "info")
                return redirect(url_for("login"))
            
            #check old username
            if not new_username:
                cursor.execute(
                    "SELECT id FROM users WHERE username = ?",
                    (recovery_username,)
                )
                taken = cursor.fetchone()

                if taken:
                    flash(
                        "Your previous username is no longer available. Please choose a new one.",
                        "error"
                    )
                    return render_template(
                        "recover.html",
                        ask_username=True,
                        email=email
                    )

                # old username is free → restore
                cursor.execute("""
                    UPDATE users
                    SET deleted = 0,
                        deleted_at = NULL,
                        username = recovery_username
                    WHERE id = ?
                """, (user_id,))
                conn.commit()

            #user provided a new username
            else:
                cursor.execute(
                    "SELECT id FROM users WHERE username = ?",
                    (new_username,)
                )
                if cursor.fetchone():
                    flash("Username is already in use.", "error")
                    return render_template(
                        "recover.html",
                        ask_username=True,
                        email=email
                    )

                cursor.execute("""
                    UPDATE users
                    SET username = ?,
                        deleted = 0,
                        deleted_at = NULL
                    WHERE id = ?
                """, (new_username, user_id))
                conn.commit()

            flash(
                "Your account has been recovered. You can now log in.",
                "success"
            )
            return redirect(url_for("login"))

        finally:
            conn.close()

    return render_template("recover.html")

    


#userpage
@app.route('/<username>')
def userPage(username):
    viewer = session.get('username')
    is_owner = viewer == username
    conn = sqlite3.connect('beevy.db')
    cursor = conn.cursor()

    # fetch user
    cursor.execute("""
        SELECT id, username, bio, avatar_path, bee_points
        FROM users
        WHERE username = ?
    """, (username,))
    user = cursor.fetchone()

    if not user:
        conn.close()
        return "User not found", 404
    #if username == "SpiderKate":
     #   cursor.execute("UPDATE users SET bee_points=? WHERE id=?",(1000000,user[0]))
      #  conn.commit()

    # fetch selling art
    cursor.execute("""
        SELECT id, title, price, thumbnail_path
        FROM art
        WHERE author_id = ?
    """, (user[0],))
    selling = cursor.fetchall()

    # fetch owned art ONLY if owner
    owned = []
    if is_owner:
        cursor.execute("""
            SELECT art.id, art.title, art.thumbnail_path
            FROM art
            JOIN art_ownership ON art.id = art_ownership.art_id
            WHERE art_ownership.owner_id = ?
        """, (user[0],))
        
        owned = cursor.fetchall()
        print(f"Art: {owned}")

    conn.close()

    return render_template(
        'userPage.html',
        user=user,
        selling=selling,
        owned=owned,
        is_owner=is_owner
    )


@app.route('/join/<room_ID>', methods=['GET','POST'])
def join_room_page(room_ID):
    if 'username' not in session: #kontroluje user je prihlasen
        flash("Log in is first to draw.","error")
        return redirect(url_for("login"))
    try:
        conn = sqlite3.connect("beevy.db")
        cursor = conn.cursor()
        cursor.execute("SELECT name, password, is_public FROM rooms WHERE room_ID =?",(room_ID,))
        room = cursor.fetchone()
    finally:
        conn.close()
    if not room:
        flash("Room not found.","error")
        return redirect(url_for("join"))
    room_name, password_hash, room_type = room
    if room_type == True:
        session.setdefault('verified_rooms', []).append(room_ID)
        return redirect(url_for('draw', room_ID=room_ID, page="draw"))
    if request.method == 'POST':
        entered_password = request.form['password']
        if password_hash and bcrypt.checkpw(entered_password.encode('utf-8'), password_hash.encode('utf-8')):
            session.setdefault('verified_rooms', []).append(room_ID)
            return redirect(url_for('draw', room_ID=room_ID, page="draw"))
        else:
            return render_template('roomPassword.html', error="Wrong password!", room_ID=room_ID)
    return render_template('roomPassword.html', room_ID=room_ID)

@app.route('/draw/<room_ID>')
def draw(room_ID):
    verified_rooms = session.get('verified_rooms', [])
    if 'username' not in session: #kontroluje user je prihlasen
        flash("Log in is first to draw.","error")
        return redirect(url_for("login"))
    try:
        username = session.get("username")
        conn = sqlite3.connect("beevy.db")
        cursor = conn.cursor()
        cursor.execute("SELECT is_public FROM rooms WHERE room_ID =?",(room_ID,))
        result = cursor.fetchone()
        cursor.execute("SELECT default_brush_size FROM users WHERE username=?",(username,))
        brush = cursor.fetchone()
    finally:
        conn.close()
    
    if not result:
        flash("Room not found.","error")
        return redirect(url_for("join"))

    room_type = result[0]
    if room_type == 'private' and room_ID not in verified_rooms:
        return redirect(url_for('join_room_page', room_ID=room_ID))
    return render_template('draw.html',room_ID=room_ID, page="draw", brush=brush)

draw_history = {}
@app.route('/create',methods=['GET','POST'])
def create():
    username = session.get('username')
    if 'username' not in session: #kontroluje user je prihlasen
        flash("Log in is first to draw.","error")
        return redirect(url_for("login"))
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
            cursor.execute("INSERT INTO rooms (name, password, room_ID, is_public, user_id) VALUES (?, ?, ?, ?, ?)", (name, hash, room_ID, is_public, User_ID[0]))
            conn.commit()
            print(f"Room created: {name} / {room_ID}")
            
        finally:
            conn.close()
        return redirect(url_for("draw", room_ID=room_ID))
    return render_template("drawCreate.html")

@app.route('/join', methods=['GET'])
def join():
    if 'username' not in session: #kontroluje user je prihlasen
        flash("Log in is first to draw.","error")
        return redirect(url_for("login"))
    return render_template('drawJoin.html')

#vypisuje vytvorene public rooms linky
@app.route('/join/public')
def public():
    if 'username' not in session: #kontroluje user je prihlasen
        flash("Log in is first to draw.","error")
        return redirect(url_for("login"))
    try:
        conn = sqlite3.connect('beevy.db')
        cursor = conn.cursor()
        cursor.execute("""
            SELECT r.name, r.room_ID, u.deleted
            FROM rooms r
            JOIN users u ON r.user_id = u.id AND r.is_public = TRUE
        """)
        rooms = cursor.fetchall()
    finally:
        conn.close()
    return render_template("drawJoinPublic.html", rooms=rooms)

#vypisuje vytvorene private rooms jako linky
@app.route('/join/private')
def private():
    if 'username' not in session: #kontroluje user je prihlasen
        flash("Log in is first to draw.","error")
        return redirect(url_for("login"))
    try:
        conn = sqlite3.connect('beevy.db')
        cursor = conn.cursor()
        cursor.execute("""
            SELECT r.name, r.room_ID, u.deleted
            FROM rooms r
            JOIN users u ON r.user_id = u.id AND r.is_public = FALSE
        """)
        rooms = cursor.fetchall()
    finally:
        conn.close()
    return render_template("drawJoinPrivate.html", rooms=rooms)

@app.route('/option')
def option():
    if 'username' not in session: #kontroluje user je prihlasen
        flash("Log in is first to draw.","error")
        return redirect(url_for("login"))
    return render_template('drawOption.html')

#settings
@app.route('/<username>/settings')
def settings(username):
    if 'username' not in session: #kontroluje jestli je vytvorena session
        flash("Log in first to access settings","error")
        return redirect(url_for("login"))
    if session['username'] != username: #kontroluje zda uzivatel vstupuje na svoji stranku (na svuj session) 
        flash("You shall not trespass in other's property.", "error")
        return redirect(url_for("index"))
    return render_template("settings.html")


@app.route("/<username>/settings/profile", methods=["GET", "POST"])
def settingsProfile(username):
    
    if "username" not in session:
        flash("Log in first to access settings.","error")
        return redirect(url_for("login"))

    if session["username"] != username:
        flash("You shall not trespass in other's property.", "error")
        return redirect(url_for("index"))

    conn = sqlite3.connect("beevy.db")
    cursor = conn.cursor()
    
    try:
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

            cursor.execute("SELECT username FROM users WHERE username = ?", (new_username,))
            db_user = cursor.fetchone()
            if db_user and username!=new_username:
                flash("Username is already in use, please choose another one.","error")
                return render_template("settingsProfile.html", user = user)

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
            # Update session username if changed
            session["username"] = new_username
            flash("Settings saved successfully.","success")
            return redirect(url_for("settingsProfile", username=new_username))
    except Exception as e:
        flash(f"Something went wrong: {e}", "error")
        return redirect(url_for("index"))    
    finally:
        conn.close()
    return render_template("settingsProfile.html", user=user)



@app.route("/<username>/settings/account", methods=["GET","POST"])
def settingsAccount(username):
    if 'username' not in session: #kontroluje jestli je vytvorena session
        flash("Log in first to access settings.","error")
        return redirect(url_for("login"))
    if session['username'] != username: #kontroluje zda uzivatel vstupuje na svoji stranku (na svuj session) 
        flash("You shall not trespass in other's property.", "error")
        return redirect(url_for("index"))
    conn = sqlite3.connect("beevy.db")
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id, email, language, theme, default_brush_size, notifications FROM users WHERE username=?",(username,))
        user = cursor.fetchone()

        if not user:
            conn.close()
            return "User not found", 404
    
    
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
            flash("Settings saved successfully.","success")
            return redirect(url_for("settingsAccount", user=user, username=username))
    except Exception as e:
        flash(f"Something went wrong: {e}", "error")
        return redirect(url_for("index"))
    finally:
            conn.close()
    return render_template("settingsAccount.html", user=user)
    


@app.route("/<username>/settings/security", methods=["GET","POST"])
def settingsSecurity(username):
    error = []
    if 'username' not in session: #kontroluje jestli je vytvorena session
        flash("Log in first to access settings.","error")
        return redirect(url_for("login"))
    if session['username'] != username: #kontroluje zda uzivatel vstupuje na svoji stranku (na svuj session) 
        flash("You shall not trespass in other's property.", "error")
        return redirect(url_for("index"))
    
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
        a=0
        if not newPassword:
            flash("New password cannot be empty.","error")
            a=1
        if not bcrypt.checkpw(curPassword.encode('utf-8'),user[3].encode('utf-8')):
            flash("Current password is incorrect.","error")
            a=1
        if (newPassword!=newPassword2):
            flash("Passwords do not match.","error")
            a=1

        if a==1:
            return render_template("settingsSecurity.html", user=user)
        
        newHash = bcrypt.hashpw(newPassword.encode('utf-8'),bcrypt.gensalt()).decode('utf-8')

        cursor.execute("UPDATE users SET password=? WHERE id=?",(newHash,user[0]))
        conn.commit()
        conn.close()
        flash("Settings saved successfully.","success")

        return render_template("settingsSecurity.html", user=user)
    conn.close()
    return render_template("settingsSecurity.html", user=user)

@app.route('/<username>/settings/logout',methods=["GET","POST"])
def settingsLogout(username):
    if 'username' not in session: #kontroluje jestli je vytvorena session
        flash("Log in first to access settings.","error")
        return redirect(url_for("login"))
    if session['username'] != username: #kontroluje zda uzivatel vstupuje na svoji stranku (na svuj session) 
        flash("You shall not trespass in other's property.", "error")
        return redirect(url_for("index"))
    if request.method == "POST":
        session.clear()
        flash("Successfully logged out.","success")
        return redirect(url_for("index"))
    return render_template("settingsLogout.html")

@app.route("/<username>/settings/delete", methods=["GET", "POST"])
def settingsDelete(username):
    # auth checks
    if "username" not in session:
        flash("Log in first to access settings.", "error")
        return redirect(url_for("login"))

    if session["username"] != username:
        flash("You shall not trespass in other's property.", "error")
        return redirect(url_for("index"))

    if request.method == "POST":
        # DELETE confirmation
        if request.form.get("confirm") != "DELETE":
            flash("You must type DELETE exactly.", "info")
            return redirect(request.url)

        password = request.form.get("password")

        conn = sqlite3.connect("beevy.db")
        cursor = conn.cursor()

        try:
            cursor.execute(
                "SELECT id, password FROM users WHERE username = ? AND deleted = 0;",
                (username,)
            )
            recUsername = username
            user = cursor.fetchone()

            if not user:
                flash("User not found or already deleted.", "error")
                return redirect(url_for("index"))

            user_id, password_hash = user

            # bcrypt check
            if not bcrypt.checkpw(password.encode("utf-8"),password_hash.encode("utf-8")):
                flash("Wrong password.", "error")
                return redirect(request.url)

            # soft delete
            deleted_username = get_unique_deleted_username(cursor)
            deleted_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute("UPDATE users SET deleted=1, deleted_at=?, username=?, recovery_username = ? WHERE id=?",(deleted_at, deleted_username, recUsername, user_id))
            # deactivate rooms
            cursor.execute("UPDATE rooms SET is_active=0 WHERE user_id=?",(user_id,))

            # deactivate art
            cursor.execute("UPDATE art SET is_active=0 WHERE author_id=?",(user_id,))
            conn.commit()
            
            session.clear()
            flash("Account and related content deactivated successfully.", "success")
            return redirect(url_for("index"))

        except Exception as e:
            conn.rollback()
            return f"Something went wrong: {e}"

        finally:
            conn.close()

    return render_template("settingsDelete.html")



@app.route('/shop')
def shop():
    if 'username' not in session:
        flash("Log in first to visit shop.", "error")
        return redirect(url_for("login"))

    conn = sqlite3.connect("beevy.db")
    cursor = conn.cursor()
    cursor.execute("""
        SELECT art.id, art.title, art.price, art.thumbnail_path, users.username, users.deleted
        FROM art
        JOIN users ON art.author_id = users.id
        WHERE users.deleted=0 AND art.is_active=1
    """)
    items = cursor.fetchall()
    conn.close()

    return render_template("shop.html", items=items)

@app.route('/shop/<int:art_id>')
def art_detail(art_id):
    if 'username' not in session:
        flash("Log in first to visit shop.", "error")
        return redirect(url_for("login"))

    conn = sqlite3.connect("beevy.db")
    cursor = conn.cursor()
    cursor.execute("""
        SELECT art.*, users.username
        FROM art
        JOIN users ON art.author_id = users.id
        WHERE art.id = ?
    """, (art_id,))
    item = cursor.fetchone()

    if not item:
        conn.close()
        return "Item not found", 404

    # examples list
    examples_list = item[10].split(",") if item[10] else []

    # check ownership
    cursor.execute("""
        SELECT 1 FROM art_ownership
        WHERE art_id = ? AND owner_id = (SELECT id FROM users WHERE username = ?)
    """, (art_id, session['username']))
    owns = cursor.fetchone() is not None
    conn.close()
    print(f"Item: {item}")

    return render_template("art_detail.html", item=item, examples_list=examples_list, owns=owns)

@app.route("/<username>/<int:art_id>/edit", methods=['GET','POST'])
def editArt(username,art_id):
    if "username" not in session:
        flash("Login first to edit artwork.", "error")
        return redirect(url_for("login"))
    if session["username"] != username:
        flash("You shall not trespass in other's property.", "error")
        return redirect(url_for("index"))
    conn = sqlite3.connect('beevy.db')
    cursor = conn.cursor()
            
    cursor.execute("""
        SELECT art.*, users.username, users.password
        FROM art
        JOIN users ON art.author_id = users.id
        WHERE art.id = ?
    """, (art_id,))
    item = cursor.fetchone()
    examples_list = item[10].split(",") if item[10] else []
    try: 
        if request.method == 'POST':
            new_title = request.form['title']
            new_description = request.form['description']
            new_slots = request.form['slots']
            new_thumb = request.form['thumbnail']
            new_ex = request.form['examples']
            confirmD = request.form['confirmDelete']
            confirmH = request.form['confirmHide']
            password = request.form['password']
            
            if confirmD == 'DELETE' and bcrypt.checkpw(password.encode("utf-8"), (users.password).encode("utf-8")):
                cursor.execute("""
                    DELETE FROM art
                    WHERE id = ?
                """,
                (art.author_id)
                )
                flash('Artwork deleted successfully.','success')
                return redirect(url_for('shop'))

            if confirmH == 'HIDE':
                cursor.execute("""
                    UPDATE art
                    SET is_active = 0
                    WHERE id = ?
                """,
                (art.author_id)
                )
                flash('Artwork hidden successfully.','success')
                return redirect(url_for('shop'))

            cursor.execute("""
                UPDATE art
                SET title = ?, description = ?, slots = ?, thumbnail_path = ?, examples_path = ?
                WHERE id = ?
            """,
            (new_title, new_description, new_slots, new_thumb, new_ex, art.author_id)
            )
    finally:
        conn.close()
    return render_template("artEdit.html", item=item, examples_list=examples_list,username=username)

@app.route("/shop/<int:art_id>/buy", methods=["GET", "POST"])
def buy_art(art_id):
    # Must be logged in
    if "username" not in session:
        flash("Login first to buy artwork.", "error")
        return redirect(url_for("login"))

    conn = sqlite3.connect("beevy.db")
    cursor = conn.cursor()

    # Get user
    cursor.execute(
        "SELECT id, bee_points FROM users WHERE username=?",
        (session["username"],)
    )
    user = cursor.fetchone()

    if not user:
        conn.close()
        flash("User not found.", "error")
        return redirect(url_for("shop"))

    user_id, user_points = user

    # Get artwork
    cursor.execute("""
        SELECT id, price, author_id, title
        FROM art
        WHERE id = ?
    """, (art_id,))
    art = cursor.fetchone()

    if not art:
        conn.close()
        flash("Artwork not found.", "error")
        return redirect(url_for("shop"))

    art_id, price, author_id, title = art

    # Prevent author buying own art
    if user_id == author_id:
        conn.close()
        flash("You cannot buy your own artwork.", "error")
        return redirect(url_for("art_detail", art_id=art_id))

    #Check ownership
    cursor.execute("""
        SELECT 1 FROM art_ownership
        WHERE art_id = ? AND owner_id = ?
    """, (art_id, user_id))

    if cursor.fetchone():
        conn.close()
        flash("You already own this artwork.", "info")
        return redirect(url_for("art_detail", art_id=art_id))
    
    #GET -> Confirmation page
   
    if request.method == "GET":
        conn.close()
        return render_template(
            "buy_confirm.html",
            art_id=art_id,
            title=title,
            price=price,
            user_points=user_points
        )

    #POST -> Perform purchase
    if user_points < price:
        conn.close()
        flash("Not enough BeePoints.", "error")
        return redirect(url_for("art_detail", art_id=art_id))

    try:
        # subtract points
        cursor.execute("""
            UPDATE users
            SET bee_points = bee_points - ?
            WHERE id = ?
        """, (price, user_id))

        # create ownership
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("""
            INSERT INTO art_ownership (art_id, owner_id, acquired_at)
            VALUES (?, ?, ?)
        """, (art_id, user_id, now))
        cursor.execute("""
            SELECT 1 FROM art_ownership
            WHERE art_id = ? AND owner_id = (SELECT id FROM users WHERE username = ?)
        """, (art_id, session["username"]))
        owns = cursor.fetchone() is not None

        conn.commit()
        flash("Artwork purchased successfully!", "success")

    except Exception as e:
        conn.rollback()
        flash("Purchase failed. Try again.", "error")

    finally:
        conn.close()

    return redirect(url_for("art_detail", art_id=art_id, owns=owns))


@app.route("/download/<int:art_id>")
def download_art(art_id):
    if "username" not in session:
        abort(403)

    conn = sqlite3.connect("beevy.db")
    cursor = conn.cursor()
    cursor.execute("""
        SELECT art.original_path, ao.can_download
        FROM art
        JOIN art_ownership ao ON art.id = ao.art_id
        JOIN users u ON ao.owner_id = u.id
        WHERE art.id = ? AND u.username = ?
    """, (art_id, session["username"]))
    row = cursor.fetchone()
    conn.close()

    if not row or not row[1]:
        abort(403)

    file_path = os.path.join(STATIC_ROOT, row[0])
    if not os.path.exists(file_path):
        abort(404)
    return send_file(file_path, as_attachment=True)

@app.route("/create_art", methods=["GET", "POST"])
def create_art():
    if 'username' not in session:
        flash("Log in first to create commissions/art.", "error")
        return redirect(url_for("login"))

    if request.method == "POST":
        title = request.form["title"]
        description = request.form["description"]
        tat = request.form["tat"]
        price = int(request.form["price"])
        art_type = request.form["type"]
        slots = request.form.get("slots")
        thumb_file = request.files["thumbnail"]
        examples_files = request.files.getlist("examples")
        username = session["username"]

        # === READ FILE ONCE ===
        file_bytes = thumb_file.read()
        filename = secure_filename(thumb_file.filename)

        os.makedirs(os.path.join(STATIC_ROOT, UPLOAD_FOLDER), exist_ok=True)

        # === SAVE ORIGINAL (NO WATERMARK) ===
        original_path = os.path.join(
            UPLOAD_FOLDER,
            f"original_{uuid.uuid4().hex}_{filename}"
        )
        with open(os.path.join(STATIC_ROOT, original_path), "wb") as f:
            f.write(file_bytes)

        # === SAVE THUMBNAIL ===
        thumb_path = os.path.join(
            UPLOAD_FOLDER,
            f"thumb_{uuid.uuid4().hex}_{filename}"
        )
        with open(os.path.join(STATIC_ROOT, thumb_path), "wb") as f:
            f.write(file_bytes)

        # === WATERMARK THUMB ===
        thumb_watermarked = thumb_path.replace(".", "_wm.")
        watermark_text(
            os.path.join(STATIC_ROOT, thumb_path),
            os.path.join(STATIC_ROOT, thumb_watermarked),
            username
        )

        # === SAVE EXAMPLES ===
        examples_paths = []
        for ex in examples_files:
            if ex.filename:
                ex_bytes = ex.read()
                ex_filename = secure_filename(ex.filename)

                ex_path = os.path.join(
                    UPLOAD_FOLDER,
                    f"example_{uuid.uuid4().hex}_{ex_filename}"
                )
                with open(os.path.join(STATIC_ROOT, ex_path), "wb") as f:
                    f.write(ex_bytes)

                ex_watermarked = ex_path.replace(".", "_wm.")
                watermark_text(
                    os.path.join(STATIC_ROOT, ex_path),
                    os.path.join(STATIC_ROOT, ex_watermarked),
                    username
                )

                # 🔧 normalize for DB
                examples_paths.append(
                    os.path.normpath(ex_watermarked).replace("\\", "/")
                )

        examples_paths_str = ",".join(examples_paths)

        # 🔧 NORMALIZE ALL PATHS FOR DB
        thumb_watermarked = os.path.normpath(thumb_watermarked).replace("\\", "/")
        original_path = os.path.normpath(original_path).replace("\\", "/")

        # === DATABASE ===
        conn = sqlite3.connect("beevy.db")
        cursor = conn.cursor()

        cursor.execute(
            "SELECT id, name, surname FROM users WHERE username = ?",
            (username,)
        )
        user_row = cursor.fetchone()
        if not user_row:
            conn.close()
            return "User not found", 400

        user_id = user_row[0]
        author_name = f"{user_row[1]} {user_row[2]} - {username}"

        cursor.execute("""
            INSERT INTO art 
            (title, description, tat, price, type, slots,
             thumbnail_path, preview_path, original_path,
             examples_path, author_id, author_name)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            title, description, tat, price, art_type, slots,
            thumb_watermarked, thumb_watermarked, original_path,
            examples_paths_str, user_id, author_name
        ))

        conn.commit()
        conn.close()

        flash("Artwork created successfully!", "success")
        return redirect("/shop")

    return render_template("create_art.html")

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
    socketio.run(app, debug=True)#, use_reloader=False -> stranky se sami nereload