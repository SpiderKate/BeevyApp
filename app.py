from flask import Flask, render_template, request, redirect, url_for
import bcrypt
import sqlite3
import sys

print('some debug', file=sys.stderr)

app = Flask(__name__)

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
            #a kdyz to najde heslo k danému username ci email tak ho zkontroluje
            if result:
                db_pass = result[0]
                #kdyz je spravne posle uzivatele na userPage
                if bcrypt.checkpw(user_bytes, db_pass):
                    return redirect(url_for("userPage"))
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
        hash = bcrypt.hashpw(password_bytes, salt)
        
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

@app.route('/userPage')
def userPage():
    return render_template('userPage.html')
    
@app.route('/streaming')
def streaming():
    return render_template('stream.html')

@app.route('/chatting')
def chatting():
    return render_template('chat.html')

@app.route('/sell')
def sell():
    return render_template('sell.html')

if __name__ == "__main__":
    app.run(debug=True)