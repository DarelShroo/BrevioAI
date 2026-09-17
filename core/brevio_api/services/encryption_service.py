import base64
import logging
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from core.brevio_api.config.dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# Historical development fallback (used when CREDENTIAL_ENCRYPTION_KEY was unset).
_DEV_FALLBACK_KEY = base64.urlsafe_b64encode(
    b"01234567890123456789012345678901"
).decode("utf-8")


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
            self._key_str = _DEV_FALLBACK_KEY

        self._aesgcm = self._build_aesgcm(self._key_str)
        self._previous_aesgcm = None
        previous = (os.getenv("CREDENTIAL_ENCRYPTION_KEY_PREVIOUS") or "").strip()
        if previous and previous != self._key_str:
            try:
                self._previous_aesgcm = self._build_aesgcm(previous)
            except EncryptionError:
                logger.warning(
                    "CREDENTIAL_ENCRYPTION_KEY_PREVIOUS is invalid; ignoring"
                )

    @staticmethod
    def _build_aesgcm(key_str: str) -> AESGCM:
        try:
            key = base64.urlsafe_b64decode(key_str)
            if len(key) != 32:
                raise ValueError("Key must be 32 bytes for AES-256")
            return AESGCM(key)
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
        Falls back to CREDENTIAL_ENCRYPTION_KEY_PREVIOUS when set (key rotation).
        """
        aad = self._build_aad(user_id, credential_id, provider)
        try:
            raw_data = base64.urlsafe_b64decode(encrypted_payload)
            if len(raw_data) < 12:
                raise ValueError("Invalid payload: too short")
            nonce = raw_data[:12]
            ciphertext = raw_data[12:]
        except Exception as e:
            raise EncryptionError(f"Decryption failed: {e}")

        try:
            plaintext = self._aesgcm.decrypt(nonce, ciphertext, aad)
            return plaintext.decode("utf-8")
        except Exception as primary_error:
            if self._previous_aesgcm is not None:
                try:
                    plaintext = self._previous_aesgcm.decrypt(nonce, ciphertext, aad)
                    logger.info(
                        "Credential decrypted with PREVIOUS encryption key "
                        "(re-save credential to re-encrypt with current key)"
                    )
                    return plaintext.decode("utf-8")
                except Exception:
                    pass
            raise EncryptionError(f"Decryption failed: {primary_error}")

    def _build_aad(self, user_id: str, credential_id: str, provider: str) -> bytes:
        return f"{user_id}:{credential_id}:{provider}".encode("utf-8")
