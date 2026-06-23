import bcrypt
import hashlib
import base64
import os
import json
import secrets
import datetime
import mydatabase
from cryptography.fernet import Fernet

db = mydatabase.database("database.txt")

# In-memory session store: { token: { "username": str, "expires": datetime } }
_sessions = {}
SESSION_LIFETIME_MINUTES = 60

# Load bad passwords list once at import time
_badpasswords = set()
try:
    with open("badpasswords.txt") as passlist:
        for line in passlist:
            word = line.strip()
            if word:
                _badpasswords.add(word.lower())
except FileNotFoundError:
    pass


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _derive_key(password: str, salt: bytes) -> bytes:
    """Derive a 32-byte key from a password and salt using PBKDF2-HMAC-SHA256.
    This is used to encrypt/decrypt per-user data — the server never stores it."""
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 390000)


def _fernet(key: bytes) -> Fernet:
    return Fernet(base64.urlsafe_b64encode(key))


def _encrypt(data: str, key: bytes) -> str:
    """Encrypt a JSON string, return a base64 string safe for JSON storage."""
    return _fernet(key).encrypt(data.encode("utf-8")).decode("utf-8")


def _decrypt(data: str, key: bytes) -> str:
    """Decrypt a base64 string back to a JSON string. Raises on bad key/data."""
    return _fernet(key).decrypt(data.encode("utf-8")).decode("utf-8")


def _purge_expired_sessions():
    now = datetime.datetime.utcnow()
    expired = [t for t, s in _sessions.items() if s["expires"] <= now]
    for t in expired:
        del _sessions[t]


# ---------------------------------------------------------------------------
# Public API — all functions return ("success"|"fail", payload)
# ---------------------------------------------------------------------------

def register(username: str, password: str) -> tuple:
    """Create a new account.
    Returns ("success", None) or ("fail", reason_string)."""
    if not username or not password:
        return ("fail", "username and password are required")
    if len(username) > 64:
        return ("fail", "username too long")
    if len(password) < 8:
        return ("fail", "password too short")
    if password.lower() in _badpasswords:
        return ("fail", "password is too common")

    db.read()
    users = db.database.setdefault("users", {})

    if username in users:
        return ("fail", "user already exists")

    # bcrypt handles its own salt internally
    pw_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    # Separate salt for PBKDF2 key derivation (not reusing the bcrypt salt)
    kdf_salt = os.urandom(32)
    key = _derive_key(password, kdf_salt)
    initial_data = _encrypt(json.dumps({}), key)

    users[username] = {
        "pw_hash": pw_hash,
        "kdf_salt": base64.b64encode(kdf_salt).decode("utf-8"),
        "user_data": initial_data,
    }
    db.write()
    return ("success", None)


def login(username: str, password: str) -> tuple:
    """Authenticate and return a session token.
    Returns ("success", token_string) or ("fail", reason_string)."""
    db.read()
    user = db.database.get("users", {}).get(username)
    if user is None:
        # Run a dummy bcrypt check to avoid timing-based username enumeration
        bcrypt.checkpw(password.encode("utf-8"), bcrypt.hashpw(b"dummy", bcrypt.gensalt()))
        return ("fail", "invalid username or password")

    if not bcrypt.checkpw(password.encode("utf-8"), user["pw_hash"].encode("utf-8")):
        return ("fail", "invalid username or password")

    _purge_expired_sessions()
    token = secrets.token_urlsafe(32)
    _sessions[token] = {
        "username": username,
        "expires": datetime.datetime.utcnow() + datetime.timedelta(minutes=SESSION_LIFETIME_MINUTES),
    }
    return ("success", token)


def logout(token: str) -> tuple:
    """Invalidate a session token.
    Returns ("success", None) or ("fail", reason_string)."""
    if token in _sessions:
        del _sessions[token]
        return ("success", None)
    return ("fail", "invalid or expired session")


def validate_session(token: str) -> tuple:
    """Check whether a token is valid and not expired.
    Returns ("success", username) or ("fail", reason_string)."""
    _purge_expired_sessions()
    session = _sessions.get(token)
    if session is None:
        return ("fail", "invalid or expired session")
    return ("success", session["username"])


def get_user_data(token: str, password: str) -> tuple:
    """Retrieve the decrypted user data dict for the session owner.
    Password is required to derive the decryption key.
    Returns ("success", data_dict) or ("fail", reason_string)."""
    status, username = validate_session(token)
    if status != "success":
        return ("fail", username)

    db.read()
    user = db.database.get("users", {}).get(username)
    if user is None:
        return ("fail", "user not found")

    kdf_salt = base64.b64decode(user["kdf_salt"])
    key = _derive_key(password, kdf_salt)
    try:
        data = json.loads(_decrypt(user["user_data"], key))
    except Exception:
        return ("fail", "decryption failed — wrong password or corrupted data")
    return ("success", data)


def set_user_data(token: str, password: str, data: dict) -> tuple:
    """Encrypt and store a user data dict for the session owner.
    Password is required to derive the encryption key.
    Returns ("success", None) or ("fail", reason_string)."""
    status, username = validate_session(token)
    if status != "success":
        return ("fail", username)

    db.read()
    users = db.database.get("users", {})
    user = users.get(username)
    if user is None:
        return ("fail", "user not found")

    # Verify password before allowing a write
    if not bcrypt.checkpw(password.encode("utf-8"), user["pw_hash"].encode("utf-8")):
        return ("fail", "invalid password")

    kdf_salt = base64.b64decode(user["kdf_salt"])
    key = _derive_key(password, kdf_salt)
    user["user_data"] = _encrypt(json.dumps(data), key)
    db.write()
    return ("success", None)


def delete_account(token: str, password: str) -> tuple:
    """Permanently delete an account and invalidate the session.
    Returns ("success", None) or ("fail", reason_string)."""
    status, username = validate_session(token)
    if status != "success":
        return ("fail", username)

    db.read()
    users = db.database.get("users", {})
    user = users.get(username)
    if user is None:
        return ("fail", "user not found")

    if not bcrypt.checkpw(password.encode("utf-8"), user["pw_hash"].encode("utf-8")):
        return ("fail", "invalid password")

    del users[username]
    db.write()

    # Invalidate all sessions for this user
    to_remove = [t for t, s in _sessions.items() if s["username"] == username]
    for t in to_remove:
        del _sessions[t]

    return ("success", None)
