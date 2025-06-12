from flask import Flask, render_template, request, redirect, url_for
from flask_bcrypt import bcrypt
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
        username = request.form['username']
        password = request.form['password']
        print('login_test')
        return redirect(url_for("index"))
        
          
    else:
        return render_template("login.html")
    
@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        name = request.form['name']
        surname = request.form['surname']
        email = request.form['email']
        dob = request.form['dob']
        bytes = password.encode('utf-8')
        salt = bcrypt.gensalt()
        hash = bcrypt.hashpw(bytes, salt)
    #need to complete import to db and controle on login
        try:
            conn = sqlite3.connect('users.db')
            cursor = conn.cursor()
            cursor.execute("INSERT INTO users (username, password, name, surname, email, dob) VALUES (?, ?, ?, ?, ?, ?)", (username, hash, name, surname, email, dob))
            conn.commit()
            print('regoster_test')
            conn.close()
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            return "User already exists!"
    return render_template("register.html")
    

if __name__ == "__main__":
    app.run(debug=True)