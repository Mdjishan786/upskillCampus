#!/usr/bin/env python3
"""
🔐 Secure Vault: Enterprise-Grade Command-Line Password Manager
Author: Professional Cryptography Refactor
Description: Implements secure database isolation using dynamic PBKDF2 
             Master-Key Derivation, Fernet authenticated payload encryption, 
             and strict interactive context guards.
"""

import os
import json
import re
import string
import secrets
import logging
import sqlite3
import getpass
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple, Any

import bcrypt
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
import base64

# ---------- Configuration & System Constants ----------
DB_PATH = Path("vault.db")
EXPORT_PATH = Path("vault_export.json")
LOG_PATH = Path("vault_manager.log")

# Structured Production Logger Config
logger = logging.getLogger("SecureVault")
logger.setLevel(logging.INFO)

if not logger.hasHandlers():
    log_format = logging.Formatter('[%(asctime)s] %(levelname)s: %(message)s')
    
    file_handler = logging.FileHandler(LOG_PATH, encoding='utf-8')
    file_handler.setFormatter(log_format)
    logger.addHandler(file_handler)


# ---------- Database Schema Controller ----------
class DatabaseManager:
    """Orchestrates relational storage transactions with operational isolation."""
    
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._initialize_tables()

    def get_connection(self) -> sqlite3.Connection:
        """Returns an operational connection to the SQLite database instance."""
        return sqlite3.connect(self.db_path)

    def _initialize_tables(self) -> None:
        """Initializes tables using explicit schema indices and configurations."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Encrypted Credentials Bucket Store
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS credentials (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    service TEXT NOT NULL,
                    username TEXT NOT NULL,
                    encrypted_payload TEXT NOT NULL,
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(service, username)
                )
            ''')
            
            # Master Identity Store containing the PBKDF2 Salt and Bcrypt verification hash
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS security_metadata (
                    id INTEGER PRIMARY KEY,
                    master_hash BLOB NOT NULL,
                    kdf_salt BLOB NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            conn.commit()


# ---------- Cryptographic Security Engine ----------
class CryptoEngine:
    """Manages secure key derivation mechanisms and authenticated message payloads."""

    @staticmethod
    def derive_fernet_key(master_password: str, salt: bytes) -> bytes:
        """Derives a highly secure 32-byte key from the master password using PBKDF2HMAC."""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=600_000, # Industry standard computing cost parameter
        )
        derived = kdf.derive(master_password.encode())
        return base64.urlsafe_b64encode(derived)

    def __init__(self, master_password: str, salt: bytes):
        fernet_key = self.derive_fernet_key(master_password, salt)
        self.cipher = Fernet(fernet_key)

    def encrypt(self, plaintext: str) -> str:
        """Encrypts data into a secure Fernet token string."""
        if not plaintext:
            return ""
        return self.cipher.encrypt(plaintext.encode('utf-8')).decode('utf-8')

    def decrypt(self, encrypted_token: str) -> str:
        """Decrypts a secure Fernet token back into plaintext string."""
        if not encrypted_token:
            return ""
        return self.cipher.decrypt(encrypted_token.encode('utf-8')).decode('utf-8')


# ---------- Core Vault Business Logic Operations ----------
class VaultService:
    """Implements structural access controls, metrics verification, and CRUD workflows."""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        self.active_engine: Optional[CryptoEngine] = None

    def initialize_master_identity(self) -> bool:
        """Sets up the initial master credentials and generates a secure KDF cryptographic salt."""
        print("\n🔐 INITIAL INITIALIZATION ROUTINE: SET MASTER CREDENTIALS")
        print("─" * 60)
        
        password = getpass.getpass("Create Master Vault Password: ")
        confirmation = getpass.getpass("Confirm Master Vault Password: ")

        if password != confirmation:
            print("❌ Input mismatch. Operations aborted.")
            return False

        if len(password) < 12: # Enforcing secure modern length floor standard
            print("❌ Vulnerability Alert: Master password length must contain minimum of 12 characters.")
            return False

        # Generate a cryptographically secure independent salt context
        kdf_salt = secrets.token_bytes(16)
        hashed_master = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt(rounds=12))

        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM security_metadata")
            cursor.execute(
                "INSERT INTO security_metadata (id, master_hash, kdf_salt) VALUES (1, ?, ?)",
                (hashed_master, kdf_salt)
            )
            conn.commit()
            
        logger.info("Successfully provisioned new secure master authorization identity framework.")
        return True

    def authenticate_vault_session(self) -> bool:
        """Verifies identity credentials and maps the running CryptoEngine pipeline context."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT master_hash, kdf_salt FROM security_metadata WHERE id = 1")
            row = cursor.fetchone()

        if not row:
            logger.info("Database records clear. Launching first-time deployment onboarding sequence.")
            if self.initialize_master_identity():
                return self.authenticate_vault_session()
            return False

        stored_hash, kdf_salt = row
        max_attempts = 3
        
        print("\n🔑 VAULT ACCESS AUTHORIZATION REQUIRED")
        print("─" * 60)

        for attempt in range(1, max_attempts + 1):
            entered_password = getpass.getpass("Enter Master Vault Password: ")
            
            if bcrypt.checkpw(entered_password.encode('utf-8'), stored_hash):
                # Dynamically spin up memory engine context using calculated salt parameters
                self.active_engine = CryptoEngine(entered_password, kdf_salt)
                logger.info("Vault framework verification token match. Operational session opened.")
                return True
                
            print(f"❌ Invalid authorization token sequence. [{max_attempts - attempt} remaining attempts]")
            
        logger.warning("Intrusion Alert: Session termination triggered due to excessive auth mismatches.")
        return False

    @staticmethod
    def evaluate_password_complexity(password: str) -> Tuple[str, str]:
        """Calculates security strength density matching entropy distributions."""
        score = 0
        if len(password) >= 12: score += 2
        elif len(password) >= 8: score += 1
        
        if re.search(r'[A-Z]', password): score += 1
        if re.search(r'[a-z]', password): score += 1
        if re.search(r'\d', password): score += 1
        if re.search(r'[!@#$%^&*(),.?":{}|<>]', password): score += 1

        if score >= 6: return "🟢 Strong", "High Entropy"
        if score >= 4: return "🟡 Medium", "Moderate Bounds"
        return "🔴 Critical Risk / Weak", "Insufficient Entropy"

    @staticmethod
    def generate_secure_password(length: int = 20) -> str:
        """Generates a secure, cryptographically random password matching standard character pools."""
        length = max(length, 12) # Clamp allocation bounds safely to enterprise parameters
        char_pool = string.ascii_letters + string.digits + "!@#$%^&*()-_=+"
        
        while True:
            candidate = ''.join(secrets.choice(char_pool) for _ in range(length))
            if (any(c.isupper() for c in candidate) and 
                any(c.islower() for c in candidate) and 
                any(c.isdigit() for c in candidate) and 
                any(c in "!@#$%^&*()-_=+" for c in candidate)):
                return candidate

    def add_credential(self, service: str, username: str, password_raw: str, notes: str = "") -> None:
        """Encrypts data payloads dynamically and updates record tracking safely."""
        if not self.active_engine: raise RuntimeError("Unverified session matrix context.")
        
        encrypted_token = self.active_engine.encrypt(password_raw)
        current_time = datetime.now(timezone.utc).isoformat()

        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO credentials (service, username, encrypted_payload, notes, updated_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (service.lower(), username, encrypted_token, notes, current_time))
            conn.commit()

        strength, _ = self.evaluate_password_complexity(password_raw)
        logger.info(f"Persisted credentials modification update mapping for: '{service}' | Metric: {strength}")

    def retrieve_credential(self, service: str) -> Optional[Dict[str, Any]]:
        """Decrypts and formats verified credentials context maps matching queries."""
        if not self.active_engine: raise RuntimeError("Unverified session matrix context.")

        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT username, encrypted_payload, notes, created_at, updated_at 
                FROM credentials WHERE service = ?
            ''', (service.lower(),))
            row = cursor.fetchone()

        if not row:
            print(f"❌ No registered service entry matches the identity context: '{service}'")
            return None

        username, encrypted_token, notes, created, updated = row
        try:
            decrypted_password = self.active_engine.decrypt(encrypted_token)
            return {
                "username": username,
                "password": decrypted_password,
                "notes": notes,
                "created_at": created,
                "updated_at": updated
            }
        except Exception as ex:
            logger.error(f"🔴 Fatal payload decipher mismatch on entity '{service}': {ex}")
            return None

    def list_inventory(self) -> None:
        """Displays formatted tracking indicators of active index inventories safely."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT service, username, updated_at FROM credentials ORDER BY service")
            records = cursor.fetchall()

        if not records:
            print("\n📭 Vault record inventory indexes empty.")
            return

        print(f"\n📋 SECURED VAULT DIRECTORY INDEX ({len(records)} Total Entries):")
        print("─" * 65)
        for service, user, updated in records:
            print(f" • Identifier: {service:<18} | Handle: {user:<22} | Logged: {updated[:10]}")

    def purge_credential(self, service: str) -> None:
        """Deletes target entries matching query indexes permanently."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM credentials WHERE service = ?", (service.lower(),))
            affected_rows = cursor.rowcount
            conn.commit()

        if affected_rows > 0:
            logger.info(f"Permanently purged system records associated to: '{service}'")
        else:
            print(f"❌ No execution matching signature record target: '{service}'")

    def export_vault_to_json(self) -> None:
        """Safely decrypts all passwords in memory and exports them to an unencrypted backup file."""
        if not self.active_engine: raise RuntimeError("Active session parameters missing.")
        
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT service, username, encrypted_payload, notes FROM credentials")
            rows = cursor.fetchall()

        if not rows:
            print("📭 Storage inventory tracking layer baseline clean. Export aborted.")
            return

        decrypted_export_set = []
        for service, user, encrypted_token, notes in rows:
            try:
                decrypted_export_set.append({
                    "service": service,
                    "username": user,
                    "password": self.active_engine.decrypt(encrypted_token),
                    "notes": notes or ""
                })
            except Exception:
                continue

        with open(EXPORT_PATH, 'w', encoding='utf-8') as stream:
            json.dump(decrypted_export_set, stream, indent=4, ensure_ascii=False)
        logger.info(f"📤 Export sequence processed successfully. Target resource located at: '{EXPORT_PATH}'")

    def import_vault_from_json(self) -> None:
        """Imports unencrypted records, encrypts them in the vault, and processes batch arrays."""
        if not EXPORT_PATH.is_file():
            print(f"❌ Data import parsing targeted asset path missing: '{EXPORT_PATH}'")
            return

        try:
            with open(EXPORT_PATH, 'r', encoding='utf-8') as stream:
                payload_batch = json.load(stream)
        except Exception as ex:
            print(f"❌ Structural schema validation formatting corruption failure: {ex}")
            return

        import_counter = 0
        for data_packet in payload_batch:
            try:
                self.add_credential(
                    service=data_packet['service'],
                    username=data_packet['username'],
                    password_raw=data_packet['password'],
                    notes=data_packet.get('notes', '')
                )
                import_counter += 1
            except KeyError as err:
                print(f"⚠️ Structural entity node syntax mapping invalid: Missing key framework value {err}")

        logger.info(f"📥 Vault import pipeline loop complete. Resolved and encrypted updates: {import_counter} Elements.")


# ---------- High Performance Command Console Router ----------
def main() -> None:
    """Manages interface parsing sequences and controls workflow logic loops."""
    db_manager = DatabaseManager(DB_PATH)
    vault = VaultService(db_manager)

    if not vault.authenticate_vault_session():
        print("🔒 Security Protocol: System execution execution lifecycle stopped.")
        return

    print("\n" + "═" * 60)
    print("  🔒 SECURE VAULT ACCESS FRAMEWORK SHELL INITIALIZED")
    print("═" * 60)
    print(" Terminal Command Route Handlers Menu Instructions:")
    print("   • add <service> <user> [pass]  -> Save/Update credentials map")
    print("   • get <service>                -> Decrypt targeted data profile")
    print("   • list                         -> List database services index")
    print("   • delete <service>             -> Wipe structural index target")
    print("   • gen [length]                 -> Generate robust random token")
    print("   • export / import              -> Process data backup payloads")
    print("   • help / exit                  -> Help guide / Safe close vault")
    print("═" * 60)

    while True:
        try:
            user_input = input("\nvault> ").strip().split()
            if not user_input: continue

            directive = user_input[0].lower()

            if directive == "add" and len(user_input) >= 3:
                target_service = user_input[1]
                target_user = user_input[2]
                
                if len(user_input) >= 4:
                    allocated_pass = user_input[3]
                else:
                    allocated_pass = vault.generate_secure_password()
                    print(f"🔑 Crypto Engine Generated Password: {allocated_pass}")
                    c_str, _ = vault.evaluate_password_complexity(allocated_pass)
                    print(f"📊 Evaluated Integrity Score Status  : {c_str}")
                    
                captured_notes = " ".join(user_input[4:]) if len(user_input) > 4 else ""
                vault.add_credential(target_service, target_user, allocated_pass, captured_notes)

            elif directive == "get" and len(user_input) == 2:
                profile = vault.retrieve_credential(user_input[1])
                if profile:
                    print(f"\n🔹 Resource Identity Mapping Target : {user_input[1].lower()}")
                    print(f"👤 Assigned Operator Handle Identity: {profile['username']}")
                    print(f"🔑 Decrypted Authenticated Password : {profile['password']}")
                    if profile['notes']:
                        print(f"📝 Bound Resource Meta Notes       : {profile['notes']}")
                    print(f"📅 Storage Record Ingestion Context : {profile['created_at']}")
                    print(f"🔄 Latest Transaction Sync State    : {profile['updated_at']}")

            elif directive == "list":
                vault.list_inventory()

            elif directive == "delete" and len(user_input) == 2:
                confirmation = input(f"⚠️ Confirm destructive structural wipe on resource target '{user_input[1]}'? (y/n): ")
                if confirmation.strip().lower() == 'y':
                    vault.purge_credential(user_input[1])

            elif directive == "gen":
                target_len = int(user_input[1]) if len(user_input) > 1 and user_input[1].isdigit() else 20
                generated_token = vault.generate_secure_password(target_len)
                c_str, _ = vault.evaluate_password_complexity(generated_token)
                print(f"🔑 Secure Output String Sequence: {generated_token}")
                print(f"📊 Computed Entropy Evaluation  : {c_str}")

            elif directive == "export":
                vault.export_vault_to_json()

            elif directive == "import":
                vault.import_vault_from_json()

            elif directive == "help":
                print("\nValid parameters sequences: add [s] [u] [p], get [s], list, delete [s], gen [l], export, import, exit")

            elif directive in ("exit", "quit"):
                print("🔒 Closing secure workspace memory threads. Vault locked. Goodbye.")
                break
            else:
                print(f"❌ Instruction parse mismatch: '{directive}'. Run parameter command 'help'.")

        except KeyboardInterrupt:
            print("\n🔒 Runtime processing sequence terminated via terminal intercept sign layer. Vault locked.")
            break
        except Exception as system_anomaly:
            logger.error(f"Critical Runtime System Anomaly Exception: {system_anomaly}", exc_info=True)


if __name__ == "__main__":
    main()
