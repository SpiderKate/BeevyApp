from flask import Flask, render_template, request, redirect, url_for, session, flash, g, send_file, abort, send_from_directory
import bcrypt
import sqlite3
import sys
import secrets
import string
import os
import shutil
import uuid
from io import BytesIO
from dotenv import load_dotenv
from werkzeug.utils import secure_filename
from flask_socketio import SocketIO, emit, join_room
from flask_wtf.csrf import CSRFProtect
from datetime import timedelta, datetime
from PIL import Image, ImageDraw, ImageFont, PngImagePlugin
from PIL.PngImagePlugin import PngInfo
from functools import wraps

load_dotenv()
now = datetime.now()

#print('some debug', file=sys.stderr)

app = Flask(__name__)
socketio = SocketIO(app)
csrf = CSRFProtect(app)

#TODO: create canvas folder for saved collab drawings
STATIC_ROOT = "static"
AVATAR_UPLOAD_FOLDER = "uploads/avatar"
UPLOAD_FOLDER = "uploads/shop"
THUMB_FOLDER = "thumbs"
EX_FOLDER = "examples"
ORIG_PATH = "original"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg"}
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024  # 50 MB
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB per file
MAX_HISTORY = 1000
#TODO: add comments

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

def watermark_text_with_metadata(src_path, dest_path, text, metadata: dict):
    img = Image.open(src_path).convert("RGBA")
    watermark = Image.new("RGBA", img.size)
    draw = ImageDraw.Draw(watermark)

    font_size = max(img.size) // 15
    try:
        font = ImageFont.truetype("arial.ttf", font_size)
    except:
        font = ImageFont.load_default()

    bbox = draw.textbbox((0, 0), text, font=font)
    w, h = img.size
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]

    draw.text(
        ((w - tw) // 2, (h - th) // 2),
        text,
        fill=(255, 255, 255, 80),
        font=font
    )

    result = Image.alpha_composite(img, watermark).convert("RGB")

    pnginfo = PngInfo()
    for k, v in metadata.items():
        pnginfo.add_text(k, str(v))

    result.save(dest_path, pnginfo=pnginfo)

#contrls if the files ave the right extension
def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

#valideates the image if they are the right type
def validate_image(file):
    """Validuje, zda je soubor obrázek s povolenou příponou"""
    if not allowed_file(file.filename):
        return False
    try:
        file.seek(0)  # ujistíme se, že čteme od začátku
        img = Image.open(file)
        img.verify()
        file.seek(0)  # pointer zpátky na začátek pro další použití
        return True
    except Exception as e:
        print("Image validation error:", e)
        return False

#adds metadata to the image for better image security
def add_metadata(image_path, author, upload_date, creation_date=None):
    """
    Adds metadata to a PNG image.
    image_path: path to the saved image
    author: str, artwork author
    upload_date: datetime object, when uploaded to Beevy
    creation_date: datetime object, when artwork was created
    """
    try:
        img = Image.open(image_path)
        meta = PngImagePlugin.PngInfo()
        meta.add_text("Author", author)
        meta.add_text("Uploaded on Beevy", upload_date.strftime("%Y-%m-%d %H:%M:%S"))
        if creation_date:
            meta.add_text("Original creation date", creation_date.strftime("%Y-%m-%d %H:%M:%S"))
        meta.add_text("Downloaded from Beevy", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        img.save(image_path, pnginfo=meta)
    except Exception as e:
        print(f"Failed to add metadata to {image_path}: {e}")

# Helper to check ownership
def user_owns_art(user_id, art_id):
    conn = sqlite3.connect("beevy.db")
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 1 FROM art_ownership
        WHERE art_id = ? AND owner_id = ?
    """, (art_id, user_id))
    owns = cursor.fetchone() is not None
    conn.close()
    return owns

#creates @login_required for furher use
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'username' not in session:
            flash("Log in first.", "error")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated

#creates @no_trespass for controlling if user doesnt invade to others sites
def no_trespass(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        username = kwargs.get('username')
        if session.get('username') != username:
            flash("You shall not trespass in other's property.", "error")
            return redirect(url_for("index"))
        return f(*args, **kwargs)
    return decorated

#outputs the stored metadata
def read_png_metadata(file_path):
    """Reads metadata from a PNG file."""
    try:
        img = Image.open(file_path)
        metadata = img.info  # returns dict of PNG text chunks
        return {
            "Author": metadata.get("Author"),
            "Uploaded on Beevy": metadata.get("Uploaded on Beevy"),
            "Original creation date": metadata.get("Original creation date"),
            "Downloaded from Beevy": metadata.get("Downloaded from Beevy")
        }
    except Exception as e:
        print(f"Failed to read metadata from {file_path}: {e}")
        return {}



app.secret_key = os.environ.get("SECRET_KEY") #neni ulozen v kodu :3
if not app.secret_key:
    raise RuntimeError("SECRET_KEY not set")

#session potrva 7 dni pak se cookie smaze
app.permanent_session_lifetime = timedelta(days=7)

#nejprve nacte user badge pred vsim ostatnim
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

#hlavni stranka..
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
                    return redirect(request.url)
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
            return redirect(request.url,page="login")
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
        #form data
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
                #print('username in use')
                flash("Username is already taken.","error")
                a = 1
            if existing_email:
                #print('email in use')
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
        #form data
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
        #print(f"Art: {owned}")

    conn.close()

    return render_template(
        'userPage.html',
        user=user,
        selling=selling,
        owned=owned,
        is_owner=is_owner
    )


@app.route('/join/<room_ID>', methods=['GET','POST'])
@login_required
def join_room_page(room_ID):
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
    if room_type == 1:
        rooms = session.get('verified_rooms', [])
        rooms.append(room_ID)
        session['verified_rooms'] = rooms
        return redirect(url_for('draw', room_ID=room_ID, page="draw"))
    if request.method == 'POST':
        entered_password = request.form['password']
        if password_hash and bcrypt.checkpw(entered_password.encode('utf-8'), password_hash.encode('utf-8')):
            rooms = session.get('verified_rooms', [])
            rooms.append(room_ID)
            session['verified_rooms'] = rooms
            return redirect(url_for('draw', room_ID=room_ID, page="draw"))
        else:
            return render_template('roomPassword.html', error="Wrong password!", room_ID=room_ID)
    return render_template('roomPassword.html', room_ID=room_ID)

@app.route('/draw/<room_ID>')
@login_required
def draw(room_ID):
    rooms = session.get('verified_rooms', [])
    rooms.append(room_ID)
    session["verified_rooms"] = rooms
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
    if room_type == 0 and room_ID not in rooms:
        return redirect(url_for('join_room_page', room_ID=room_ID))
    return render_template('draw.html',room_ID=room_ID, page="draw", brush=brush)

draw_history = {}
@app.route('/create',methods=['GET','POST'])
@login_required
def create():
    username = session.get('username')
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
        room_ID = str(uuid.uuid4())
        try:
            conn = sqlite3.connect('beevy.db')
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM users WHERE username = ?;",(username,))
            User_ID = cursor.fetchone()
            cursor.execute("INSERT INTO rooms (name, password, room_ID, is_public, user_id) VALUES (?, ?, ?, ?, ?)", (name, hash, room_ID, is_public, User_ID[0]))
            conn.commit()
            #print(f"Room created: {name} / {room_ID}")
            
        finally:
            conn.close()
        return redirect(url_for("draw", room_ID=room_ID))
    return render_template("drawCreate.html")

@app.route('/join', methods=['GET'])
@login_required
def join():
    return render_template('drawJoin.html')

#vypisuje vytvorene public rooms linky
@app.route('/join/public')
@login_required
def public():
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
@login_required
def private():
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
@login_required
def option():
    #FIXME: if click button render dif template then redirect
    return render_template('drawOption.html')

#settings...
@app.route('/<username>/settings')
@login_required
@no_trespass
def settings(username):
    return render_template("settings.html")


@app.route("/<username>/settings/profile", methods=["GET", "POST"])
@login_required
@no_trespass
def settingsProfile(username):

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
@login_required
@no_trespass
def settingsAccount(username):
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
@login_required
@no_trespass
def settingsSecurity(username):
    error = []
    
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
@login_required
@no_trespass
def settingsLogout(username):
    if request.method == "POST":
        session.clear()
        flash("Successfully logged out.","success")
        return redirect(url_for("index"))
    return render_template("settingsLogout.html")

@app.route("/<username>/settings/delete", methods=["GET", "POST"])
@login_required
@no_trespass
def settingsDelete(username):

    if request.method == "POST":
        # DELETE confirmation
        if request.form.get("confirm") != "DELETE":
            flash("You must type DELETE exactly.", "info")
            return render_template("settingsDelete.html")

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

#TODO only max 15 on page then click next (smth like carousel)
@login_required
def shop():

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
@login_required
def art_detail(art_id):

    conn = sqlite3.connect("beevy.db")
    cursor = conn.cursor()

    # Fetch artwork and author
    cursor.execute("""
        SELECT art.*, users.username
        FROM art
        JOIN users ON art.author_id = users.id
        WHERE art.id = ?
    """, (art_id,))
    item = cursor.fetchone()
    conn.close()

    if not item:
        return "Item not found", 404

    # Prepare examples list
    examples_list = item[10].split(",") if item[10] else []

    # Check if the current user owns the artwork
    user_id = None
    owns = False
    if "username" in session:
        # Get user id first
        conn = sqlite3.connect("beevy.db")
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE username=?", (session["username"],))
        row = cursor.fetchone()
        conn.close()
        if row:
            user_id = row[0]
            owns = user_owns_art(user_id, art_id)

#BUG: preview/view mode instead only shop view

    return render_template("art_detail.html", item=item, examples_list=examples_list, owns=owns)


@app.route("/<username>/<int:art_id>/edit", methods=["GET", "POST"])
def editArt(username, art_id):
    if "username" not in session:
        flash("Login first.", "error")
        return redirect(url_for("login"))

    if session["username"] != username:
        flash("Unauthorized access.", "error")
        return redirect(url_for("index"))

    conn = sqlite3.connect("beevy.db")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT art.*, users.password
        FROM art
        JOIN users ON art.author_id = users.id
        WHERE art.id = ?
    """, (art_id,))
    item = cursor.fetchone()

    if not item:
        conn.close()
        abort(404)

    examples_list = item[10].split(",") if item[10] else []

    if request.method == "POST":

        confirm_delete = request.form.get("confirmDelete")
        confirm_hide = request.form.get("confirmHide")
        confirm_show = request.form.get("confirmShow")
        password = request.form.get("password")

        # === DELETE ARTWORK ===
        if confirm_delete == "DELETE":
            if not password:
                flash("Password required.", "error")
                return redirect(request.url)

            if not bcrypt.checkpw(password.encode(), item[-1].encode()):
                flash("Wrong password.", "error")
                return redirect(request.url)

            cursor.execute("DELETE FROM art WHERE id = ?", (art_id,))
            conn.commit()
            conn.close()
#TODO: if art deleted owned stays, examples get deleted
#TODO: if no one owns delete everything
            flash("Artwork deleted permanently.", "success")
            return redirect(url_for("shop"))

        # === HIDE ARTWORK ===
        if confirm_hide == "HIDE":
            cursor.execute("""
                UPDATE art SET is_active = 0 WHERE id = ?
            """, (art_id,))
            conn.commit()
            conn.close()

            flash("Artwork hidden.", "success")
            return redirect(url_for("shop"))
        
        if confirm_show == "SHOW":
            cursor.execute("""
                UPDATE art SET is_active = 1 WHERE id = ?
            """, (art_id,))
            conn.commit()
            conn.close()

            flash("Artwork unhidden.", "success")
            return redirect(url_for("shop"))

        # === NORMAL EDIT ===
        new_title = request.form.get("title")
        new_description = request.form.get("description")
        new_slots = request.form.get("slots") or None

        thumb_file = request.files.get("thumbnail")
        examples_files = request.files.getlist("examples")

        thumbnail_path = item[7]
        examples_path = item[10]

        # thumbnail upload
        if thumb_file and thumb_file.filename:
            if not validate_image(thumb_file):
                flash("Invalid thumbnail.", "error")
                return redirect(request.url)

            filename = secure_filename(thumb_file.filename)
            save_path = f"uploads/thumbs/{filename}"
            thumb_file.save(os.path.join("static", save_path))
            thumbnail_path = save_path

        # example images
        if examples_files and examples_files[0].filename:
            new_examples = []
            for ex in examples_files:
                if validate_image(ex):
                    fname = secure_filename(ex.filename)
                    ex_path = f"uploads/examples/{fname}"
                    ex.save(os.path.join("static", ex_path))
                    new_examples.append(ex_path)

            examples_path = ",".join(new_examples)

        cursor.execute("""
            UPDATE art
            SET title = ?, description = ?, slots = ?, thumbnail_path = ?, examples_path = ?
            WHERE id = ?
        """, (
            new_title,
            new_description,
            new_slots,
            thumbnail_path,
            examples_path,
            art_id
        ))

        conn.commit()
        conn.close()

        flash("Artwork updated.", "success")
        return redirect(request.url)

    conn.close()
    return render_template(
        "artEdit.html",
        item=item,
        examples_list=examples_list,
        username=username
    )

@app.route("/shop/<int:art_id>/buy", methods=["GET", "POST"])
#TODO: comms chat
#TODO: comms safe delivery  author to buyer
def buy_art(art_id):
    if "username" not in session:
        flash("Login first to buy artwork.", "error")
        return redirect(url_for("login"))

    conn = sqlite3.connect("beevy.db")
    cursor = conn.cursor()

    # Get user
    cursor.execute("SELECT id, bee_points FROM users WHERE username=?", (session["username"],))
    user = cursor.fetchone()
    if not user:
        conn.close()
        flash("User not found.", "error")
        return redirect(url_for("shop"))
    user_id, user_points = user

    # Get artwork
    cursor.execute("SELECT id, price, author_id, title FROM art WHERE id=?", (art_id,))
    art = cursor.fetchone()
    conn.close()
    if not art:
        flash("Artwork not found.", "error")
        return redirect(url_for("shop"))
    art_id, price, author_id, title = art

    # Prevent author buying own art
    if user_id == author_id:
        flash("You cannot buy your own artwork.", "error")
        return redirect(url_for("art_detail", art_id=art_id))

    # Check ownership using helper
    if user_owns_art(user_id, art_id):
        flash("You already own this artwork.", "info")
        return redirect(url_for("art_detail", art_id=art_id))

    # GET -> show confirmation
    if request.method == "GET":
        return render_template(
            "buy_confirm.html",
            art_id=art_id,
            title=title,
            price=price,
            user_points=user_points
        )

    # POST -> perform purchase
    if user_points < price:
        flash("Not enough BeePoints.", "error")
        return redirect(url_for("art_detail", art_id=art_id))

    try:
        conn = sqlite3.connect("beevy.db")
        cursor = conn.cursor()

        # Subtract points
        cursor.execute("UPDATE users SET bee_points = bee_points - ? WHERE id=?", (price, user_id))

        # Add ownership
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("INSERT INTO art_ownership (art_id, owner_id, acquired_at) VALUES (?, ?, ?)",
                       (art_id, user_id, now))

        conn.commit()
        flash("Artwork purchased successfully!", "success")
    except Exception:
        conn.rollback()
        flash("Purchase failed. Try again.", "error")
    finally:
        conn.close()

    # Update ownership status
    owns = user_owns_art(user_id, art_id)
    return redirect(url_for("art_detail", art_id=art_id, owns=owns))




@app.route("/download/<int:art_id>")
@login_required
def download_art(art_id):
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

    file_rel_path = row[0].replace("\\", "/")
    file_dir = os.path.dirname(file_rel_path)
    file_name = os.path.basename(file_rel_path)
    full_dir = os.path.join(STATIC_ROOT, file_dir)

    if not os.path.exists(os.path.join(full_dir, file_name)):
        abort(404)


    # Clean download name
    download_name = f"beevyDownload{art_id:04d}.png"
    # Optional: read metadata
    metadata = read_png_metadata(os.path.join(full_dir, file_name))
    print("Metadata:", metadata)

    return send_from_directory(full_dir, file_name, as_attachment=True,download_name=download_name)




@app.route("/create_art", methods=["GET", "POST"])
@login_required
#TODO rozdelit for kids or not
#TODO zmensit resolution for thumnail, preview
def create_art():
    if request.method == "POST":
        username = session["username"]

        # --- Form data ---
        title = request.form.get("title")
        description = request.form.get("description")
        tat = request.form.get("tat")
        price = int(request.form.get("price", 0))
        art_type = request.form.get("type")
        slots = request.form.get("slots")
        thumb_file = request.files.get("thumbnail")
        examples_files = request.files.getlist("examples")

        if not thumb_file or not thumb_file.filename:
            flash("Thumbnail is required.", "error")
            return redirect(request.url)

        if not validate_image(thumb_file):
            flash("Invalid thumbnail file.", "error")
            return redirect(request.url)

        os.makedirs(os.path.join(STATIC_ROOT, UPLOAD_FOLDER), exist_ok=True)
        os.makedirs(os.path.join(STATIC_ROOT, UPLOAD_FOLDER, THUMB_FOLDER), exist_ok=True)
        os.makedirs(os.path.join(STATIC_ROOT, UPLOAD_FOLDER, EX_FOLDER), exist_ok=True)
        os.makedirs(os.path.join(STATIC_ROOT, UPLOAD_FOLDER, ORIG_FOLDER), exist_ok=True)

        conn = sqlite3.connect("beevy.db")
        cursor = conn.cursor()
        cursor.execute("""SELECT author_name FROM art
                       JOIN users ON art.author_id = users.id
        """)
        user_row = cursor.fetchone()

        # --- Helper to save + watermark + add metadata ---
        def process_image(file, username, prefix="", save_original=True):
            """
            Saves original image (optional), creates watermarked version with metadata.
            Returns (watermarked_rel_path, original_rel_path or None)
            """

            filename = secure_filename(file.filename)
            file.seek(0)

            # --- folders ---
            base_path = UPLOAD_FOLDER
            thumb_folder = os.path.join(UPLOAD_FOLDER, THUMB_FOLDER)
            example_folder =os.path.join(UPLOAD_FOLDER, EX_FOLDER)
            original_folder = os.path.join(UPLOAD_FOLDER, ORIG_FOLDER)

            for folder in (thumb_folder, example_folder, original_folder):
                os.makedirs(os.path.join(STATIC_ROOT, folder), exist_ok=True)

            # --- ORIGINAL ---
            original_rel_path = None
            full_original_path = None

            if save_original:
                original_rel_path = os.path.join(
                    original_folder,
                    f"{uuid.uuid4().hex}_{filename}"
                ).replace("\\", "/")
                full_original_path = os.path.join(STATIC_ROOT, original_rel_path)

                img = Image.open(file)
                meta = PngInfo()
                meta.add_text("Author", username)
                meta.add_text("Uploaded on Beevy", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                img.save(full_original_path, pnginfo=meta)

                file.seek(0)  # reset for watermarking
            # --- WATERMARKED ---
            target_folder = thumb_folder if prefix == "thumb" else example_folder

            watermarked_rel_path = os.path.join(
                target_folder,
                f"{prefix}_{uuid.uuid4().hex}_{filename}"
            ).replace("\\", "/")

            full_watermarked_path = os.path.join(STATIC_ROOT, watermarked_rel_path)
            cursor.execute("""SELECT author_name FROM art
                        JOIN users ON art.author_id = users.id
                           """)
            author_name = cursor.fetchone()[0]
            metadata = {
                "Author": author_name,
                "Uploaded on Beevy": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "Downloaded from Beevy": "Beevy",
                "Preview": "True" if prefix != "original" else "False"
            }

            watermark_source = full_original_path if full_original_path else file
            watermark_text_with_metadata(
                full_original_path if full_original_path else file,
                full_watermarked_path,
                username,
                metadata
            )
            return watermarked_rel_path, original_rel_path



        # Thumbnail
        thumb_watermarked, original_path = process_image(thumb_file, username, prefix="thumb")

        # Example images
        examples_paths = []
        for ex in examples_files:
            if ex.filename:
                if not validate_image(ex):
                    flash(f"Invalid example file: {ex.filename}", "error")
                    return redirect(request.url)
                ex_wm, ex_original = process_image(ex, username, prefix="example")
                examples_paths.append(ex_wm)    

        if len(examples_paths) > 5:
            flash("Too many example images.", "error")
            return redirect(request.url)

        examples_paths_str = ",".join(examples_paths)

        # --- Save to DB ---
        conn = sqlite3.connect("beevy.db")
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, surname FROM users WHERE username = ?", (username,))
        user_row = cursor.fetchone()
        if not user_row:
            conn.close()
            flash("User not found.", "error")
            return redirect(url_for("index"))

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


@app.route("/preview/<int:art_id>")
@login_required
def preview_art(art_id):
    conn = sqlite3.connect("beevy.db")
    cursor = conn.cursor()
    cursor.execute("SELECT preview_path FROM art WHERE id = ?", (art_id,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        abort(404)

    file_path = os.path.join(STATIC_ROOT, row[0])
    real_path = os.path.realpath(file_path)

    if not real_path.startswith(os.path.realpath(STATIC_ROOT)):
        abort(403)
    if not os.path.exists(real_path):
        abort(404)

    # Read metadata (can be passed to template if needed)
    metadata = read_png_metadata(real_path)

    return send_from_directory(
        STATIC_ROOT,
        os.path.relpath(real_path, STATIC_ROOT)
    )



@socketio.on('join_room')
def handle_join(data):
    room = data['room']
    join_room(room)
    #print(f"Client joined room {room}")
    if room in draw_history:
        emit('draw_history', draw_history[room], to=request.sid)

@socketio.on('draw')
def handle_draw(data):
    room = data['room']
    verified_rooms = session.get('verified_rooms', [])
    if room not in verified_rooms:
        return  # ignore unauthorized draw events

    if room not in draw_history:
        draw_history[room] = []

    draw_history[room].append(data)
    emit('draw', data, to=room, skip_sid=request.sid)
    
if __name__ == "__main__":
    socketio.run(app, debug=False)#, use_reloader=False -> stranky se sami nereload