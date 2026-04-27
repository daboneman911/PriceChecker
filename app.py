from flask import Flask, request, jsonify, render_template_string
import db
import scraper

app = Flask(__name__)

_STATUS_HTML = """<!DOCTYPE html>
<html>
<head>
  <title>Price Tracker</title>
  <style>
    body { font-family: sans-serif; padding: 20px; max-width: 1000px; margin: auto; }
    h2 { color: #333; }
    table { border-collapse: collapse; width: 100%; }
    th, td { border: 1px solid #ccc; padding: 8px 12px; text-align: left; }
    th { background: #f0f0f0; }
    .drop { background: #d4edda; }
    .rise { background: #f8d7da; }
    .flat { background: #f8f9fa; }
    a { color: #0066cc; }
  </style>
</head>
<body>
<h2>Price Tracker Status</h2>
<table>
  <tr>
    <th>#</th><th>User</th><th>Item</th><th>URL</th>
    <th>Initial</th><th>Last</th><th>Change</th><th>Last Checked</th>
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
  </tr>
  {% endfor %}
</table>
</body>
</html>"""


@app.route("/add", methods=["POST"])
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
def status():
    items = db.get_all_items()
    users = db.get_all_users()
    return render_template_string(_STATUS_HTML, items=items, users=users)


@app.route("/remove/<int:item_id>", methods=["DELETE"])
def remove(item_id):
    item = db.get_item(item_id)
    if not item:
        return jsonify({"error": "Item not found"}), 404
    db.remove_item(item_id)
    return jsonify({"deleted": item_id}), 200


if __name__ == "__main__":
    db.init_db()
    app.run(host="0.0.0.0", port=5000)
