"""
Модуль для безопасного (зашифрованного) хранения API-ключа.
Использует симметричное шифрование Fernet (AES-128 в режиме CBC + HMAC).

Логика:
  1. Если есть SOURCE_TXT_FILE (api_key.txt) — читаем ключ оттуда,
     шифруем в STORAGE_FILE (auth.enc), удаляем txt (чтобы не хранить
     ключ в открытом виде) и возвращаем его.
  2. Иначе — читаем уже зашифрованный auth.enc.
"""
import os
from cryptography.fernet import Fernet, InvalidToken


KEY_FILE = "secret.key"          # файл с ключом шифрования (не коммитить!)
STORAGE_FILE = "auth.enc"        # файл с зашифрованным api-key
SOURCE_TXT_FILE = "api_key.txt"  # исходный txt с ключом (удаляется после шифрования)


def _load_or_create_cipher() -> Fernet:
    if not os.path.exists(KEY_FILE):
        key = Fernet.generate_key()
        with open(KEY_FILE, "wb") as f:
            f.write(key)
        # На UNIX-системах ограничим права доступа
        try:
            os.chmod(KEY_FILE, 0o600)
        except OSError:
            pass
    with open(KEY_FILE, "rb") as f:
        return Fernet(f.read())


def _read_from_txt() -> str | None:
    if not os.path.exists(SOURCE_TXT_FILE):
        return None
    try:
        with open(SOURCE_TXT_FILE, "r", encoding="utf-8") as f:
            key = f.read().strip()
    except OSError as e:
        print(f"⚠️  Не удалось прочитать {SOURCE_TXT_FILE}: {e}")
        return None

    if not key:
        print(f"⚠️  Файл {SOURCE_TXT_FILE} пустой.")
        return None
    return key


def _remove_txt() -> None:
    try:
        if os.path.exists(SOURCE_TXT_FILE):
            os.remove(SOURCE_TXT_FILE)
    except OSError as e:
        print(f"⚠️  Не удалось удалить {SOURCE_TXT_FILE}: {e}")


def save_api_key(api_key: str) -> None:
    cipher = _load_or_create_cipher()
    token = cipher.encrypt(api_key.encode("utf-8"))
    with open(STORAGE_FILE, "wb") as f:
        f.write(token)
    try:
        os.chmod(STORAGE_FILE, 0o600)
    except OSError:
        pass


def load_api_key() -> str | None:
    txt_key = _read_from_txt()
    if txt_key:
        save_api_key(txt_key)
        _remove_txt()
        print(f"🔐 Ключ из {SOURCE_TXT_FILE} зашифрован в {STORAGE_FILE} "
              f"и удалён из открытого файла.")
        return txt_key

    if not os.path.exists(STORAGE_FILE):
        return None
    cipher = _load_or_create_cipher()
    try:
        with open(STORAGE_FILE, "rb") as f:
            return cipher.decrypt(f.read()).decode("utf-8")
    except InvalidToken:
        print("⚠️  Не удалось расшифровать сохранённый ключ (файл повреждён).")
        return None


def clear_api_key() -> None:
    """Удаляет сохранённый ключ (для выхода из аккаунта)."""
    if os.path.exists(STORAGE_FILE):
        os.remove(STORAGE_FILE)