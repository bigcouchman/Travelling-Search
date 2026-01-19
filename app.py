from flask import Flask, g, render_template, request, jsonify, redirect, url_for, session, flash
import sqlite3
import os
from ai_routes import ai_bp
from dotenv import load_dotenv
load_dotenv()  

app = Flask(__name__)
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.secret_key = "super_secret_in_travelling_because_i_need_it_secure"
DB_PATH = 'database.db'  
app.register_blueprint(ai_bp)
app.config['CESIUM_TOKEN'] = os.getenv("CESIUM_TOKEN")
# Signup route
@app.route("/signup",methods=["GET","POST"])
def signup():
    if request.method == "POST":
        username = request.form["username"]
        email = request.form["email"]
        password = request.form["password"]

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO users (username, email, password) VALUES (?, ?, ?)",
                           (username, email, password))
            conn.commit()
            flash("Account successfully created.", "success")
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            flash("Username or email exists aready.", "danger")
        finally:
            conn.close()
    return render_template("signup.html")

# Login Route
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, password))
        user = cursor.fetchone()
        conn.close()

        if user:
            session["user"] = username
            flash(f"Welcome back, {username}!", "success")
            return redirect(url_for("home"))
        else:
            flash("Invalid credentials.", "danger")
    return render_template("login.html")

# Logout Route
@app.route("/logout")
def logout():
    session.pop("user", None)
    flash("You have been logged out.", "info")
    return redirect(url_for("login"))

# Main page route
@app.route("/")
def home():
    if "user" not in session:
        return redirect(url_for("signup"))
    return render_template("index.html")

# Debugging only!
@app.route("/test")
def test():
    return "Flask is working!"

# Search route to search through database for locations
@app.route("/search")
def search():
    term = request.args.get("q", "").lower()
    category = request.args.get("category", "").lower()

    if not term:
        return jsonify([])

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Enables dict-style access
    cursor = conn.cursor()

    if category:
        cursor.execute("""
    SELECT id, name, city, image_url, description,
           category, rating, lat, lng
    FROM   places
    WHERE  (LOWER(city) LIKE ? OR LOWER(name) LIKE ?)
    AND    (? = '' OR LOWER(category) = ?)
""", (f'%{term}%', f'%{term}%', category, category))
    else:
        cursor.execute("""
            SELECT id, name, city, image_url, description, category, rating, lat, lng
            FROM places
            WHERE LOWER(city) LIKE ? OR LOWER(name) LIKE ?
        """, (f"%{term}%", f"%{term}%"))

    rows = cursor.fetchall()
    conn.close()

    results = [{
        "id": r["id"],
        "name": r["name"],
        "city": r["city"],
        "image_url": r["image_url"],
        "description": r["description"],
        "category": r["category"],
        "rating": r["rating"],
        "lat": r["lat"],  
        "lng": r["lng"]
    } for r in rows]

    return jsonify(results)

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DB_PATH, timeout=5)
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(exc):
    db = g.pop('db', None)
    if db is not None:
        db.close()

# About page route
@app.route("/about")
def about():
    return render_template("aboutus.html")

# search for places route
@app.route("/places")
def get_gltf_places():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT name, city, description, lat, lng
        FROM places
        WHERE lat IS NOT NULL AND lng IS NOT NULL
    """)

    rows = cursor.fetchall()
    conn.close()

    return jsonify([
        {
            "name": row["name"],
            "city": row["city"],
            "description": row["description"],
            "lat": row["lat"],
            "lng": row["lng"],
        }
        for row in rows
    ])


# Welcome user
@app.context_processor
def inject_user():
    return dict(current_user=session.get("user"))

# Profile page route
@app.route("/profile", methods=["GET", "POST"])
def profile():
    if "user" not in session:
        flash("Please log in to access your profile.", "warning")
        return redirect(url_for("login"))

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    username = session["user"]

    if request.method == "POST":
        new_username = request.form["username"]
        new_email = request.form["email"]
        new_password = request.form["password"]

        try:
            cursor.execute("""
                UPDATE users 
                SET username = ?, email = ?, password = ?
                WHERE username = ?
            """, (new_username, new_email, new_password, username))
            conn.commit()
            flash("Your changes were saved. Please log in again.", "info")
            conn.close()
            session.pop("user", None)  # Log user out
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            flash("That username or email is already taken.", "danger")
    else:
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        user_data = cursor.fetchone()
        conn.close()

        return render_template("profile.html", user={
            "username": user_data[1],
            "email": user_data[2],
            "password": user_data[3]
        })

# Globe Route
@app.route("/globe")
def globe():
    return render_template("globe.html")

# API Route to return all locations with lat/lon (for Cesium globe)
@app.route("/api/locations")
def get_locations():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Update this query if your table/column names differ
    cursor.execute("""
        SELECT name, city, description, lat, lng
        FROM places
        WHERE lat IS NOT NULL AND lng IS NOT NULL
    """)
    
    rows = cursor.fetchall()
    conn.close()

    results = []
    for row in rows:
        results.append({
            "name": row["name"],
            "city": row["city"],
            "description": row["description"],
            "lat": row["lat"],
            "lon": row["lng"],
        })

    return jsonify(results)

# Select from favorites
@app.route('/favorite/<place_id>', methods=['POST'])
def toggle_favorite(place_id):
    if "user" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    username = session["user"]
    conn = sqlite3.connect(DB_PATH, timeout=5)
    cur  = conn.cursor()

    try:
        cur.execute("SELECT 1 FROM favorites WHERE username=? AND place_id=?",
                    (username, place_id))
        exists = cur.fetchone()

        if exists:
            cur.execute("DELETE FROM favorites WHERE username=? AND place_id=?",
                        (username, place_id))
            status = "removed"
        else:
            cur.execute("INSERT INTO favorites (username, place_id) VALUES (?, ?)",
                        (username, place_id))
            status = "added"

        conn.commit()
    except sqlite3.Error as e:
        conn.rollback()
        print("DB error:", e)
        return jsonify({"error": "DB write failed"}), 500
    finally:
        conn.close()

    return jsonify({"status": status})


# Favorite Entries
@app.route('/favorites', methods=['GET'])             # <‑‑ NOTE plural
def show_favorites():
    if "user" not in session:
        flash("Please log in to view your favorites.", "warning")
        return redirect(url_for("login"))

    username = session["user"]
    conn = get_db()
    cur  = conn.cursor()
    cur.execute("""
        SELECT p.id, p.name, p.city, p.image_url, p.description,
               p.category, p.rating, p.lat, p.lng
        FROM   favorites f
        JOIN   places    p ON f.place_id = p.id
        WHERE  f.username = ?
    """, (username,))
    favorites = cur.fetchall()
    return render_template("favorites.html", favorites=favorites)

# Itinerary route
@app.route("/itinerary")
def itinerary():
    return render_template("itinerary.html")

# ▼ ADD this right after your `@app.route("/")` home view
from datetime import datetime, timedelta

@app.route("/tripplan", methods=["GET", "POST"])
def tripplan():
    if "user" not in session:           
        flash("Please log in first.", "warning")
        return redirect(url_for("login"))

    days = []                            
    if request.method == "POST":
        try:
            start = datetime.fromisoformat(request.form["start"])
            end   = datetime.fromisoformat(request.form["end"])
            if start > end:
                raise ValueError("Start after end")

            delta = (end - start).days + 1          # inclusive
            for i in range(delta):
                d = start + timedelta(days=i)
                days.append({
                    "label": d.strftime("%A – %b %d %Y"),  # e.g. Monday – Jul 01 2025
                    "iso":   d.date().isoformat()          # 2025‑07‑01
                })
        except Exception as e:
            flash("Invalid dates selected.", "danger")

    # render the SAME template either way
    return render_template(
        "itinerary.html",
        days=days,                       # empty list on first visit (so search is hidden)
        trip_start=request.form.get("start", ""),
        trip_end=request.form.get("end",  "")
    )
# Save trip Route
@app.get("/api/trip_days/<int:trip_id>")
def trip_days(trip_id):
    if "user" not in session:
        return jsonify(error="unauth"), 401

    db = get_db()
    rows = db.execute("""
        SELECT td.trip_date, p.name, p.city
        FROM trip_days td
        JOIN places p ON td.place_id = p.id
        JOIN trips t ON td.trip_id = t.id
        WHERE td.trip_id = ? AND t.username = ?
        ORDER BY td.trip_date
    """, (trip_id, session["user"])).fetchall()

    # Group by day
    from collections import defaultdict
    days = defaultdict(list)
    for row in rows:
        days[row["trip_date"]].append({
            "name": row["name"],
            "city": row["city"]
        })

    return jsonify([
        {"date": day, "places": places}
        for day, places in days.items()
    ])

# Get trips and delete trips
@app.get("/trips")
def trips_get():
    if "user" not in session:
        return redirect(url_for("login"))

    db = get_db()
    rows = db.execute("""SELECT id,title,start,end
                         FROM trips
                         WHERE username = ?
                         ORDER BY start DESC""", 
                         (session["user"],)).fetchall()
    # rows is list[ Row(id=…, …) ]
    return render_template("trips.html", trips=rows)

@app.delete("/api/delete_trip/<int:trip_id>")
def delete_trip(trip_id):
    if "user" not in session:
        return jsonify(error="unauthorized"), 401

    db = get_db()
    cur = db.cursor()

    try:
        # Make sure the trip belongs to the current user
        trip_check = cur.execute("SELECT id FROM trips WHERE id = ? AND username = ?", (trip_id, session["user"])).fetchone()
        if not trip_check:
            return jsonify(error="not found or unauthorized"), 403

        # Delete from trip_days first (FK constraint)
        cur.execute("DELETE FROM trip_days WHERE trip_id = ?", (trip_id,))
        cur.execute("DELETE FROM trips WHERE id = ?", (trip_id,))
        db.commit()
        return jsonify(ok=True)
    except sqlite3.Error as e:
        db.rollback()
        return jsonify(error=str(e)), 500

# Trip saver
@app.post("/api/save_trip")
def save_trip():
    if "user" not in session:
        return jsonify(error="unauthorized"), 401

    data = request.get_json()
    title = data.get("title", "").strip()
    start = data.get("start")
    end = data.get("end")
    days = data.get("days", [])

    if not title or not start or not end:
        return jsonify(error="Missing trip info"), 400

    try:
        db = get_db()
        cur = db.cursor()

        # Insert into trips table
        cur.execute("""
            INSERT INTO trips (username, title, start, end)
            VALUES (?, ?, ?, ?)
        """, (session["user"], title, start, end))
        trip_id = cur.lastrowid

        # Insert each day's selected place_ids into trip_days
        for day in days:
            date = day["date"]
            for pid in day["places"]:
                cur.execute("""
                    INSERT INTO trip_days (trip_id, trip_date, place_id)
                    VALUES (?, ?, ?)
                """, (trip_id, date, pid))

        db.commit()
        return jsonify(ok=True, trip_id=trip_id)
    except Exception as e:
        db.rollback()
        return jsonify(error=str(e)), 500


# Digital Twin Cesium Route
@app.route("/digital_twin")
def digital_twin():
    return render_template("digital_twin.html", config=app.config)

@app.route("/tower")
def tower():
    return render_template("tower.html")

# Show Model 
@app.get("/model")
def model_view():
    """
    URL pattern:
      /model?asset_id=96188&lat=48.8584&lon=2.2945&title=Eiffel+Tower
    Only asset_id is required; lat / lon just re‑locate the model.
    """
    return render_template("model_viewer.html", title=request.args.get("title"))


if __name__ == "__main__":
    app.run(debug=True)

    