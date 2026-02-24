from flask import Flask, render_template, request, redirect, url_for, session, flash as flask_flash, g, send_file, abort, send_from_directory
import bcrypt
import sqlite3
import sys
import secrets
import string
import os
import shutil
import uuid
import json
from io import BytesIO
from dotenv import load_dotenv
from werkzeug.utils import secure_filename
from flask_socketio import SocketIO, emit, join_room
from flask_wtf.csrf import CSRFProtect
from datetime import timedelta, datetime
from PIL import Image, ImageDraw, ImageFont, PngImagePlugin
from PIL.PngImagePlugin import PngInfo
from functools import wraps
from flask_apscheduler import APScheduler
from backup_utils import backup_database, cleanup_old_backups
from translations import translations

load_dotenv()
now = datetime.now()

#print('some debug', file=sys.stderr)

app = Flask(__name__)
socketio = SocketIO(app)
csrf = CSRFProtect(app)

# ===== Database Backup Scheduler =====
# Configure APScheduler for weekly database backups
app.config['SCHEDULER_API_ENABLED'] = True
scheduler = APScheduler()

def weekly_backup_job():
    """Runs every Sunday at 2 AM"""
    try:
        success, backup_path, message = backup_database()
        if success:
            print(f"✓ Weekly backup completed: {message}", file=sys.stderr)
            # Clean up old backups (keep last 10)
            removed, cleanup_msg = cleanup_old_backups(keep_count=10)
            print(f"✓ {cleanup_msg}", file=sys.stderr)
        else:
            print(f"✗ Weekly backup failed: {message}", file=sys.stderr)
    except Exception as e:
        print(f"✗ Backup job error: {str(e)}", file=sys.stderr)

# Initialize scheduler during app setup (not in before_request)
scheduler.init_app(app)
scheduler.add_job(
    func=weekly_backup_job,
    trigger='cron',
    day_of_week='sun',
    hour=2,
    minute=0,
    id='weekly_backup',
    name='Weekly Database Backup'
)
scheduler.start()

#TODO: create canvas folder for saved collab drawings
STATIC_ROOT = "static"
AVATAR_UPLOAD_FOLDER = "uploads/avatar"
UPLOAD_FOLDER = "uploads/shop"
THUMB_FOLDER = "thumbs"
EX_FOLDER = "examples"
ORIG_FOLDER = "original"
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

def flash_translated(message_key, category="info", **kwargs):
    user_language = session.get('user_language', 'en')
    translated = translations.get(message_key, language=user_language, default=message_key)
    if kwargs:
        translated = translated.format(**kwargs)
    flask_flash(translated, category)

def watermark_text_with_metadata(src_path, dest_path, text, metadata: dict):
    """Draws a tiled, rotated watermark that remains visible on both light and dark images.
    The watermark text is drawn with a dark outline and a lighter semi-transparent fill, repeated
    across the image at a lower opacity but higher coverage so it's always noticeable.
    """
    img = Image.open(src_path).convert("RGBA")
    w, h = img.size

    # build a watermark layer we can tile and rotate
    watermark = Image.new("RGBA", img.size, (0, 0, 0, 0))

    # choose a slightly larger font so watermark is more prominent but lower opacity
    font_size = max(img.size) // 20
    try:
        font = ImageFont.truetype("arial.ttf", font_size)
    except Exception:
        font = ImageFont.load_default()

    # make a single text tile that we will rotate and tile across the watermark layer
    # measure text size
    tmp = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    tmp_draw = ImageDraw.Draw(tmp)
    text_bbox = tmp_draw.textbbox((0, 0), text, font=font)
    tw = text_bbox[2] - text_bbox[0]
    th = text_bbox[3] - text_bbox[1]

    # create text image slightly padded to allow outline
    pad = max(6, font_size // 6)
    tile_w = tw + pad * 2
    tile_h = th + pad * 2
    text_img = Image.new("RGBA", (tile_w, tile_h), (0, 0, 0, 0))
    tile_draw = ImageDraw.Draw(text_img)

    # outline (dark) and main fill (light) with semi-transparent alpha
    outline_alpha = 70  # stronger outline for contrast
    fill_alpha = 30      # softer main text fill
    outline_color = (0, 0, 0, outline_alpha)
    fill_color = (255, 255, 255, fill_alpha)

    x0, y0 = pad, pad
    # draw outline by drawing the text multiple times around center
    offsets = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]
    for ox, oy in offsets:
        tile_draw.text((x0 + ox, y0 + oy), text, font=font, fill=outline_color)
    # draw main text on top
    tile_draw.text((x0, y0), text, font=font, fill=fill_color)

    # rotate the tile for diagonal coverage
    angle = -25
    rotated_tile = text_img.rotate(angle, expand=1)

    # tile rotated_tile across watermark layer with spacing roughly half tile width
    spacing_x = max(40, rotated_tile.width // 2)
    spacing_y = max(40, rotated_tile.height // 2)

    for yy in range(-rotated_tile.height, h + rotated_tile.height, spacing_y):
        for xx in range(-rotated_tile.width, w + rotated_tile.width, spacing_x):
            watermark.alpha_composite(rotated_tile, dest=(xx, yy))

    # optionally reduce overall watermark opacity a bit more to keep it subtle
    combined = Image.alpha_composite(img, watermark)

    # ensure metadata saved in PNG
    pnginfo = PngInfo()
    for k, v in metadata.items():
        pnginfo.add_text(k, str(v))

    # save as PNG to preserve text chunks
    combined.convert("RGB").save(dest_path, format="PNG", pnginfo=pnginfo)

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
            flash_translated("flash.login_first", "error")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated

#creates @no_trespass for controlling if user doesnt invade to others sites
def no_trespass(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        username = kwargs.get('username')
        if session.get('username') != username:
            flash_translated("flash.trespass", "error")
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


def process_uploaded_image(file, username, prefix="", save_original=True, author_name=None):
    """Saves an original PNG (optional), creates a watermarked PNG with metadata.
    Returns tuple (watermarked_rel_path, original_rel_path_or_None).
    """
    filename = secure_filename(file.filename)
    base_name = os.path.splitext(filename)[0]
    file.seek(0)

    thumb_folder = os.path.join(UPLOAD_FOLDER, THUMB_FOLDER)
    example_folder = os.path.join(UPLOAD_FOLDER, EX_FOLDER)
    original_folder = os.path.join(UPLOAD_FOLDER, ORIG_FOLDER)

    for folder in (thumb_folder, example_folder, original_folder):
        os.makedirs(os.path.join(STATIC_ROOT, folder), exist_ok=True)

    original_rel_path = None
    full_original_path = None

    if save_original:
        original_rel_path = os.path.join(
            original_folder,
            f"{uuid.uuid4().hex}_{base_name}.png"
        ).replace("\\", "/")
        full_original_path = os.path.join(STATIC_ROOT, original_rel_path)

        img = Image.open(file)
        img = img.convert("RGBA")
        meta = PngInfo()
        # resolve author name if not provided
        if not author_name:
            try:
                conn = sqlite3.connect("beevy.db")
                cursor = conn.cursor()
                cursor.execute("SELECT name, surname FROM users WHERE username = ?", (username,))
                ur = cursor.fetchone()
                conn.close()
                if ur:
                    author_name = f"{ur[0]} {ur[1]} - {username}"
                else:
                    author_name = username
            except Exception:
                author_name = username

        meta.add_text("Author", author_name)
        meta.add_text("Uploaded on Beevy", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        img.save(full_original_path, pnginfo=meta, format="PNG")
        file.seek(0)

    target_folder = thumb_folder if prefix == "thumb" else example_folder

    watermarked_rel_path = os.path.join(
        target_folder,
        f"{prefix}_{uuid.uuid4().hex}_{base_name}.png"
    ).replace("\\", "/")

    full_watermarked_path = os.path.join(STATIC_ROOT, watermarked_rel_path)

    metadata = {
        "Author": author_name if author_name else username,
        "Uploaded on Beevy": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "Downloaded from Beevy": "Beevy",
        "Preview": "True" if prefix != "original" else "False"
    }

    watermark_text_with_metadata(
        full_original_path if full_original_path else file,
        full_watermarked_path,
        username,
        metadata
    )

    return watermarked_rel_path, original_rel_path



app.secret_key = os.environ.get("SECRET_KEY") #neni ulozen v kodu :3
if not app.secret_key:
    raise RuntimeError("SECRET_KEY not set")

#session potrva 7 dni pak se cookie smaze
app.permanent_session_lifetime = timedelta(days=7)

#nejprve nacte user badge pred vsim ostatnim
@app.before_request
def load_logged_in_user():
    g.avatar_path = None
    g.user_theme = 'bee'
    g.user_language = session.get("user_language", "en")
    g.trans = translations

    username = session.get('username')
    if username:
        conn = sqlite3.connect('beevy.db')
        cursor = conn.cursor()

        cursor.execute("SELECT avatar_path FROM users WHERE username=?", (username,))
        row = cursor.fetchone()
        if row and row[0]:
            g.avatar_path = row[0]

        cursor.execute("SELECT theme FROM preferences WHERE user_id = (SELECT id FROM users WHERE username=?)", (username,))
        pref_row = cursor.fetchone()
        if pref_row and pref_row[0]:
            g.user_theme = pref_row[0]

        conn.close()
        
@app.context_processor
def inject_t():
    def t(key, **kwargs):
        text = translations.get(key, g.user_language, default=key)
        if kwargs:
            text = text.format(**kwargs)
        return text
    return dict(t=t)


#hlavni stranka..
@app.route('/')
def index():
    return render_template("index.html", page="index")


@app.route('/health')
def health():
    return {"status": "ok"}, 200

@app.route('/login', methods=['GET', 'POST'])
def login():
    login_errors = []
    # Only flash if they are visiting GET /login
    if 'username' in session and request.method == 'GET':
        flash_translated("flash.already_logged_in", "info")
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
            cursor.execute("SELECT password,username,id, deleted FROM users WHERE email=? OR username=?",(usEm, usEm))
            #vysledek se popripadne ulozi sem
            result = cursor.fetchone()
            db_pass, username, id, deleted = result

            cursor.execute("SELECT language FROM preferences WHERE user_id = ?", (id,)) 
            row = cursor.fetchone()

            if row:
                session["user_language"] = row[0]
            
            
            #a kdyz to najde heslo k danému username ci email tak ho zkontroluje
            if result:
                if isinstance(db_pass, str): #chexks if its a string
                    db_pass = db_pass.encode('utf-8') #converts the string to bytes
                    
                #kdyz je spravne posle uzivatele na userPage
                if deleted:
                    flash_translated("flash.account_deleted", "info")
                    return redirect(request.url)
                if bcrypt.checkpw(user_bytes, db_pass):
                    session.permanent = True
                    session['username'] = username
                    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    cursor.execute("UPDATE users SET last_login_at=? WHERE id=?",(now,id))
                    conn.commit()
                    #print("Rows updated:", cursor.rowcount)
                    flash_translated("flash.login_success", "success")
                    return redirect(url_for("userPage", username=session['username']))
                else:
                    flash_translated("flash.invalid_credentials", "error")
            else:
                flash_translated("flash.invalid_credentials", "error")
            return redirect(request.url,page="login")
        except Exception as e:
            flash_translated("flash.error_occurred", "error", e=str(e))
            return redirect(url_for("index"))
        finally:
            conn.close()
    else:
        return render_template("login.html", page="login")
    
    
@app.route('/register', methods = ['GET','POST'])
def register():
    # Only flash if they are visiting GET /login
    if 'username' in session and request.method == 'GET':
        flash_translated("flash.already_registered", "info")
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
            flash_translated("flash.username_too_long", "error")
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
                user_id = cursor.lastrowid
                # create default preferences for new user
                cursor.execute("INSERT INTO preferences (user_id, language, theme, default_brush_size, notifications) VALUES (?,?,?,?,?)", (user_id, 'en', 'bee', 30, 1))
                conn.commit()
                flash_translated("flash.registration_success", "success")
                return redirect(url_for("login", page="login"))
            if existing_user:
                #print('username in use')
                flash_translated("flash.username_taken", "error")
                a = 1
            if existing_email:
                #print('email in use')
                flash_translated("flash.email_in_use", "error")
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
            flash_translated("flash.enter_credentials", "error")
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
                flash_translated("flash.if_account_exists", "info")
                return render_template("recover.html")

            user_id, password_hash, deleted, recovery_username = user
            if not bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8")):
                flash_translated("flash.invalid_credentials", "error")
                return render_template("recover.html")
            
            if deleted == 0:
                flash_translated("flash.account_already_active", "info")
                return redirect(url_for("login"))
            
            #check old username
            if not new_username:
                cursor.execute(
                    "SELECT id FROM users WHERE username = ?",
                    (recovery_username,)
                )
                taken = cursor.fetchone()

                if taken:
                    flash_translated("flash.username_in_use", "error")
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
                    flash_translated("flash.username_in_use", "error")
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

            flash_translated("flash.account_recovery_help", "success")
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
        flash_translated("flash.user_not_found", "error")
        return "", 404
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
            SELECT art.id, art.title, art.thumbnail_path, art_ownership.source
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
        flash_translated("flash.room_not_found", "error")
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
        cursor.execute("SELECT default_brush_size FROM preferences WHERE user_id=(SELECT id FROM users WHERE username=?)",(username,))
        brush = cursor.fetchone()

    finally:
        conn.close()
    
    if not result:
        flash_translated("flash.room_not_found", "error")
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
print("wrrwrwr")
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
    return render_template("drawJoinPrivate.html", roomsP=rooms)

@app.route('/option')
@login_required
def option():
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
            flash_translated("flash.user_not_found", "error")
            return "", 404

        if request.method == "POST":
            new_username = request.form.get("username")
            new_bio = request.form.get("bio")
            avatar = request.files.get("avatar")

            cursor.execute("SELECT username FROM users WHERE username = ?", (new_username,))
            db_user = cursor.fetchone()
            if db_user and username!=new_username:
                flash_translated("flash.username_taken", "error")
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
            flash_translated("flash.settings_saved", "success")
            return redirect(url_for("settingsProfile", username=new_username))
    except Exception as e:
        flash_translated("flash.error_occurred", "error", e=str(e))
        return redirect(url_for("index"))    
    finally:
        conn.close()
    return render_template("settingsProfile.html", user=user)


@app.route("/<username>/settings/preferences", methods=["GET", "POST"])
@login_required
@no_trespass
def settingsPreferences(username):
    conn = sqlite3.connect("beevy.db")
    cursor = conn.cursor()
    try:
        # get basic user info
        cursor.execute("SELECT id FROM users WHERE username=?", (username,))
        user_id = cursor.fetchone()[0]
        

        if not user_id:
            conn.close()
            flash_translated("flash.user_not_found", "error")
            return "", 404
        
    # get preferences (create defaults if missing)
        cursor.execute("SELECT language, theme, default_brush_size, notifications FROM preferences WHERE user_id = ?", (user_id,))
        prefs = cursor.fetchone()
        if not prefs:
            prefs = ('en', 'bee', 30, 1)
            cursor.execute(
                "INSERT INTO preferences (user_id, language, theme, default_brush_size, notifications) VALUES (?,?,?,?,?)",
                (user_id, prefs[0], prefs[1], prefs[2], prefs[3])
            )
            conn.commit()
        
        # assemble tuple expected by template: (id, language, theme, default_brush_size, notifications)
        user = (user_id, prefs[0], prefs[1], prefs[2], prefs[3])

        if request.method == "POST":
            new_language = request.form.get("language")
            new_theme = request.form.get("theme")
            new_brush = int(request.form.get("brush") or prefs[2])
            new_not = 1 if request.form.get("not") else 0  # handle checkbox

            # update or insert preferences
            cursor.execute("SELECT 1 FROM preferences WHERE user_id = ?", (user_id,))
            if cursor.fetchone():
                cursor.execute(
                    "UPDATE preferences SET language = ?, theme = ?, default_brush_size = ?, notifications = ? WHERE user_id = ?",
                    (new_language, new_theme, new_brush, new_not, user_id)
                )
            else:
                cursor.execute(
                    "INSERT INTO preferences (user_id, language, theme, default_brush_size, notifications) VALUES (?,?,?,?,?)",
                    (user_id, new_language, new_theme, new_brush, new_not)
                )
            conn.commit()
            session["user_language"] = new_language
            flash_translated("flash.settings_saved", "success")
            return redirect(url_for("settingsPreferences", username=username))
    except Exception as e:
        flash_translated("flash.error_occurred", "error", e=str(e))
        return redirect(url_for("index"))
    finally:
        conn.close()
    return render_template("settingsPreferences.html", user=user)


@app.route("/<username>/settings/account", methods=["GET","POST"])
@login_required
@no_trespass
def settingsAccount(username):
    conn = sqlite3.connect("beevy.db")
    cursor = conn.cursor()
    try:
        # get basic user info
        cursor.execute("SELECT id, email FROM users WHERE username=?", (username,))
        user_row = cursor.fetchone()

        if not user_row:
            conn.close()
            flash_translated("flash.user_not_found", "error")
            return "", 404

        user_id, email = user_row
        
        # assemble tuple expected by template: (id, email)
        user = (user_id, email)

        if request.method == "POST":
            new_email = request.form.get("email")

            # update users email
            cursor.execute(
                "UPDATE users SET email = ? WHERE id = ?",
                (new_email, user_id)
            )
            flash_translated("flash.settings_saved", "success")
            return redirect(url_for("settingsAccount", username=username))
    except Exception as e:
        flash_translated("flash.error_occurred", "error", e=str(e))
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
        flash_translated("flash.user_not_found", "error")
        return "", 404

    if request.method == "POST":
        curPassword = request.form.get('curPassword')
        newPassword = request.form.get('newPassword')
        newPassword2 = request.form.get('newPassword2')
        a=0
        if not newPassword:
            flash_translated("flash.password_empty", "error")
            a=1
        if not bcrypt.checkpw(curPassword.encode('utf-8'),user[3].encode('utf-8')):
            flash_translated("flash.password_incorrect", "error")
            a=1
        if (newPassword!=newPassword2):
            flash_translated("flash.passwords_mismatch", "error")
            a=1

        if a==1:
            return render_template("settingsSecurity.html", user=user)
        
        newHash = bcrypt.hashpw(newPassword.encode('utf-8'),bcrypt.gensalt()).decode('utf-8')

        cursor.execute("UPDATE users SET password=? WHERE id=?",(newHash,user[0]))
        conn.commit()
        conn.close()
        flash_translated("flash.settings_saved", "success")

        return render_template("settingsSecurity.html", user=user)
    conn.close()
    return render_template("settingsSecurity.html", user=user)

@app.route('/<username>/settings/logout',methods=["GET","POST"])
@login_required
@no_trespass
def settingsLogout(username):
    if request.method == "POST":
        session.clear()
        flash_translated("flash.logout_success", "success")
        return redirect(url_for("index"))
    return render_template("settingsLogout.html")

@app.route("/<username>/settings/delete", methods=["GET", "POST"])
@login_required
@no_trespass
def settingsDelete(username):

    if request.method == "POST":
        # DELETE confirmation
        if request.form.get("confirm") != "DELETE":
            flash_translated("flash.must_type_delete", "info")
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
                flash_translated("flash.user_not_found", "error")
                return redirect(url_for("index"))

            user_id, password_hash = user

            # bcrypt check
            if not bcrypt.checkpw(password.encode("utf-8"),password_hash.encode("utf-8")):
                flash_translated("flash.wrong_password", "error")
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
            flash_translated("flash.account_deactivated", "success")
            return redirect(url_for("index"))

        except Exception as e:
            conn.rollback()
            flash_translated("flash.error_occurred", "error", e=str(e))

        finally:
            conn.close()

    return render_template("settingsDelete.html")



@app.route('/shop')

#TODO only max 15 on page then click next (smth like carousel) and randomly mix them up to refersh the content
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
# TODO: css buy art
@app.route('/shop/<int:art_id>')
@login_required
def art_detail(art_id):

    conn = sqlite3.connect("beevy.db")
    cursor = conn.cursor()

    # Fetch artwork and optional author (allow author to be NULL after deletion)
    cursor.execute("""
        SELECT art.*,users.bee_points, users.username
        FROM art
        LEFT JOIN users ON art.author_id = users.id
        WHERE art.id = ?
    """, (art_id,))
    item = cursor.fetchone()

    if not item:
        conn.close()
        return "Item not found", 404

    # Prepare examples list
    examples_list = item[10].split(",") if item[10] else []

    # Determine active state
    is_active = bool(item[13])

    # Check if the current user owns the artwork and determine which image to show
    user_id = None
    owns = False
    owned_image = None
    is_author = False
    if "username" in session:
        # Get user id first
        cursor.execute("SELECT id FROM users WHERE username=?", (session["username"],))
        row = cursor.fetchone()
        if row:
            user_id = row[0]
            owns = user_owns_art(user_id, art_id)
            is_author = (session.get("username") == item[-1])
            if owns:
                # Prefer owner-specific source if we created copies for owners
                cursor.execute("SELECT source FROM art_ownership WHERE art_id = ? AND owner_id = ?", (art_id, user_id))
                src_row = cursor.fetchone()
                if src_row and src_row[0]:
                    owned_image = src_row[0]
                else:
                    owned_image = item[9]  # original_path

    # If item is inactive (deleted from shop) only allow owners or authors to view it
    if not is_active and not owns and not is_author:
        conn.close()
        abort(404)

    # If the current user owns this art (and is not the author), redirect to owned view
    if owns and not is_author:
        conn.close()
        return redirect(url_for('owned_view', art_id=art_id))

    conn.close()
    return render_template("art_detail.html", item=item, examples_list=examples_list, owns=owns, owned_image=owned_image, is_author=is_author, is_active=is_active)


@app.route('/owned/<int:art_id>', methods=['GET'])
@login_required
def owned_view(art_id):
    """Owner-only view showing artwork details, thumbnail, examples, download and remove ownership button."""
    conn = sqlite3.connect("beevy.db")
    cursor = conn.cursor()

    # Fetch artwork and author
    cursor.execute("""
        SELECT art.*, users.username
        FROM art
        LEFT JOIN users ON art.author_id = users.id
        WHERE art.id = ?
    """, (art_id,))
    item = cursor.fetchone()

    if not item:
        conn.close()
        abort(404)

    # Get current user id
    cursor.execute("SELECT id FROM users WHERE username = ?", (session.get('username'),))
    row = cursor.fetchone()
    if not row:
        conn.close()
        abort(403)
    user_id = row[0]

    # Verify ownership
    owns = user_owns_art(user_id, art_id)
    is_author = (session.get('username') == item[-1])
    if not owns and not is_author:
        conn.close()
        abort(403)

    # Prepare examples list
    examples_list = item[10].split(",") if item[10] else []

    # Determine active state
    is_active = bool(item[13])

    # Get owned image (prefer owner-specific copy or original)
    owned_image = None
    if owns:
        cursor.execute("SELECT source FROM art_ownership WHERE art_id = ? AND owner_id = ?", (art_id, user_id))
        src_row = cursor.fetchone()
        if src_row and src_row[0]:
            owned_image = src_row[0]
        else:
            owned_image = item[9]  # original_path

    conn.close()
    return render_template("owned_detail.html", item=item, examples_list=examples_list, owns=owns, owned_image=owned_image, is_author=is_author, is_active=is_active)


@app.route('/owned/<int:art_id>/remove', methods=['POST'])
@login_required
def remove_ownership(art_id):
    """Remove the current user's ownership of an artwork.
    - If there are other owners, only remove the ownership record and delete the owner's copy.
    - If the user was the only owner and the art is inactive, also delete the art row and any remaining files.
    """
    conn = sqlite3.connect("beevy.db")
    cursor = conn.cursor()

    # get current user id
    cursor.execute("SELECT id FROM users WHERE username = ?", (session.get('username'),))
    row = cursor.fetchone()
    if not row:
        conn.close()
        abort(403)
    user_id = row[0]

    # verify ownership
    cursor.execute("SELECT id, source FROM art_ownership WHERE art_id = ? AND owner_id = ?", (art_id, user_id))
    ownership = cursor.fetchone()
    if not ownership:
        conn.close()
        flash_translated("flash.not_owner", "error")
        return redirect(url_for('userPage', username=session.get('username')))

    ownership_id, source_rel = ownership

    # count owners
    cursor.execute("SELECT COUNT(*) FROM art_ownership WHERE art_id = ?", (art_id,))
    owners_count = cursor.fetchone()[0]

    # get art info
    cursor.execute("SELECT thumbnail_path, preview_path, original_path, examples_path, is_active FROM art WHERE id = ?", (art_id,))
    art_row = cursor.fetchone()
    if not art_row:
        # nothing to do
        cursor.execute("DELETE FROM art_ownership WHERE id = ?", (ownership_id,))
        conn.commit()
        conn.close()
        flash_translated("flash.ownership_removed", "success")
        return redirect(url_for('userPage', username=session.get('username')))

    thumb_rel, preview_rel, orig_rel, examples_rel, is_active = art_row

    # remove owner's copy file if present
    if source_rel:
        full = os.path.join(STATIC_ROOT, source_rel)
        try:
            if os.path.exists(full):
                os.remove(full)
        except Exception as e:
            print("Failed to remove owner file:", e)

    # delete ownership record
    cursor.execute("DELETE FROM art_ownership WHERE id = ?", (ownership_id,))

    # if this was the only owner and art is inactive => delete art and its files
    if owners_count <= 1 and not is_active:
        # delete any remaining stored files
        for rel in (thumb_rel, preview_rel, orig_rel):
            if rel:
                full = os.path.join(STATIC_ROOT, rel)
                try:
                    if os.path.exists(full):
                        os.remove(full)
                except Exception:
                    pass
        if examples_rel:
            for ex in examples_rel.split(','):
                full = os.path.join(STATIC_ROOT, ex)
                try:
                    if os.path.exists(full):
                        os.remove(full)
                except Exception:
                    pass
        # delete art row
        cursor.execute("DELETE FROM art WHERE id = ?", (art_id,))
        conn.commit()
        conn.close()
        flash_translated("flash.ownership_removed_cleanup", "success")
        return redirect(url_for('userPage', username=session.get('username')))

    conn.commit()
    conn.close()
    flash_translated("flash.ownership_removed", "success")
    return redirect(url_for('userPage', username=session.get('username')))


@app.route("/<username>/<int:art_id>/edit", methods=["GET", "POST"])
@login_required
@no_trespass
def editArt(username, art_id):
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
                flash_translated("flash.password_required", "error")
                return redirect(request.url)

            if not bcrypt.checkpw(password.encode(), item[-1].encode()):
                flash_translated("flash.wrong_password", "error")
                return redirect(request.url)

            try:
                # Determine owners for this artwork
                cursor.execute("SELECT id, owner_id FROM art_ownership WHERE art_id = ?", (art_id,))
                owners = cursor.fetchall()

                thumb_rel = item[7]
                preview_rel = item[8]
                original_rel = item[9]
                examples_rel = item[10] or ""

                def rel_to_full(rel):
                    if not rel:
                        return None
                    return os.path.join(STATIC_ROOT, rel)

                # If no owners, remove all files and DB row
                if not owners:
                    for rel in (thumb_rel, preview_rel, original_rel):
                        if rel:
                            full = rel_to_full(rel)
                            try:
                                if os.path.exists(full):
                                    os.remove(full)
                            except Exception:
                                pass
                    if examples_rel:
                        for ex in examples_rel.split(","):
                            full = rel_to_full(ex)
                            try:
                                if os.path.exists(full):
                                    os.remove(full)
                            except Exception:
                                pass
                    cursor.execute("DELETE FROM art WHERE id = ?", (art_id,))
                    conn.commit()
                    conn.close()
                    flash_translated("flash.artwork_deleted", "success")
                    return redirect(url_for("shop"))

                # Owners exist: copy original (or best available) for each owner and update art_ownership.source
                owned_dir = os.path.join(STATIC_ROOT, UPLOAD_FOLDER, "owned")
                os.makedirs(owned_dir, exist_ok=True)

                src_rel = original_rel or preview_rel or thumb_rel
                src_full = rel_to_full(src_rel)

                for ownership_id, owner_id in owners:
                    try:
                        if src_full and os.path.exists(src_full):
                            dest_filename = f"{uuid.uuid4().hex}_{os.path.basename(src_rel)}"
                            dest_rel = os.path.join(UPLOAD_FOLDER, "owned", dest_filename).replace("\\", "/")
                            dest_full = os.path.join(STATIC_ROOT, dest_rel)
                            # ensure parent dir exists
                            os.makedirs(os.path.dirname(dest_full), exist_ok=True)
                            shutil.copy2(src_full, dest_full)
                            cursor.execute("UPDATE art_ownership SET source = ? WHERE id = ?", (dest_rel, ownership_id))
                    except Exception as e:
                        print("Failed to create owner copy:", e)

                # Remove public files and anonymize/hide the art from the shop
                for rel in (thumb_rel, preview_rel, original_rel):
                    if rel:
                        full = rel_to_full(rel)
                        try:
                            if os.path.exists(full):
                                os.remove(full)
                        except Exception:
                            pass
                if examples_rel:
                    for ex in examples_rel.split(","):
                        full = rel_to_full(ex)
                        try:
                            if os.path.exists(full):
                                os.remove(full)
                        except Exception:
                            pass

                deleted_username = get_unique_deleted_username(cursor)
                cursor.execute("""
                    UPDATE art SET author_id = NULL, is_active = 0, thumbnail_path = '', preview_path = '', original_path = ''
                    WHERE id = ?
                """, (art_id,))
                conn.commit()
                conn.close()
                flash_translated("flash.artwork_deleted_shop", "success")
                return redirect(url_for("shop"))
            except Exception as e:
                # Rollback and surface an error instead of 500
                try:
                    conn.rollback()
                except Exception:
                    pass
                conn.close()
                print("Delete artwork failed:", e)
                flash_translated("flash.delete_failed", "error")
                return redirect(request.url)

        # === HIDE ARTWORK ===
        if confirm_hide == "HIDE":
            cursor.execute("""
                UPDATE art SET is_active = 0 WHERE id = ?
            """, (art_id,))
            conn.commit()
            conn.close()

            flash_translated("flash.artwork_hidden", "success")
            return redirect(url_for("shop"))
        
        if confirm_show == "SHOW":
            cursor.execute("""
                UPDATE art SET is_active = 1 WHERE id = ?
            """, (art_id,))
            conn.commit()
            conn.close()

            flash_translated("flash.artwork_unhidden", "success")
            return redirect(url_for("shop"))

        # === NORMAL EDIT ===
        new_title = request.form.get("title")
        new_description = request.form.get("description")
        new_slots = request.form.get("slots") or None

        thumb_file = request.files.get("thumbnail")
        examples_files = request.files.getlist("examples")

        # Resolve author display name for metadata
        cursor.execute("SELECT id, name, surname FROM users WHERE username = ?", (session['username'],))
        user_row = cursor.fetchone()
        author_name = f"{user_row[1]} {user_row[2]} - {session['username']}" if user_row else session['username']

        thumbnail_path = item[7]
        examples_path = item[10]
        original_path = item[9]

        # thumbnail upload
        if thumb_file and thumb_file.filename:
            # --- size check ---
            try:
                thumb_file.stream.seek(0, os.SEEK_END)
                size = thumb_file.stream.tell()
                thumb_file.stream.seek(0)
            except Exception:
                size = None

            if size and size > MAX_FILE_SIZE:
                flash_translated("flash.thumbnail_too_large", "error")
                return redirect(request.url)

            # --- extension/type check ---
            if not allowed_file(thumb_file.filename):
                flash_translated("flash.invalid_thumbnail", "error")
                return redirect(request.url)

            if not validate_image(thumb_file):
                flash_translated("flash.invalid_thumbnail", "error")
                return redirect(request.url)

            # save with watermark + metadata
            thumb_watermarked, thumb_original = process_uploaded_image(thumb_file, session['username'], prefix="thumb", author_name=author_name)
            thumbnail_path = thumb_watermarked
            original_path = thumb_original

        # example images
        if examples_files and examples_files[0].filename:
            new_examples = []
            for ex in examples_files:
                if not validate_image(ex):
                    flash_translated("flash.invalid_example_file", "error", filename=ex.filename)
                    return redirect(request.url)

                # size check
                try:
                    ex.stream.seek(0, os.SEEK_END)
                    ex_size = ex.stream.tell()
                    ex.stream.seek(0)
                except Exception:
                    ex_size = None

                if ex_size and ex_size > MAX_FILE_SIZE:
                    flash_translated("flash.ex_file_too_large", "error", ex=ex)
                    return redirect(request.url)

                ex_wm, ex_original = process_uploaded_image(ex, session['username'], prefix="example", author_name=author_name)
                new_examples.append(ex_wm)

            examples_path = ",".join(new_examples)

        cursor.execute("""
            UPDATE art
            SET title = ?, description = ?, slots = ?, thumbnail_path = ?, examples_path = ?, original_path = ?
            WHERE id = ?
        """, (
            new_title,
            new_description,
            new_slots,
            thumbnail_path,
            examples_path,
            original_path,
            art_id
        ))
        conn.commit()
        conn.close()

        flash_translated("flash.artwork_updated", "success")
        return redirect(request.url)

    conn.close()
    return render_template(
        "artEdit.html",
        item=item,
        examples_list=examples_list,
        username=username,
        max_file_size=MAX_FILE_SIZE,
        allowed_extensions=list(ALLOWED_EXTENSIONS)
    )

@app.route("/shop/<int:art_id>/buy", methods=["GET", "POST"])
@login_required
#TODO: comms chat
#TODO: comms safe delivery  author to buyer
def buy_art(art_id):

    conn = sqlite3.connect("beevy.db")
    cursor = conn.cursor()

    # Get user
    cursor.execute("SELECT id, bee_points FROM users WHERE username=?", (session["username"],))
    user = cursor.fetchone()
    if not user:
        conn.close()
        flash_translated("flash.user_not_found", "error")
        return redirect(url_for("shop"))
    user_id, user_points = user

    # Get artwork
    cursor.execute("SELECT id, price, author_id, title FROM art WHERE id=?", (art_id,))
    art = cursor.fetchone()
    conn.close()
    if not art:
        flash_translated("flash.artwork_not_found", "error")
        return redirect(url_for("shop"))
    art_id, price, author_id, title = art

    # Prevent author buying own art
    if user_id == author_id:
        flash_translated("flash.artwork_cannot_buy_own", "error")
        return redirect(url_for("art_detail", art_id=art_id))

    # Check ownership using helper
    if user_owns_art(user_id, art_id):
        flash_translated("flash.already_owned", "info")
        return redirect(url_for("art_detail", art_id=art_id))

    # GET -> show confirmation
    if request.method == "GET":
        if user_points < price:
            flash_translated("flash.insufficient_points", "error")
            return redirect(url_for("art_detail", art_id=art_id))
        return render_template(
            "buy_confirm.html",
            art_id=art_id,
            title=title,
            price=price,
            user_points=user_points
        )

    try:
        conn = sqlite3.connect("beevy.db")
        cursor = conn.cursor()

        # Subtract points
        cursor.execute("UPDATE users SET bee_points = bee_points - ? WHERE id=?", (price, user_id))
        cursor.execute("UPDATE users SET bee_points = bee_points + ? WHERE id=?", (price, author_id))

        # Add ownership
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("INSERT INTO art_ownership (art_id, owner_id, acquired_at) VALUES (?, ?, ?)",
                       (art_id, user_id, now))

        conn.commit()
        flash_translated("flash.artwork_purchased", "success")
    except Exception:
        conn.rollback()
        flash_translated("flash.purchase_failed", "error")
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
        SELECT COALESCE(NULLIF(ao.source, ''), art.original_path) as path, ao.can_download
        FROM art_ownership ao
        LEFT JOIN art ON ao.art_id = art.id
        JOIN users u ON ao.owner_id = u.id
        WHERE ao.art_id = ? AND u.username = ?
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
        price = int(request.form.get("price", 0))
        thumb_file = request.files.get("thumb")
        art_type = request.form.get("type")
        if art_type == "commission":
            tat = request.form.get("tat")
            slots = request.form.get("slots")
            examples_files = request.files.getlist("examples")
        else:
            tat = 1
            slots = None
            examples_files = []

        if not thumb_file or not thumb_file.filename:
            flash_translated("flash.thumbnail_required", "error")
            return redirect(request.url)

        if not validate_image(thumb_file):
            flash_translated("flash.invalid_thumbnail", "error")
            return redirect(request.url)

        os.makedirs(os.path.join(STATIC_ROOT, UPLOAD_FOLDER), exist_ok=True)
        os.makedirs(os.path.join(STATIC_ROOT, UPLOAD_FOLDER, THUMB_FOLDER), exist_ok=True)
        os.makedirs(os.path.join(STATIC_ROOT, UPLOAD_FOLDER, EX_FOLDER), exist_ok=True)
        os.makedirs(os.path.join(STATIC_ROOT, UPLOAD_FOLDER, ORIG_FOLDER), exist_ok=True)

        conn = sqlite3.connect("beevy.db")
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, surname FROM users WHERE username = ?", (username,))
        user_row = cursor.fetchone()
        if not user_row:
            conn.close()
            flash_translated("flash.user_not_found", "error")
            return redirect(url_for("index"))
        user_id = user_row[0]
        author_name = f"{user_row[1]} {user_row[2]} - {username}"

        # --- Helper to save + watermark + add metadata ---
        def process_image(file, username, prefix="", save_original=True):
            # thin wrapper used by create_art for backwards compatibility
            return process_uploaded_image(file, username, prefix=prefix, save_original=save_original, author_name=author_name) 



        # Thumbnail
        thumb_watermarked, original_path = process_image(thumb_file, username, prefix="thumb")

        # Example images
        examples_paths = []
        for ex in examples_files:
            if ex.filename:
                if not validate_image(ex):
                    flash_translated("flash.invalid_example_file", "error", filename=ex.filename)
                    return redirect(request.url)
                ex_wm, ex_original = process_image(ex, username, prefix="example")
                examples_paths.append(ex_wm)    

        if len(examples_paths) > 5:
            flash_translated("flash.too_many_examples", "error")
            return redirect(request.url)

        examples_paths_str = ",".join(examples_paths)

        # --- Save to DB ---


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

        flash_translated("flash.artwork_created", "success")
        return redirect("/shop")

    return render_template("create_art.html")


@app.route("/preview/<int:art_id>")
@login_required
def preview_art(art_id):
    """Serve a preview image. If the current user owns the art, prefer their owner-specific source or original; otherwise serve the public preview."""
    conn = sqlite3.connect("beevy.db")
    cursor = conn.cursor()
    cursor.execute("SELECT preview_path, original_path, is_active, author_id FROM art WHERE id = ?", (art_id,))
    row = cursor.fetchone()

    if not row:
        conn.close()
        abort(404)

    preview_rel, orig_rel, is_active, author_id = row

    # Determine if requester is owner or author
    user_id = None
    is_owner = False
    is_author = False
    chosen_rel = None
    if "username" in session:
        cursor.execute("SELECT id FROM users WHERE username = ?", (session.get("username"),))
        urow = cursor.fetchone()
        if urow:
            user_id = urow[0]
            is_owner = user_owns_art(user_id, art_id)
            is_author = (user_id == author_id)
            if is_owner:
                cursor.execute("SELECT source FROM art_ownership WHERE art_id = ? AND owner_id = ?", (art_id, user_id))
                src_row = cursor.fetchone()
                if src_row and src_row[0]:
                    chosen_rel = src_row[0]
                elif orig_rel:
                    chosen_rel = orig_rel

    # Access rules: inactive art only visible to owner/author
    if not is_active and not is_owner and not is_author:
        conn.close()
        abort(404)

    # If no owner-specific file chosen, fall back to public preview, original, or thumbnail
    if not chosen_rel:
        chosen_rel = preview_rel or orig_rel or None

    # Try thumbnail too if nothing else
    if not chosen_rel:
        cursor.execute("SELECT thumbnail_path FROM art WHERE id = ?", (art_id,))
        trow = cursor.fetchone()
        if trow and trow[0]:
            chosen_rel = trow[0]

    conn.close()

    if not chosen_rel:
        abort(404)

    file_path = os.path.join(STATIC_ROOT, chosen_rel)
    real_path = os.path.realpath(file_path)

    if not real_path.startswith(os.path.realpath(STATIC_ROOT)):
        abort(403)
    if not os.path.exists(real_path):
        abort(404)

    return send_from_directory(
        STATIC_ROOT,
        os.path.relpath(real_path, STATIC_ROOT)
    )


@app.route('/owned/<int:art_id>/preview')
@login_required
def owned_preview(art_id):
    """Owner-only preview — ensures only owners/authors can access owner copies."""
    conn = sqlite3.connect("beevy.db")
    cursor = conn.cursor()
    cursor.execute("SELECT preview_path, original_path, author_id, is_active FROM art WHERE id = ?", (art_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        abort(404)

    preview_rel, orig_rel, author_id, is_active = row

    # get user id
    cursor.execute("SELECT id FROM users WHERE username = ?", (session.get('username'),))
    urow = cursor.fetchone()
    if not urow:
        conn.close()
        abort(403)
    user_id = urow[0]

    owns = user_owns_art(user_id, art_id)
    is_author = (user_id == author_id)
    if not owns and not is_author:
        conn.close()
        abort(403)

    # Prefer owner-specific source, then original, then preview, then thumbnail
    cursor.execute("SELECT source FROM art_ownership WHERE art_id = ? AND owner_id = ?", (art_id, user_id))
    src_row = cursor.fetchone()
    chosen_rel = None
    if src_row and src_row[0]:
        chosen_rel = src_row[0]
    elif orig_rel:
        chosen_rel = orig_rel
    elif preview_rel:
        chosen_rel = preview_rel
    else:
        cursor.execute("SELECT thumbnail_path FROM art WHERE id = ?", (art_id,))
        trow = cursor.fetchone()
        if trow and trow[0]:
            chosen_rel = trow[0]

    conn.close()

    if not chosen_rel:
        abort(404)

    file_path = os.path.join(STATIC_ROOT, chosen_rel)
    real_path = os.path.realpath(file_path)

    if not real_path.startswith(os.path.realpath(STATIC_ROOT)):
        abort(403)
    if not os.path.exists(real_path):
        abort(404)

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
    port = int(os.environ.get("PORT", 5000))
    socketio.run(app, port=port)#, use_reloader=False -> stranky se sami nereload