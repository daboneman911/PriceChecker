from flask import Flask, request, jsonify, render_template_string, session, redirect, url_for
from functools import wraps
import db
import scraper

app = Flask(__name__)

try:
    import config as _cfg
    app.secret_key = _cfg.SECRET_KEY
except (ImportError, AttributeError):
    app.secret_key = "dev-only-insecure-key"


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("logged_in"):
            if request.is_json or request.method == "DELETE":
                return jsonify({"error": "Not authenticated"}), 401
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


_LOGIN_HTML = """<!DOCTYPE html>
<html>
<head>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Price Tracker</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: -apple-system, BlinkMacSystemFont, sans-serif; background: #f2f2f7;
           display: flex; align-items: center; justify-content: center; min-height: 100vh; }
    .card { background: white; padding: 40px 30px; border-radius: 20px; width: 90%;
            max-width: 340px; box-shadow: 0 4px 24px rgba(0,0,0,0.08); text-align: center; }
    .icon { font-size: 48px; margin-bottom: 12px; }
    h2 { font-size: 22px; color: #1c1c1e; margin-bottom: 6px; }
    p { color: #8e8e93; font-size: 14px; margin-bottom: 28px; }
    input[type=password] { width: 100%; padding: 16px; border: 2px solid #e5e5ea;
      border-radius: 12px; font-size: 28px; text-align: center; letter-spacing: 10px;
      outline: none; transition: border-color 0.2s; }
    input[type=password]:focus { border-color: #007aff; }
    button { width: 100%; padding: 16px; background: #007aff; color: white; border: none;
             border-radius: 12px; font-size: 17px; font-weight: 600; margin-top: 16px;
             cursor: pointer; }
    button:active { opacity: 0.8; }
    .error { color: #ff3b30; font-size: 14px; margin-top: 12px; }
  </style>
</head>
<body>
  <div class="card">
    <div class="icon">👟</div>
    <h2>Price Tracker</h2>
    <p>Enter your PIN to continue</p>
    <form method="POST">
      <input type="password" name="pin" placeholder="••••" maxlength="10" autofocus inputmode="numeric">
      <button type="submit">Continue</button>
      {% if error %}<p class="error">Wrong PIN — try again</p>{% endif %}
    </form>
  </div>
</body>
</html>"""


_FORM_HTML = """<!DOCTYPE html>
<html>
<head>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Track a Price</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: -apple-system, BlinkMacSystemFont, sans-serif; background: #f2f2f7; padding: 20px; }
    .container { max-width: 500px; margin: 0 auto; }
    .header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; }
    h2 { font-size: 24px; color: #1c1c1e; }
    .nav a { color: #007aff; text-decoration: none; font-size: 15px; margin-left: 16px; }
    .card { background: white; border-radius: 16px; padding: 24px; box-shadow: 0 2px 12px rgba(0,0,0,0.06); }
    label { display: block; font-size: 13px; font-weight: 600; color: #8e8e93;
            text-transform: uppercase; letter-spacing: 0.5px; margin: 20px 0 8px; }
    label:first-child { margin-top: 0; }
    input[type=url], input[type=text] { width: 100%; padding: 14px; border: 1.5px solid #e5e5ea;
      border-radius: 10px; font-size: 16px; outline: none; }
    input:focus { border-color: #007aff; }
    .user-toggle { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
    .user-btn { padding: 14px; border: 2px solid #e5e5ea; border-radius: 10px; text-align: center;
                font-size: 16px; font-weight: 600; cursor: pointer; color: #3c3c43; }
    .user-btn input { display: none; }
    .user-btn.selected { border-color: #007aff; background: #e8f0ff; color: #007aff; }
    button[type=submit] { width: 100%; padding: 16px; background: #007aff; color: white; border: none;
                          border-radius: 12px; font-size: 17px; font-weight: 600; margin-top: 24px; cursor: pointer; }
    button[type=submit]:active { opacity: 0.8; }
    .alert { padding: 14px 16px; border-radius: 10px; margin-bottom: 20px; font-size: 15px; font-weight: 500; }
    .alert.success { background: #d4edda; color: #155724; }
    .alert.error { background: #fde8e8; color: #c0392b; }
  </style>
  <script>
    function selectUser(el) {
      document.querySelectorAll('.user-btn').forEach(b => b.classList.remove('selected'));
      el.classList.add('selected');
      el.querySelector('input').checked = true;
    }
  </script>
</head>
<body>
  <div class="container">
    <div class="header">
      <h2>👟 Track a Price</h2>
      <div class="nav">
        <a href="/status">Status</a>
        <a href="/logout">Logout</a>
      </div>
    </div>
    {% if message %}
    <div class="alert {{ 'success' if success else 'error' }}">{{ message }}</div>
    {% endif %}
    <div class="card">
      <form method="POST" action="/track">
        <label>Product URL</label>
        <input type="url" name="url" placeholder="https://..." required value="{{ url or '' }}">
        <label>Item Name</label>
        <input type="text" name="name" placeholder="Air Max 90" required>
        <label>Who is tracking?</label>
        <div class="user-toggle">
          <label class="user-btn selected" onclick="selectUser(this)">
            <input type="radio" name="user" value="fitz" checked> Fitz
          </label>
          <label class="user-btn" onclick="selectUser(this)">
            <input type="radio" name="user" value="sha"> Sha
          </label>
        </div>
        <button type="submit">Track Price</button>
      </form>
    </div>
  </div>
</body>
</html>"""


_STATUS_HTML = """<!DOCTYPE html>
<html>
<head>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Price Tracker</title>
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, sans-serif; padding: 20px; max-width: 1000px; margin: auto; }
    .header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
    h2 { color: #333; }
    .nav a { color: #007aff; text-decoration: none; margin-left: 16px; }
    table { border-collapse: collapse; width: 100%; }
    th, td { border: 1px solid #ccc; padding: 8px 12px; text-align: left; }
    th { background: #f0f0f0; }
    .drop { background: #d4edda; }
    .rise { background: #f8d7da; }
    .flat { background: #f8f9fa; }
    a { color: #0066cc; }
    .remove-btn { background: none; border: none; cursor: pointer; font-size: 16px; padding: 2px 6px;
                  border-radius: 4px; color: #cc0000; }
    .remove-btn:hover { background: #fde8e8; }
  </style>
  <script>
    function removeItem(id, btn) {
      if (!confirm('Remove this item?')) return;
      fetch('/remove/' + id, {method: 'DELETE'})
        .then(r => r.json())
        .then(() => btn.closest('tr').remove());
    }
  </script>
</head>
<body>
<div class="header">
  <h2>Price Tracker Status</h2>
  <div class="nav">
    <a href="/">Add Item</a>
    <a href="/logout">Logout</a>
  </div>
</div>
<table>
  <tr>
    <th>#</th><th>User</th><th>Item</th><th>URL</th>
    <th>Initial</th><th>Last</th><th>Change</th><th>Last Checked</th><th></th>
  </tr>
  {% for item in items %}
  {% set change = item.last_price - item.initial_price %}
  {% set pct = ((change / item.initial_price) * 100) | round(1) if item.initial_price else 0 %}
  <tr class="{{ 'drop' if change < 0 else 'rise' if change > 0 else 'flat' }}">
    <td>{{ item.id }}</td>
    <td>{{ users[item.user_id]['name'] }}</td>
    <td>{{ item.item_name }}</td>
    <td><a href="{{ item.url }}" target="_blank">link</a></td>
    <td>${{ "%.2f"|format(item.initial_price) }}</td>
    <td>${{ "%.2f"|format(item.last_price) }}</td>
    <td>{{ "%+.1f"|format(pct) }}%</td>
    <td>{{ item.last_checked_at or "never" }}</td>
    <td><button class="remove-btn" onclick="removeItem({{ item.id }}, this)">🗑</button></td>
  </tr>
  {% endfor %}
</table>
</body>
</html>"""


@app.route("/login", methods=["GET", "POST"])
def login():
    error = False
    if request.method == "POST":
        import config
        if request.form.get("pin") == config.APP_PIN:
            session["logged_in"] = True
            return redirect(url_for("index"))
        error = True
    return render_template_string(_LOGIN_HTML, error=error)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/")
@login_required
def index():
    return render_template_string(_FORM_HTML, message=None, success=False, url="")


@app.route("/track", methods=["POST"])
@login_required
def track():
    url = request.form.get("url", "").strip()
    name = request.form.get("name", "").strip()
    user_id = request.form.get("user", "").strip()

    if not url or not name or not user_id:
        return render_template_string(_FORM_HTML, message="All fields are required.", success=False, url=url)

    users = db.get_all_users()
    if user_id not in users:
        return render_template_string(_FORM_HTML, message=f"Unknown user: {user_id}", success=False, url=url)

    try:
        price = scraper.get_price(url)
    except Exception as e:
        return render_template_string(_FORM_HTML, message=f"Couldn't fetch price: {e}", success=False, url=url)

    db.add_item(user_id, url, name, price)
    return render_template_string(_FORM_HTML, message=f"{name} added at ${price:.2f}!", success=True, url="")


@app.route("/add", methods=["POST"])
@login_required
def add():
    data = request.get_json(force=True) or {}
    url = data.get("url", "").strip()
    name = data.get("name", "").strip()
    user_id = data.get("user", "").strip()

    if not url or not name or not user_id:
        return jsonify({"error": "url, name, and user are required"}), 400

    users = db.get_all_users()
    if user_id not in users:
        return jsonify({"error": f"Unknown user: {user_id}"}), 400

    try:
        price = scraper.get_price(url)
    except Exception as e:
        return jsonify({"error": f"Could not fetch price: {e}"}), 422

    item_id = db.add_item(user_id, url, name, price)
    return jsonify({"id": item_id, "name": name, "price": price}), 201


@app.route("/status")
@login_required
def status():
    items = db.get_all_items()
    users = db.get_all_users()
    return render_template_string(_STATUS_HTML, items=items, users=users)


@app.route("/remove/<int:item_id>", methods=["DELETE"])
@login_required
def remove(item_id):
    item = db.get_item(item_id)
    if not item:
        return jsonify({"error": "Item not found"}), 404
    db.remove_item(item_id)
    return jsonify({"deleted": item_id}), 200


if __name__ == "__main__":
    db.init_db()
    app.run(host="0.0.0.0", port=5000)
