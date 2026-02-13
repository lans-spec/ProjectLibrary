#include <MFRC522v2.h>
#include <MFRC522DriverSPI.h>
#include <MFRC522DriverPinSimple.h>
#include <MFRC522Debug.h>

#define SS_PIN    10
#define RST_PIN   5
#define MOSI_PIN  11
#define MISO_PIN  13
#define SCK_PIN   12  

MFRC522DriverPinSimple ss_pin(10);
MFRC522DriverSPI driver{ss_pin};
MFRC522 mfrc522{driver};
MFRC522::MIFARE_Key key;

#define BLOCK_NAME_1   4
#define BLOCK_NAME_2   5
#define BLOCK_ID       6
#define BLOCK_SECTION  8
#define BLOCK_EMAIL_1  9
#define BLOCK_EMAIL_2 10

String fullName      = "Lanze Anderson C. Lozano      ";
byte idData[16]      = "136515140138";
byte sectionData[16] = "12-STEM";
String fullEmail     = "lanze.anderson@gmail.com      ";

void setKeyDefault() {
  for (byte i = 0; i < 6; i++) key.keyByte[i] = 0xFF;
}

bool writeBlock(byte blockAddr, byte *data16) {
  setKeyDefault();
  
  if (!mfrc522.PCD_Authenticate(0x60, blockAddr, &key, &(mfrc522.uid))) {
    Serial.print(F("Auth failed (write) for block ")); Serial.println(blockAddr);
    return false;
  }
  
  if (!mfrc522.MIFARE_Write(blockAddr, data16, 16)) {
    Serial.print(F("Write failed for block ")); Serial.println(blockAddr);
    return false;
  }
  
  Serial.print(F("Wrote to block ")); Serial.println(blockAddr);
  return true;
}

void writeLongName(byte block1, byte block2, String data) {
  byte buffer[16];
  
  setKeyDefault();

  // -------- FIRST BLOCK --------
  memset(buffer, 0, 16);
  for (int i = 0; i < 16 && i < data.length(); i++)
    buffer[i] = data[i];

  if (mfrc522.PCD_Authenticate(0x60, block1, &key, &(mfrc522.uid))) {
    mfrc522.MIFARE_Write(block1, buffer, 16);
  }

  // -------- SECOND BLOCK --------
  memset(buffer, 0, 16);
  for (int i = 16; i < 32 && i < data.length(); i++)
    buffer[i - 16] = data[i];

  
  if (mfrc522.PCD_Authenticate(0x60, block2, &key, &(mfrc522.uid))) {
    mfrc522.MIFARE_Write(block2, buffer, 16);
  }

  mfrc522.PCD_StopCrypto1();
  Serial.println("Long name written successfully!");
}

void writeLongEmail(byte block1, byte block2, String data) {
  byte buffer[16];
  
  setKeyDefault();

  // -------- FIRST BLOCK --------
  memset(buffer, 0, 16);
  for (int i = 0; i < 16 && i < data.length(); i++)
    buffer[i] = data[i];

  if (mfrc522.PCD_Authenticate(0x60, block1, &key, &(mfrc522.uid))) {
    if (!mfrc522.MIFARE_Write(block1, buffer, 16)) {
      Serial.println("Email write failed (block1)");
      return;
    }
  }

  // -------- SECOND BLOCK --------
  memset(buffer, 0, 16);
  for (int i = 16; i < 32 && i < data.length(); i++)
    buffer[i - 16] = data[i];

  if (mfrc522.PCD_Authenticate(0x60, block2, &key, &(mfrc522.uid))) {
    if (!mfrc522.MIFARE_Write(block2, buffer, 16)) {
      Serial.println("Email write failed (block2)");
      return;
    }
  }

  mfrc522.PCD_StopCrypto1();
  Serial.println("Long email written successfully!");
}

String readLongName(byte block1, byte block2) {
  byte buffer[18];
  byte size = sizeof(buffer);
  String result = "";

  setKeyDefault();

  // Read block 1
  if (mfrc522.PCD_Authenticate(0x60, block1, &key, &(mfrc522.uid))) {
    if (mfrc522.MIFARE_Read(block1, buffer, &size)) {
      for (int i = 0; i < 16; i++)
        if (buffer[i] != 0)
          result += (char)buffer[i];
    }
  }

  // Read block 2
  if (mfrc522.PCD_Authenticate(0x60, block2, &key, &(mfrc522.uid))) {
    if (mfrc522.MIFARE_Read(block2, buffer, &size)) {
      for (int i = 0; i < 16; i++)
        if (buffer[i] != 0)
          result += (char)buffer[i];
    }
  }

  mfrc522.PCD_StopCrypto1();
  return result;
}

String readLongEmail(byte block1, byte block2) {
  byte buffer[18];
  byte size = sizeof(buffer);
  String result = "";

  setKeyDefault();

  // Read first block
  if (mfrc522.PCD_Authenticate(0x60, block1, &key, &(mfrc522.uid))) {
    if (mfrc522.MIFARE_Read(block1, buffer, &size)) {
      for (int i = 0; i < 16; i++)
        if (buffer[i] != 0)
          result += (char)buffer[i];
    }
  }

  // Read second block
  if (mfrc522.PCD_Authenticate(0x60, block2, &key, &(mfrc522.uid))) {
    if (mfrc522.MIFARE_Read(block2, buffer, &size)) {
      for (int i = 0; i < 16; i++)
        if (buffer[i] != 0)
          result += (char)buffer[i];
    }
  }

  mfrc522.PCD_StopCrypto1();
  return result;
}

void setup() {
  Serial.begin(115200);
  SPI.begin();
  mfrc522.PCD_Init();
  
  Serial.println(F("\n=== WRITE MODE: Tap card to store data ==="));
  Serial.println(F("Blocks used: 4 (Name), 5(ID), 6 (Section), 8 (Email)\n"));
}

void loop() {
  // Wait for card
  if (!mfrc522.PICC_IsNewCardPresent())
    return;

  if (!mfrc522.PICC_ReadCardSerial())
    return;
  
  delay(150);
  
  Serial.print(F("Card detected! UID: "));
  MFRC522Debug::PrintUID(Serial, mfrc522.uid);
  Serial.println();
  
  // Write all data to the card
  bool ok = true;
  ok &= writeBlock(BLOCK_ID, idData);
  ok &= writeBlock(BLOCK_SECTION, sectionData);
  
  writeLongName(BLOCK_NAME_1, BLOCK_NAME_2, fullName);
  writeLongEmail(BLOCK_EMAIL_1, BLOCK_EMAIL_2, fullEmail);
  
  // Read back and verify
  String name = readLongName(BLOCK_NAME_1, BLOCK_NAME_2);
  String email = readLongEmail(BLOCK_EMAIL_1, BLOCK_EMAIL_2);
  
  Serial.println("Name: " + name);
  Serial.println("Email: " + email);
  
  Serial.println(ok ? F("All fields written successfully!\n")
                    : F("One or more fields FAILED to write.\n"));
  
  mfrc522.PICC_HaltA();
  mfrc522.PCD_StopCrypto1();
  delay(1000);
}