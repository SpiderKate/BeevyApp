# test_flash_translation.py
from flask import Flask, session, get_flashed_messages
from flask import flash as flask_flash

# Import your translation system
from app import flash_translated
from translations import translations

app = Flask(__name__)
app.secret_key = "test-secret-key"


@app.route("/test")
def test_route():
    # Simulate language stored in session
    session["user_language"] = "cs"

    # Flash a translated message
    flash_translated("flash.settings_saved", "success")

    return "OK"


with app.test_request_context("/test"):
    # Run the route manually
    response = app.view_functions["test_route"]()

    # Retrieve flashed messages
    messages = get_flashed_messages(with_categories=True)

    print("=== FLASH TEST ===")
    print("Session language:", session.get("user_language"))
    print("Flashed messages:", messages)

    # Expected:
    # Session language: cs
    # Flashed messages: [('success', 'Přihlášení proběhlo úspěšně')]  ← example
