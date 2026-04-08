from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings


class SecretsService:
    prefix = "enc::"

    def __init__(self) -> None:
        self._fernet = Fernet(self._resolve_key())

    def _resolve_key(self) -> bytes:
        raw = (settings.app_encryption_key or settings.jwt_secret or "replace-me").strip().encode("utf-8")
        digest = hashlib.sha256(raw).digest()
        return base64.urlsafe_b64encode(digest)

    def is_encrypted(self, value: str | None) -> bool:
        return bool(value and value.startswith(self.prefix))

    def encrypt_if_needed(self, value: str | None) -> str:
        if not value:
            return ""
        if self.is_encrypted(value):
            return value
        token = self._fernet.encrypt(value.encode("utf-8")).decode("utf-8")
        return f"{self.prefix}{token}"

    def decrypt_if_needed(self, value: str | None) -> str:
        if not value:
            return ""
        if not self.is_encrypted(value):
            return value
        payload = value[len(self.prefix) :]
        try:
            return self._fernet.decrypt(payload.encode("utf-8")).decode("utf-8")
        except InvalidToken:
            return ""


secrets_service = SecretsService()
