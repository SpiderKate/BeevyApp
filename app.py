from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)

@app.route('/')
def index():
    return render_template("index.html")


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        return redirect(url_for("index"))
    else:
        return render_template("login.html")
    
@app.route('/register', methods=['GET','POST'])
def register():
    return render_template("register.html")
    

if __name__ == "__main__":
    app.run(debug=True)