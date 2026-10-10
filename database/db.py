import sqlite3
from flask import g

DATABASE = 'surplus_food.db'

def get_db():
    """Connect to the SQLite database and ensure foreign keys are enforced."""
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
        # Enforce foreign key constraints in SQLite
        db.execute("PRAGMA foreign_keys = ON")
    return db

def init_db(app):
    """Initialize the database with our schema."""
    with app.app_context():
        db = get_db()
        
        # 1. Users Table (Providers, Volunteers, Admins)
        db.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('provider', 'volunteer', 'admin')),
                phone TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # 2. Food Listings Table
        db.execute('''
            CREATE TABLE IF NOT EXISTS food_listings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                provider_id INTEGER NOT NULL,
                food_name TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                remaining_quantity INTEGER NOT NULL,
                dietary_type TEXT,
                description TEXT,
                latitude REAL,
                longitude REAL,
                address TEXT,
                available_from TIMESTAMP,
                expires_at TIMESTAMP NOT NULL,
                status TEXT DEFAULT 'available' CHECK(status IN ('available', 'partially_claimed', 'fully_claimed', 'picked_up', 'expired', 'cancelled')),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (provider_id) REFERENCES users (id)
            )
        ''')

        # 3. Claims Table
        db.execute('''
            CREATE TABLE IF NOT EXISTS claims (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                listing_id INTEGER NOT NULL,
                volunteer_id INTEGER NOT NULL,
                quantity INTEGER NOT NULL,
                status TEXT DEFAULT 'claimed' CHECK(status IN ('claimed', 'picked_up', 'cancelled')),
                claimed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                picked_up_at TIMESTAMP,
                FOREIGN KEY (listing_id) REFERENCES food_listings (id),
                FOREIGN KEY (volunteer_id) REFERENCES users (id)
            )
        ''')
        
        db.commit()

def close_connection(exception):
    """Close the database connection at the end of the request."""
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()
