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
    if request.method == 'POST':
        usEm = request.form['username']
        password = request.form['password']
        user_bytes = password.encode('utf-8')
        try:
            conn = sqlite3.connect('users.db')
            cursor = conn.cursor()
            cursor.execute("SELECT password FROM users WHERE email=? OR username=?",(usEm, usEm))
            result = cursor.fetchone()
            if result:
                db_pass = result[0]
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
        try:
            conn = sqlite3.connect('users.db')
            cursor = conn.cursor()
            cursor.execute("SELECT username FROM users WHERE username=?", (username,))
            existing_user = cursor.fetchone()
            cursor.execute("SELECT email FROM users WHERE email=?", (email,))
            existing_email = cursor.fetchone()

            reg_errors = []
            if existing_user:
                print('username in use')
                reg_errors.append("Username is already taken.")
            if existing_email:
                print('email in use')
                reg_errors.append("Email is already in use.")
            if reg_errors:
                return render_template("register.html", reg_errors = reg_errors)
            else:
                cursor.execute("INSERT INTO users (username, password, name, surname, email, dob) VALUES (?, ?, ?, ?, ?, ?)", (username, hash, name, surname, email, dob))
                conn.commit()
                
                return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            return "User already exists!"
        finally:
            conn.close()
    return render_template("register.html")

@app.route('/userPage')
def userPage():
    return render_template('userPage.html')
    

if __name__ == "__main__":
    app.run(debug=True)