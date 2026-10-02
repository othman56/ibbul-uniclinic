import sqlite3
from flask import g

DATABASE = 'clinic.db'

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db

def init_db():
    db = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row
    db.executescript('''
        CREATE TABLE IF NOT EXISTS users (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            username      TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role          TEXT NOT NULL DEFAULT 'student',
            patient_id    INTEGER,
            FOREIGN KEY (patient_id) REFERENCES patients(id)
        );

        CREATE TABLE IF NOT EXISTS patients (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT NOT NULL,
            matric_no   TEXT UNIQUE NOT NULL,
            age         INTEGER,
            gender      TEXT,
            phone       TEXT,
            email       TEXT,
            blood_group TEXT,
            address     TEXT,
            created_at  TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS appointments (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id  INTEGER NOT NULL,
            date        TEXT NOT NULL,
            time        TEXT NOT NULL,
            reason      TEXT,
            status      TEXT DEFAULT 'Scheduled',
            FOREIGN KEY (patient_id) REFERENCES patients(id)
        );

        CREATE TABLE IF NOT EXISTS prescriptions (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id  INTEGER NOT NULL,
            date        TEXT NOT NULL,
            diagnosis   TEXT,
            medication  TEXT,
            dosage      TEXT,
            notes       TEXT,
            FOREIGN KEY (patient_id) REFERENCES patients(id)
        );

        CREATE TABLE IF NOT EXISTS bills (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id  INTEGER NOT NULL,
            date        TEXT NOT NULL,
            description TEXT,
            amount      REAL NOT NULL,
            status      TEXT DEFAULT 'Unpaid',
            FOREIGN KEY (patient_id) REFERENCES patients(id)
        );
    ''')
    db.commit()
    db.close()
