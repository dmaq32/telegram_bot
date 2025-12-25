import hashlib

def hash_telegram_id(telegram_id: int) -> str:
    return hashlib.sha256(str(telegram_id).encode('utf-8')).hexdigest()