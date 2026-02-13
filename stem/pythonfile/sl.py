
import sqlite3

def initialize_mahs_database():
    # Establishes a connection to the database file
    conn = sqlite3.connect('mahs_library.db')
    cursor = conn.cursor()

    # Create the Students Table
    # [span_6](start_span)This stores RFID data for identification[span_6](end_span)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS students (
            rfid_id TEXT PRIMARY KEY,
            full_name TEXT NOT NULL,
            grade_section TEXT,
            [span_7](start_span)has_overdue_books INTEGER DEFAULT 0 -- 0 = No, 1 = Yes[span_7](end_span)
        )
    ''')

    # Create the Books Table
    # [span_8](start_span)This stores Barcode/QR data for book logging[span_8](end_span)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS books (
            barcode_id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            author TEXT,
            status TEXT DEFAULT 'available' -- 'available' or 'borrowed'
        )
    ''')

    # Create the Transactions Table
    # [span_9](start_span)Automates record keeping and notification logs[span_9](end_span)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
            rfid_id TEXT,
            barcode_id TEXT,
            borrow_date DATETIME DEFAULT CURRENT_TIMESTAMP,
            return_date DATETIME,
            FOREIGN KEY (rfid_id) REFERENCES students (rfid_id),
            FOREIGN KEY (barcode_id) REFERENCES books (barcode_id)
        )
    ''')

    conn.commit()
    conn.close()
    print("MAHS Library Database initialized successfully.")

if _name_ == "_main_":
    initialize_mahs_database()