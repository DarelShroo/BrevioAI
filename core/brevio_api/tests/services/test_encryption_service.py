import base64
import os

import pytest

from core.brevio_api.services.encryption_service import (
    EncryptionError,
    EncryptionService,
)


def test_encryption_service_valid_key():
    key = base64.urlsafe_b64encode(os.urandom(32)).decode("utf-8")
    service = EncryptionService(key=key)

    plaintext = "sk-1234567890"
    user_id = "user1"
    credential_id = "cred1"
    provider = "openai"

    encrypted = service.encrypt(plaintext, user_id, credential_id, provider)
    assert encrypted != plaintext

    decrypted = service.decrypt(encrypted, user_id, credential_id, provider)
    assert decrypted == plaintext


def test_encryption_service_invalid_aad():
    key = base64.urlsafe_b64encode(os.urandom(32)).decode("utf-8")
    service = EncryptionService(key=key)

    plaintext = "sk-1234567890"
    encrypted = service.encrypt(plaintext, "user1", "cred1", "openai")

    with pytest.raises(EncryptionError):
        # Wrong user_id
        service.decrypt(encrypted, "user2", "cred1", "openai")


def test_encryption_service_invalid_key_length():
    key = base64.urlsafe_b64encode(os.urandom(16)).decode("utf-8")
    with pytest.raises(EncryptionError):
        EncryptionService(key=key)
