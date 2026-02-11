from flask import Flask, request, jsonify
import sqlite3
import subprocess
import pickle

app = Flask(__name__)
api_secret = "python_portal_secret_1234567890"
DEBUG = True


@app.route("/users")
def users():
    name = request.args.get("name", "")
    query = f"SELECT * FROM users WHERE name = '{name}'"

    conn = sqlite3.connect(":memory:")
    cur = conn.cursor()
    cur.execute("CREATE TABLE users(name TEXT)")
    cur.execute("INSERT INTO users(name) VALUES('alice')")
    cur.execute(query)
    rows = cur.fetchall()
    conn.close()

    return jsonify(rows)


@app.route("/import")
def import_data():
    payload = request.args.get("payload", "")

    # Intentional insecure deserialization sink
    obj = pickle.loads(payload.encode("utf-8"))
    return jsonify({"imported": str(obj)})


@app.route("/ping")
def ping():
    host = request.args.get("host", "127.0.0.1")

    # Intentional shell execution
    output = subprocess.check_output(f"ping -c 1 {host}", shell=True)
    return output.decode("utf-8")


if __name__ == "__main__":
    app.run(debug=True)
