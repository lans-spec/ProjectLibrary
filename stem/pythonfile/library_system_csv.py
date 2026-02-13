
import csv
import os
import time
from datetime import datetime

import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

EMAIL_HOST = "smtp.gmail.com"
EMAIL_PORT = 587
EMAIL_ADDRESS = "lanze.anderson@gmail.com"
EMAIL_PASSWORD = "hirl quyv gdzs dewd"
LIBRARY_NAME = "MELCHORA AQUINO HIGH SCHOOL LIBRARY"
BORROWING_DAYS = 7

class CSVLibraryDatabase:
    def __init__(self, filename="library_database.csv"):
        self.filename = filename
        self.setup_database()
    
    def setup_database(self):
        """Create CSV file with headers if it doesn't exist"""
        if not self.filename in os.listdir():
            with open(self.filename, 'w', newline='') as file:
                writer = csv.writer(file)
                writer.writerow(['student_id', 'Student_Name', 'book_barcode', 
                               'book_title', 'action', 'timestamp', 'date_time'])
            print(f"Created new database: {self.filename}")
    
    def log_transaction(self, student_id, Student_Name, book_barcode, book_title, action):
        """Log a transaction to CSV file"""
        try:
            timestamp = time.time()
            date_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            with open(self.filename, 'a', newline='') as file:
                writer = csv.writer(file)
                writer.writerow([student_id, Student_Name, book_barcode, 
                               book_title, action, timestamp, date_time])
            
            print(f"📝 Transaction logged to {self.filename}")
            return True
            
        except Exception as e:
            print(f"❌ Error writing to CSV: {e}")
            return False
    
    def check_overdue_books_csv(self, student_id):
        """Check for overdue books using CSV database"""
        overdue_books = []
        current_time = time.time()
        
        try:
            with open(self.filename, 'r') as file:
                reader = csv.DictReader(file)
                
                for row in reader:
                    if (row['student_id'] == student_id and 
                        row['action'] == 'borrow' and 
                        not self.is_returned(student_id, row['book_barcode'])):
                        
                        borrow_time = float(row['timestamp'])
                        if current_time - borrow_time > 259200:
                            overdue_books.append({
                                'book_title': row['book_title'],
                                'due_date': borrow_time + 259200
                            })
            
            return overdue_books
            
        except Exception as e:
            print(f"Error reading CSV: {e}")
            return []
    
    def is_returned(self, student_id, book_barcode):
        """Check if a book has been returned"""
        try:
            with open(self.filename, 'r') as file:
                reader = csv.DictReader(file)
                
                for row in reader:
                    if (row['student_id'] == student_id and 
                        row['book_barcode'] == book_barcode and 
                        row['action'] == 'return'):
                        return True
            return False
            
        except Exception as e:
            print(f"Error checking return status: {e}")
            return False
    
    def get_student_history(self, student_id):
        """Get all transactions for a student"""
        history = []
        try:
            with open(self.filename, 'r') as file:
                reader = csv.DictReader(file)
                
                for row in reader:
                    if row['student_id'] == student_id:
                        history.append(row)
            
            return history
            
        except Exception as e:
            print(f"Error getting history: {e}")
            return []
    
    def get_book_status(self, book_barcode):
        """Check if a book is currently borrowed"""
        try:
            with open(self.filename, 'r') as file:
                lines = file.readlines()
                
                # Check most recent transaction for this book
                for line in reversed(lines):
                    row = line.strip().split(',')
                    if len(row) >= 5 and row[2] == book_barcode:
                        return row[4]  # 'borrow' or 'return'
            
            return 'available'
            
        except Exception as e:
            print(f"Error checking book status: {e}")
            return 'unknown'

class EmailNotifier:
    def __init__(self):
        self.host = EMAIL_HOST
        self.port = EMAIL_PORT
        self.sender = EMAIL_ADDRESS
        self.password = EMAIL_PASSWORD
    
    def send_borrow_notification(self, student_data, book_data, due_date):
        """Send email to student about borrowed book"""
        try:
            borrow_date = datetime.now().strftime("%B %d, %Y")
            due_date_str = due_date.strftime("%B %d, %Y")

            msg = MIMEMultipart('alternative')
            msg['Subject'] = f"📚 Book Borrowed: {book_data['title']}"
            msg['From'] = f"{LIBRARY_NAME} <{self.sender}>"
            msg['To'] = student_data['email']

            context = ssl.create_default_context()
            with smtplib.SMTP(self.host, self.port) as server:
                server.starttls(context=context)
                server.login(self.sender, self.password)
                server.send_message(msg)
            
            print(f"✅ Email sent to {student_data['email']}")
            return True
            
        except Exception as e:
            print(f"❌ Email failed: {e}")
            return False

class LibrarySystem:
    def __init__(self):
        print("Initializing Library System...")
        self.RFID_RST_PIN = 4
        self.RFID_SS_PIN = 5
        
        self.database = CSVLibraryDatabase()
        self.notifier = EmailNotifier()
    
    def process_borrowing(self, student_id, book_barcode):
        """Process book borrowing with CSV logging"""
        try:
            student = self.load_student_data()[student_id]
            book = self.load_book_data()[book_barcode]
            
            from datetime import datetime, timedelta
            due_date = datetime.now() + timedelta(days=BORROWING_DAYS)

            # Log to CSV database   
            self.database.log_transaction(
                student_id=student_id,
                student_name=student['name'],
                book_barcode=book_barcode,
                book_title=book['title'],
                action='borrow'
            )
            
            # Update in-memory status
            self.books[book_barcode]['available'] = False
            
            if 'email' in student and student['email']:
                self.email_notifier.send_borrow_notification(student, book, due_date)
            else:
                print(f"⚠️ No email for {student['name']}")

            due_date = time.time() + (3 * 24 * 60 * 60)
            self.send_notification(student, book, due_date)

            print(f"\n✅ Book '{book['title']}' borrowed by {student['name']}")
            print(f"   Transaction saved to {self.database.filename}")
            
            return True
            
        except Exception as e:
            print(f"❌ Borrowing error: {e}")
            return False
    
    def process_return(self, book_barcode):
        """Process book return with CSV logging"""
        try:
            # Find the book in our records
            for record in self.borrowing_records:
                if record['book_barcode'] == book_barcode and not record['returned']:
                    
                    # Log return to CSV
                    self.database.log_transaction(
                        student_id=record['student_id'],
                        student_name=record['student_name'],
                        book_barcode=book_barcode,
                        book_title=record['book_title'],
                        action='return'
                    )
                    
                    # Update status
                    record['returned'] = True
                    self.books[book_barcode]['available'] = True
                    
                    print(f"✅ Book '{record['book_title']}' returned")
                    print(f"   Return logged to {self.database.filename}")
                    
                    return True
            
            print("❌ No active borrowing found for this book")
            return False
            
        except Exception as e:
            print(f"❌ Return error: {e}")
            return False

    def load_student_data(self):
        """Load actual student data - REPLACE WITH YOUR DATA"""
        return {
            "1234567890": {"student_id": "136515140138", "name": "Lanze Andereson C. Lozano", "email": "lanze.anderson@gmail.com"},
            "0987654321": {"student_id": "136515130851", "name": "Jessabel S. Umayan", "email": "jessabelsorianoumayan@gmail.com"},
            "2468101357": {"student_id": "111844140223", "name": "Angela A. Merced", "email": "angela.merced@gmail.com"},
        }
    
    def load_book_data(self):
        """Load actual book data - REPLACE WITH YOUR DATA"""
        return {
            "9789716982115": {"title": "Noli Me Tangere", "author": "Jose Rizal", "available": True},
            "9789716982115": {"title": "El Filibusterismo", "author": "Jose Rizal", "available": True},
        }
    
    def setup_hardware(self):
        """Initialize RFID and barcode scanner - ADD THIS METHOD"""
        print("Setting up hardware...")
        # Add your RFID and barcode initialization code here
        pass
    
    def setup_wifi(self):
        """Connect to WiFi - ADD THIS METHOD"""
        print("Setting up WiFi...")
        # Add your WiFi connection code here
        pass

    def check_overdue_books(self, student_id):
        """Check overdue books using CSV database"""
        overdue_list = self.database.check_overdue_books_csv(student_id)
        
        if overdue_list:
            print(f"⚠️  {len(overdue_list)} OVERDUE BOOK(S):")
            for book in overdue_list:
                due_date = datetime.fromtimestamp(book['due_date']).strftime("%Y-%m-%d")
                print(f"   - {book['book_title']} (Due: {due_date})")
            return False
        return True
    
    def generate_report(self):
        """Generate a simple library report from CSV"""
        print("\n" + "="*50)
        print("LIBRARY REPORT")
        print("="*50)
        
        try:
            with open(self.database.filename, 'r') as file:
                reader = csv.DictReader(file)
                transactions = list(reader)
                
                total_borrow = sum(1 for t in transactions if t['action'] == 'borrow')
                total_return = sum(1 for t in transactions if t['action'] == 'return')
                
                print(f"Total Transactions: {len(transactions)}")
                print(f"Books Borrowed: {total_borrow}")
                print(f"Books Returned: {total_return}")
                print(f"Currently Borrowed: {total_borrow - total_return}")
                
                # Today's activity
                today = datetime.now().strftime("%Y-%m-%d")
                today_activity = [t for t in transactions if t['date_time'].startswith(today)]
                print(f"Today's Activity: {len(today_activity)} transactions")
                
        except Exception as e:
            print(f"Report error: {e}")



# ============================================================================
# OPTIONAL: EXCEL EXPORT FUNCTION (For Better Reports)
# ============================================================================

def export_to_excel(csv_file="library_database.csv", excel_file="library_report.xlsx"):
    """Convert CSV to Excel format for better reporting"""
    try:
        import pandas as pd
        
        # Read CSV file
        df = pd.read_csv(csv_file)
        
        # Create Excel writer
        with pd.ExcelWriter(excel_file, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='All Transactions', index=False)
            
            # Create summary sheet
            summary_data = {
                'Metric': ['Total Transactions', 'Total Borrows', 'Total Returns', 
                          'Active Borrows', 'Unique Students', 'Unique Books'],
                'Value': [len(df), 
                         len(df[df['action'] == 'borrow']),
                         len(df[df['action'] == 'return']),
                         len(df[df['action'] == 'borrow']) - len(df[df['action'] == 'return']),
                         df['student_id'].nunique(),
                         df['book_barcode'].nunique()]
            }
            summary_df = pd.DataFrame(summary_data)
            summary_df.to_excel(writer, sheet_name='Summary', index=False)
            
        print(f"✅ Report exported to {excel_file}")
        return True
        
    except ImportError:
        print("⚠️  Install pandas: 'pip install pandas openpyxl'")
        return False
    except Exception as e:
        print(f"❌ Export error: {e}")
        return False

# ============================================================================
# UPDATED MAIN MENU OPTION
# ============================================================================

def main_menu():
    """Updated main menu with CSV options"""
    library = LibrarySystem()
    
    while True:
        print("\n" + "="*50)
        print("    SCHOOL LIBRARY SYSTEM (CSV DATABASE)")
        print("="*50)
        print("1. Borrow a Book")
        print("2. Return a Book")
        print("3. View Student History")
        print("4. Check Book Status")
        print("5. Generate Library Report")
        print("6. Export to Excel")
        print("7. Exit")
        
        choice = input("\nEnter choice (1-7): ").strip()
        
        if choice == '1':
            # Borrow book process
            student_id = library.read_rfid()
            if student_id and library.check_overdue_books(student_id):
                book_barcode = library.read_barcode()
                if book_barcode:
                    library.process_borrowing(student_id, book_barcode)
        
        elif choice == '2':
            # Return book
            book_barcode = library.read_barcode()
            if book_barcode:
                library.process_return(book_barcode)
        
        elif choice == '3':
            # View student history
            student_id = input("Enter Student ID: ").strip()
            history = library.database.get_student_history(student_id)
            if history:
                for trans in history:
                    print(f"{trans['date_time']}: {trans['action']} {trans['book_title']}")
        
        elif choice == '4':
            # Check book status
            book_barcode = input("Enter Book Barcode: ").strip()
            status = library.database.get_book_status(book_barcode)
            print(f"Book Status: {status}")
        
        elif choice == '5':
            # Generate report
            library.generate_report()
        
        elif choice == '6':
            # Export to Excel
            export_to_excel()
        
        elif choice == '7':
            print("Goodbye!")
            break
        
        else:
            print("Invalid choice")

if __name__ == "__main__":
    main_menu()