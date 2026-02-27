"""
Encryption utilities matching Fineract's EncryptionUtil:
  - AES-256-CBC with PBKDF2-SHA1 key derivation
  - BCrypt master password hashing
"""

import base64

from constants import SALT_SIZE, IV_SIZE, AES_KEY_SIZE, PBKDF2_ITERATIONS, BCRYPT_ROUNDS

try:
    from Crypto.Cipher import AES
    from Crypto.Hash import SHA1
    from Crypto.Protocol.KDF import PBKDF2
    from Crypto.Random import get_random_bytes
    from Crypto.Util.Padding import pad
except ImportError as exc:
    raise SystemExit("ERROR: PyCryptodome is required.\n  pip install pycryptodome") from exc

try:
    import bcrypt
except ImportError as exc:
    raise SystemExit("ERROR: bcrypt is required.\n  pip install bcrypt") from exc


class TenantEncryption:
    """AES/CBC/PKCS5Padding encryption matching Fineract's EncryptionUtil."""

    @staticmethod
    def encrypt(master_password: str, plain_password: str) -> str:
        """
        Encrypt *plain_password* with *master_password*.

        Returns a base64-encoded blob structured as:
            IV (16 B) | salt (16 B) | ciphertext
        """
        salt = get_random_bytes(SALT_SIZE)
        iv = get_random_bytes(IV_SIZE)
        key = PBKDF2(
            master_password,
            salt,
            dkLen=AES_KEY_SIZE,
            count=PBKDF2_ITERATIONS,
            hmac_hash_module=SHA1,
        )
        cipher = AES.new(key, AES.MODE_CBC, iv)
        ciphertext = cipher.encrypt(pad(plain_password.encode(), AES.block_size))
        return base64.b64encode(iv + salt + ciphertext).decode()

    @staticmethod
    def hash_master_password(master_password: str) -> str:
        """Return a BCrypt hash of *master_password*."""
        return bcrypt.hashpw(
            master_password.encode(),
            bcrypt.gensalt(rounds=BCRYPT_ROUNDS),
        ).decode()
