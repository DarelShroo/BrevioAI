import base64
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from core.brevio_api.config.dotenv import load_dotenv

load_dotenv()


class EncryptionError(Exception):
    pass


class EncryptionService:
    def __init__(self, key: str = None):
        self._key_str = key or os.getenv("CREDENTIAL_ENCRYPTION_KEY")
        if not self._key_str:
            from core.shared.utils.environment import is_production_environment

            # Fallback for development. In production, this should fail.
            if is_production_environment():
                raise ValueError("CREDENTIAL_ENCRYPTION_KEY must be set in production")
            self._key_str = base64.urlsafe_b64encode(
                b"01234567890123456789012345678901"
            ).decode("utf-8")

        try:
            self._key = base64.urlsafe_b64decode(self._key_str)
            if len(self._key) != 32:
                raise ValueError("Key must be 32 bytes for AES-256")
            self._aesgcm = AESGCM(self._key)
        except Exception as e:
            raise EncryptionError(f"Failed to initialize EncryptionService: {e}")

    def encrypt(
        self, plaintext: str, user_id: str, credential_id: str, provider: str
    ) -> str:
        """
        Encrypts the plaintext using AES-256-GCM.
        AAD is built from user_id, credential_id, and provider.
        Returns a base64 encoded string containing nonce + ciphertext.
        """
        try:
            aad = self._build_aad(user_id, credential_id, provider)
            nonce = os.urandom(12)
            ciphertext = self._aesgcm.encrypt(nonce, plaintext.encode("utf-8"), aad)
            return base64.urlsafe_b64encode(nonce + ciphertext).decode("utf-8")
        except Exception as e:
            raise EncryptionError(f"Encryption failed: {e}")

    def decrypt(
        self, encrypted_payload: str, user_id: str, credential_id: str, provider: str
    ) -> str:
        """
        Decrypts the payload using AES-256-GCM.
        """
        try:
            aad = self._build_aad(user_id, credential_id, provider)
            raw_data = base64.urlsafe_b64decode(encrypted_payload)
            if len(raw_data) < 12:
                raise ValueError("Invalid payload: too short")
            nonce = raw_data[:12]
            ciphertext = raw_data[12:]
            plaintext = self._aesgcm.decrypt(nonce, ciphertext, aad)
            return plaintext.decode("utf-8")
        except Exception as e:
            raise EncryptionError(f"Decryption failed: {e}")

    def _build_aad(self, user_id: str, credential_id: str, provider: str) -> bytes:
        return f"{user_id}:{credential_id}:{provider}".encode("utf-8")
