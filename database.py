import os
import psycopg2

DATABASE_URL = os.getenv('DATABASE_URL')  # Η διεύθυνση της βάσης από το Railway

def connect_db():
    """Συνδέεται στη βάση δεδομένων και επιστρέφει τη σύνδεση και τον cursor"""
    conn = psycopg2.connect("postgresql://postgres:jitvcjHcHnWKoMVDMXGPcJhFdukRjukO@roundhouse.proxy.rlwy.net:51799/railway")
    cursor = conn.cursor()
    return conn, cursor

def setup_database():
    """Δημιουργεί τον πίνακα reminders αν δεν υπάρχει"""
    conn, cursor = connect_db()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reminders (
            id SERIAL PRIMARY KEY,
            user_id BIGINT NOT NULL,
            message TEXT NOT NULL,
            reminder_time TIMESTAMP NOT NULL
        );
    ''')
    conn.commit()
    cursor.close()
    conn.close()

# Εκτέλεση της αρχικοποίησης της βάσης
setup_database()
