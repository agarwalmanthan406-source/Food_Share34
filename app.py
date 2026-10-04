from flask import Flask, render_template, request, redirect, url_for, session, flash, g
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from database import db

app = Flask(__name__)
app.secret_key = 'dev_hackathon_key' 

# ------------------------------------------------------------------ #
# Database Setup & Request Lifecycle                                 #
# ------------------------------------------------------------------ #

with app.app_context():
    db.init_db(app)

app.teardown_appcontext(db.close_connection)

@app.before_request
def load_logged_in_user():
    user_id = session.get('user_id')
    if user_id is None:
        g.user = None
    else:
        conn = db.get_db()
        g.user = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()

# ------------------------------------------------------------------ #
# Public Routes                                                      #
# ------------------------------------------------------------------ #

@app.route("/")
def landing():
    return render_template("landing.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        password = request.form.get("password")
        role = request.form.get("role") 
        
        if not role in ['provider', 'volunteer', 'admin']:
            return render_template("register.html", error="Invalid role selected.")

        conn = db.get_db()
        error = None

        if not name or not email or not password:
            error = "All fields are required."
        else:
            try:
                conn.execute(
                    "INSERT INTO users (name, email, password_hash, role) VALUES (?, ?, ?, ?)",
                    (name, email, generate_password_hash(password), role)
                )
                conn.commit()
            except conn.IntegrityError:
                error = f"User {email} is already registered."

        if error is None:
            return redirect(url_for("login"))
        
        return render_template("register.html", error=error)
        
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        
        conn = db.get_db()
        error = None
        user = conn.execute(
            "SELECT * FROM users WHERE email = ?", (email,)
        ).fetchone()

        if user is None or not check_password_hash(user['password_hash'], password):
            error = "Incorrect email or password."

        if error is None:
            session.clear()
            session['user_id'] = user['id']
            
            if user['role'] == 'provider':
                return redirect(url_for('provider_dashboard'))
            elif user['role'] == 'volunteer':
                return redirect(url_for('volunteer_dashboard'))
            elif user['role'] == 'admin':
                return redirect(url_for('admin_dashboard'))
            else:
                return redirect(url_for('landing'))
                
        return render_template("login.html", error=error)
        
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("landing"))

# ------------------------------------------------------------------ #
# Provider Routes                                                    #
# ------------------------------------------------------------------ #

@app.route("/provider/dashboard")
def provider_dashboard():
    if g.user is None or g.user['role'] != 'provider':
        return redirect(url_for('login'))
    
    conn = db.get_db()
    listings = conn.execute(
        "SELECT * FROM food_listings WHERE provider_id = ? ORDER BY created_at DESC", 
        (g.user['id'],)
    ).fetchall()
    
    return render_template("provider_dashboard.html", listings=listings)

@app.route("/provider/listings/create", methods=["GET", "POST"])
def create_listing():
    if g.user is None or g.user['role'] != 'provider':
        return redirect(url_for('login'))
        
    if request.method == "POST":
        food_name = request.form.get("food_name")
        quantity = request.form.get("quantity")
        dietary_type = request.form.get("dietary_type")
        address = request.form.get("address")
        expires_at = request.form.get("expires_at")
        
        conn = db.get_db()
        conn.execute(
            """INSERT INTO food_listings 
               (provider_id, food_name, quantity, remaining_quantity, dietary_type, address, expires_at) 
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (g.user['id'], food_name, quantity, quantity, dietary_type, address, expires_at)
        )
        conn.commit()
        return redirect(url_for('provider_dashboard'))
        
    return render_template("create_listing.html")

@app.route("/provider/listing/<int:listing_id>/claims")
def provider_listing_claims(listing_id):
    if g.user is None or g.user['role'] != 'provider':
        return redirect(url_for('login'))
        
    conn = db.get_db()
    
    listing = conn.execute(
        "SELECT * FROM food_listings WHERE id = ? AND provider_id = ?", 
        (listing_id, g.user['id'])
    ).fetchone()
    
    if not listing:
        flash("Listing not found or you do not have permission to view it.")
        return redirect(url_for('provider_dashboard'))
        
    query = """
        SELECT c.*, u.name as volunteer_name 
        FROM claims c
        JOIN users u ON c.volunteer_id = u.id
        WHERE c.listing_id = ?
        ORDER BY c.claimed_at DESC
    """
    claims = conn.execute(query, (listing_id,)).fetchall()
    
    return render_template("provider_claims.html", listing=listing, claims=claims)

# ------------------------------------------------------------------ #
# Volunteer Routes                                                   #
# ------------------------------------------------------------------ #

@app.route("/volunteer/dashboard")
def volunteer_dashboard():
    if g.user is None or g.user['role'] != 'volunteer':
        return redirect(url_for('login'))
    
    current_time = datetime.now().strftime('%Y-%m-%dT%H:%M')
    conn = db.get_db()
    
    query = """
        SELECT f.*, u.name as provider_name 
        FROM food_listings f
        JOIN users u ON f.provider_id = u.id
        WHERE f.remaining_quantity > 0 
        AND f.expires_at > ?
        ORDER BY f.expires_at ASC
    """
    available_food = conn.execute(query, (current_time,)).fetchall()
    
    return render_template("volunteer_dashboard.html", listings=available_food)

@app.route("/volunteer/claim/<int:listing_id>", methods=["POST"])
def claim_food(listing_id):
    if g.user is None or g.user['role'] != 'volunteer':
        return redirect(url_for('login'))
        
    claim_quantity = int(request.form.get("claim_quantity", 1))
    current_time = datetime.now().strftime('%Y-%m-%dT%H:%M')
    
    conn = db.get_db()
    
    cursor = conn.execute(
        """
        UPDATE food_listings 
        SET remaining_quantity = remaining_quantity - ? 
        WHERE id = ? 
          AND remaining_quantity >= ? 
          AND expires_at > ?
        """,
        (claim_quantity, listing_id, claim_quantity, current_time)
    )
    
    if cursor.rowcount > 0:
        conn.execute(
            "INSERT INTO claims (listing_id, volunteer_id, quantity) VALUES (?, ?, ?)",
            (listing_id, g.user['id'], claim_quantity)
        )
        conn.execute(
            "UPDATE food_listings SET status = 'fully_claimed' WHERE id = ? AND remaining_quantity = 0",
            (listing_id,)
        )
        conn.commit()
        flash(f"Successfully claimed {claim_quantity} meals!")
    else:
        flash("Sorry, that food is no longer available or not enough quantity remains.")

    return redirect(url_for('volunteer_dashboard'))

@app.route("/volunteer/claims")
def volunteer_claims():
    if g.user is None or g.user['role'] != 'volunteer':
        return redirect(url_for('login'))
        
    conn = db.get_db()
    query = """
        SELECT c.*, f.food_name, f.address, u.name as provider_name 
        FROM claims c
        JOIN food_listings f ON c.listing_id = f.id
        JOIN users u ON f.provider_id = u.id
        WHERE c.volunteer_id = ?
        ORDER BY c.claimed_at DESC
    """
    my_claims = conn.execute(query, (g.user['id'],)).fetchall()
    
    return render_template("volunteer_claims.html", claims=my_claims)

# ------------------------------------------------------------------ #
# Admin Routes                                                       #
# ------------------------------------------------------------------ #

@app.route("/admin/dashboard")
def admin_dashboard():
    if g.user is None or g.user['role'] != 'admin':
        return redirect(url_for('login'))
        
    conn = db.get_db()
    current_time = datetime.now().strftime('%Y-%m-%dT%H:%M')
    
    total_listings = conn.execute("SELECT COUNT(*) as count FROM food_listings").fetchone()['count']
    
    available_listings = conn.execute(
        "SELECT COUNT(*) as count FROM food_listings WHERE remaining_quantity > 0 AND expires_at > ?", 
        (current_time,)
    ).fetchone()['count']
    
    expired_listings = conn.execute(
        "SELECT COUNT(*) as count FROM food_listings WHERE expires_at <= ?", 
        (current_time,)
    ).fetchone()['count']
    
    meals_distributed = conn.execute("SELECT SUM(quantity) as total FROM claims").fetchone()['total'] or 0
    
    stats = {
        'total': total_listings,
        'available': available_listings,
        'expired': expired_listings,
        'meals': meals_distributed
    }
    
    query = """
        SELECT f.*, u.name as provider_name 
        FROM food_listings f
        JOIN users u ON f.provider_id = u.id
        ORDER BY f.created_at DESC
    """
    all_listings = conn.execute(query).fetchall()
    
    return render_template("admin_dashboard.html", stats=stats, listings=all_listings)

@app.route("/admin/listing/delete/<int:listing_id>", methods=["POST"])
def admin_delete_listing(listing_id):
    if g.user is None or g.user['role'] != 'admin':
        return redirect(url_for('login'))
        
    conn = db.get_db()
    conn.execute("DELETE FROM food_listings WHERE id = ?", (listing_id,))
    conn.execute("DELETE FROM claims WHERE listing_id = ?", (listing_id,))
    conn.commit()
    
    flash("Listing successfully removed by administrator.")
    return redirect(url_for('admin_dashboard'))

if __name__ == "__main__":
    app.run(debug=True, port=5001)