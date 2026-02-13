# ============================================================================
# main_library_system.py
# Integrated Library Borrowing System for ESP32-S3 with RFID & Barcode Scanner
# ============================================================================

import time
import network
import urequests
import json
import machine
from machine import Pin, SPI
import mfrc522  # RFID library
import usb_hid
from usb_hid import Device
import usb_cdc

# ============================================================================
# CONFIGURATION - CHANGE THESE VALUES
# ============================================================================

# WiFi Configuration
WIFI_SSID = "Converge_HA7V"
WIFI_PASSWORD = "632594SV"

# Email Notification Configuration (using SMTP2GO or similar service)
EMAIL_API_URL = "https://api.smtp2go.com/v3/email/send"
EMAIL_API_KEY = "your_smtp2go_api_key_here"
SUPERVISOR_EMAIL = "lozano.lanzeanderson.co@gmail.com"

# Database Configuration (Using Google Sheets as simple free database)
GOOGLE_SHEETS_URL = "https://script.google.com/macros/s/YOUR_GOOGLE_SCRIPT_ID/exec"

# RFID Configuration
RFID_RST_PIN = 21
RFID_SS_PIN = 5

# ============================================================================
# INITIALIZE COMPONENTS
# ============================================================================

class LibrarySystem:
    def __init__(self):
        print("Initializing Library System...")
        
        # Initialize WiFi
        self.wifi = network.WLAN(network.STA_IF)
        self.wifi.active(True)
        
        # Initialize RFID Reader
        spi = SPI(2, baudrate=2500000, polarity=0, phase=0)
        spi.init()
        self.rfid = mfrc522.MFRC522(spi=spi, gpioRst=RFID_RST_PIN, gpioCs=RFID_SS_PIN)
        
        # Initialize USB for barcode scanner (simulated as keyboard input)
        self.barcode_buffer = ""
        self.scanning_barcode = False
        
        # Student and book databases (in real implementation, use Google Sheets/MySQL)
        self.students = {
            "1234567890": {"name": "lanze Anderson C. Lozano ","section":"12-Stem","LRN": "357858938090","email": "lanze.anderson@gmail.com", "status": "active"},
            "0987654321": {"name": "Jessabel S. Umayan","section": "12 Stem","LRN": "09484693584","contact": "09674617765", "status": "active"},
            "1122334455": {"name": "Angela A. Merced","section": "12 stem","LRN": "048493930878","Contact": "0994949338787", "status": "active"}
        }
        
        self.books = {
            "9780143039693": {"title": "Noli Me Tangere", "author": "Jose Rizal", "available": True},
            "9780143039709": {"title": "El Filibusterismo", "author": "Jose Rizal", "available": True},
            "9789712723591": {"title": "Philippine History", "author": "Teodoro Agoncillo", "available": True}
        }
        
        # Borrowing records
        self.borrowing_records = []
        
        # Connect to WiFi
        self.connect_wifi()
        
        print("System Ready!")
        print("\n" + "="*50)
        print("    SCHOOL LIBRARY BORROWING SYSTEM")
        print("="*50)
    
    # ============================================================================
    # WIFI FUNCTIONS
    # ============================================================================
    
    def connect_wifi(self):
        """Connect to WiFi network"""
        print(f"Connecting to WiFi: {WIFI_SSID}")
        self.wifi.connect(WIFI_SSID, WIFI_PASSWORD)
        
        timeout = 20  # 20 seconds timeout
        while timeout > 0:
            if self.wifi.isconnected():
                print(f"WiFi Connected!")
                print(f"IP Address: {self.wifi.ifconfig()[0]}")
                return True
            time.sleep(1)
            timeout -= 1
            print(".", end="")
        
        print("\nFailed to connect to WiFi")
        return False
    
    # ============================================================================
    # RFID FUNCTIONS
    # ============================================================================
    
    def read_rfid(self):
        """Read student ID from RFID card"""
        print("\nWaiting for Student ID Card...")
        print("Place card near the RFID reader")
        
        while True:
            # Scan for cards
            (status, tag_type) = self.rfid.request(self.rfid.REQIDL)
            
            if status == self.rfid.OK:
                # Get the UID of the card
                (status, uid) = self.rfid.anticoll()
                
                if status == self.rfid.OK:
                    # Convert UID to string
                    card_id = "".join([str(i) for i in uid])
                    print(f"Card detected! ID: {card_id}")
                    
                    # Optional: Halt the card to prevent multiple reads
                    self.rfid.select_tag(uid)
                    self.rfid.card_auth(self.rfid.AUTHENT1A, 8, self.rfid_key, uid)
                    self.rfid.halt_auth()
                    
                    return card_id
            
            time.sleep(0.1)  # Small delay to prevent CPU overload
            
            # Check for keyboard interrupt (Ctrl+C)
            try:
                if machine.Pin(0).value() == 0:  # Boot button on ESP32
                    return None
            except:
                pass
    
    # ============================================================================
    # BARCODE FUNCTIONS
    # ============================================================================
    
    def read_barcode(self):
        """Read barcode from USB scanner (simulated with serial input)"""
        print("\nReady to scan book barcode...")
        print("Point scanner at barcode and press trigger")
        
        # In actual implementation, this would read from USB HID or serial
        # For simulation, we'll use serial input
        barcode = input(": ").strip()
        
        if barcode:
            print(f"Barcode scanned: {barcode}")
            return barcode
        return None
    
    # ============================================================================
    # DATABASE & VALIDATION FUNCTIONS
    # ============================================================================
    
    def validate_student(self, student_id):
        """Check if student exists and can borrow books"""
        if student_id not in self.students:
            print("❌ Student not found in database")
            return False
        
        student = self.students[student_id]
        
        if student["status"] != "active":
            print(f"❌ Student account is {student['status']}")
            return False
        
        # Check for overdue books
        overdue_count = self.check_overdue_books(student_id)
        if overdue_count > 0:
            print(f"❌ Student has {overdue_count} overdue book(s)")
            print("Please return overdue books first")
            return False
        
        print(f"✅ Student verified: {student['name']}")
        return True
    
    def check_overdue_books(self, student_id):
        """Check if student has any overdue books"""
        overdue_count = 0
        current_time = time.time()
        
        for record in self.borrowing_records:
            if record["student_id"] == student_id and not record["returned"]:
                # Check if overdue (assuming 14-day borrowing period)
                borrow_time = record["borrow_time"]
                if current_time - borrow_time > 14 * 24 * 60 * 60:  # 14 days in seconds
                    overdue_count += 1
        
        return overdue_count
    
    def validate_book(self, barcode):
        """Check if book exists and is available"""
        if barcode not in self.books:
            print("❌ Book not found in database")
            return False
        
        book = self.books[barcode]
        
        if not book["available"]:
            print("❌ Book is already borrowed by another student")
            return False
        
        print(f"✅ Book verified: {book['title']} by {book['author']}")
        return True
    
    # ============================================================================
    # BORROWING PROCESS
    # ============================================================================
    
    def process_borrowing(self, student_id, barcode):
        """Process the book borrowing transaction"""
        try:
            # Get student and book info
            student = self.students[student_id]
            book = self.books[barcode]
            
            # Create borrowing record
            record = {
                "student_id": student_id,
                "student_name": student["name"],
                "book_barcode": barcode,
                "book_title": book["title"],
                "borrow_time": time.time(),
                "due_date": time.time() + (14 * 24 * 60 * 60),  # 14 days from now
                "returned": False
            }
            
            # Add to records
            self.borrowing_records.append(record)
            
            # Mark book as unavailable
            self.books[barcode]["available"] = False
            
            # Send notification
            self.send_notification(student, book, record["due_date"])
            
            # Update Google Sheets (if configured)
            self.update_database(student_id, barcode, "borrow")
            
            print("\n" + "="*50)
            print("✅ BOOK BORROWED SUCCESSFULLY!")
            print(f"Student: {student['name']}")
            print(f"Book: {book['title']}")
            print(f"Due Date: {self.format_date(record['due_date'])}")
            print("="*50)
            
            return True
            
        except Exception as e:
            print(f"❌ Error processing borrowing: {e}")
            return False
    
    # ============================================================================
    # RETURN PROCESS
    # ============================================================================
    
    def process_return(self, barcode):
        """Process book return"""
        # Find the borrowing record
        for record in self.borrowing_records:
            if record["book_barcode"] == barcode and not record["returned"]:
                # Mark as returned
                record["returned"] = True
                record["return_time"] = time.time()
                
                # Mark book as available
                self.books[barcode]["available"] = True
                
                # Check if overdue
                current_time = time.time()
                if current_time > record["due_date"]:
                    days_overdue = int((current_time - record["due_date"]) / (24 * 60 * 60))
                    print(f"⚠️  Book returned {days_overdue} day(s) overdue!")
                else:
                    print("✅ Book returned on time!")
                
                # Update database
                self.update_database(record["student_id"], barcode, "return")
                
                # Send return notification
                self.send_return_notification(record)
                
                print(f"\nBook '{record['book_title']}' has been returned.")
                return True
        
        print("❌ No active borrowing record found for this book")
        return False
    
    # ============================================================================
    # NOTIFICATION FUNCTIONS
    # ============================================================================
    
    def send_notification(self, student, book, due_date):
        """Send email notification to supervisor"""
        if not self.wifi.isconnected():
            print("⚠️  Cannot send notification - WiFi not connected")
            return False
        
        try:
            # Format the email message
            subject = f"Library Book Borrowed: {book['title']}"
            message = f"""
            NEW BOOK BORROWED
            
            Student: {student['name']}
            Student ID: {list(self.students.keys())[list(self.students.values()).index(student)]}
            
            Book: {book['title']}
            Author: {book['author']}
            
            Borrowed: {self.format_date(time.time())}
            Due Date: {self.format_date(due_date)}
            
            This is an automated notification from the Library System.
            """
            
            # Prepare email data for SMTP2GO
            email_data = {
                "api_key": EMAIL_API_KEY,
                "to": [SUPERVISOR_EMAIL],
                "sender": "library@yourschool.edu.ph",
                "subject": subject,
                "text_body": message
            }
            
            # Send the request
            response = urequests.post(EMAIL_API_URL, json=email_data, headers={'Content-Type': 'application/json'})
            
            if response.status_code == 200:
                print(f"📧 Notification sent to {SUPERVISOR_EMAIL}")
                response.close()
                return True
            else:
                print(f"❌ Failed to send notification. Status: {response.status_code}")
                response.close()
                return False
                
        except Exception as e:
            print(f"❌ Notification error: {e}")
            return False
    
    def send_return_notification(self, record):
        """Send notification when book is returned"""
        print(f"📧 Return notification sent for '{record['book_title']}'")
        # Similar implementation to send_notification()
    
    # ============================================================================
    # DATABASE SYNC FUNCTIONS
    # ============================================================================
    
    def update_database(self, student_id, barcode, action):
        """Update Google Sheets database"""
        if not self.wifi.isconnected() or GOOGLE_SHEETS_URL == "YOUR_GOOGLE_SCRIPT_ID":
            return False
        
        try:
            data = {
                "student_id": student_id,
                "book_barcode": barcode,
                "action": action,
                "timestamp": time.time()
            }
            
            response = urequests.post(GOOGLE_SHEETS_URL, json=data)
            response.close()
            return True
            
        except Exception as e:
            print(f"⚠️  Database sync failed: {e}")
            return False
    
    # ============================================================================
    # UTILITY FUNCTIONS
    # ============================================================================
    
    def format_date(self, timestamp):
        """Format timestamp to readable date"""
        # Convert seconds to readable date (simplified)
        days = int(timestamp / (24 * 60 * 60))
        return f"Day {days}"
    
    def display_menu(self):
        """Display main menu"""
        print("\n" + "="*50)
        print("    LIBRARY SYSTEM MAIN MENU")
        print("="*50)
        print("1. Borrow a Book")
        print("2. Return a Book")
        print("3. View Borrowing Records")
        print("4. System Status")
        print("5. Exit")
        print("="*50)
    
    def view_records(self):
        """Display current borrowing records"""
        print("\n" + "="*50)
        print("    CURRENT BORROWING RECORDS")
        print("="*50)
        
        if not self.borrowing_records:
            print("No books are currently borrowed.")
            return
        
        active_loans = [r for r in self.borrowing_records if not r["returned"]]
        
        if not active_loans:
            print("No active borrowings.")
            return
        
        for i, record in enumerate(active_loans, 1):
            status = "OVERDUE" if time.time() > record["due_date"] else "ON TIME"
            print(f"{i}. {record['student_name']} - {record['book_title']} ({status})")
    
    def system_status(self):
        """Display system status"""
        print("\n" + "="*50)
        print("    SYSTEM STATUS")
        print("="*50)
        print(f"WiFi: {'Connected' if self.wifi.isconnected() else 'Disconnected'}")
        print(f"Students in database: {len(self.students)}")
        print(f"Books in database: {len(self.books)}")
        print(f"Active borrowings: {len([r for r in self.borrowing_records if not r['returned']])}")
        print(f"Overdue books: {len([r for r in self.borrowing_records if not r['returned'] and time.time() > r['due_date']])}")
        print("="*50)
    
    # ============================================================================
    # MAIN APPLICATION LOOP
    # ============================================================================
    
    def run(self):
        """Main application loop"""
        while True:
            self.display_menu()
            
            try:
                choice = input("\nEnter your choice (1-5): ").strip()
                
                if choice == '1':  # Borrow Book
                    print("\n" + "="*50)
                    print("    BOOK BORROWING PROCESS")
                    print("="*50)
                    
                    # Step 1: Scan Student ID
                    student_id = self.read_rfid()
                    if not student_id:
                        print("❌ No student ID detected")
                        continue
                    
                    # Step 2: Validate Student
                    if not self.validate_student(student_id):
                        continue
                    
                    # Step 3: Scan Book Barcode
                    barcode = self.read_barcode()
                    if not barcode:
                        print("❌ No barcode scanned")
                        continue
                    
                    # Step 4: Validate Book
                    if not self.validate_book(barcode):
                        continue
                    
                    # Step 5: Process Borrowing
                    self.process_borrowing(student_id, barcode)
                
                elif choice == '2':  # Return Book
                    print("\n" + "="*50)
                    print("    BOOK RETURN PROCESS")
                    print("="*50)
                    
                    barcode = self.read_barcode()
                    if barcode:
                        self.process_return(barcode)
                
                elif choice == '3':  # View Records
                    self.view_records()
                
                elif choice == '4':  # System Status
                    self.system_status()
                
                elif choice == '5':  # Exit
                    print("\nThank you for using the Library System!")
                    break
                
                else:
                    print("❌ Invalid choice. Please try again.")
                
                # Small delay before next iteration
                time.sleep(1)
                
            except KeyboardInterrupt:
                print("\n\nSystem interrupted by user")
                break
            except Exception as e:
                print(f"\n❌ Error: {e}")
                time.sleep(2)

# ============================================================================
# ADDITIONAL REQUIRED FILES
# ============================================================================

"""
File 2: mfrc522.py (RFID Library for ESP32)
Save this as a separate file on your ESP32-S3
"""

# mfrc522.py content (simplified version for ESP32)
class MFRC522:
    def __init__(self, spi, gpioRst, gpioCs):
        self.spi = spi
        self.rst = Pin(gpioRst, Pin.OUT)
        self.cs = Pin(gpioCs, Pin.OUT)
        self.rst.value(1)
        self.cs.value(1)
        self.init()
    
    def init(self):
        self.reset()
        # Ini