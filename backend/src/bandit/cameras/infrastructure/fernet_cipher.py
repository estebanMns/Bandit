"""Cifrado de URLs de cámara: pueden contener usuario y clave."""

from cryptography.fernet import Fernet


class FernetUrlCipher:
    def __init__(self, key: str) -> None:
        self._fernet = Fernet(key.encode())

    def encrypt(self, url: str) -> str:
        return self._fernet.encrypt(url.encode()).decode()

    def decrypt(self, encrypted: str) -> str:
        return self._fernet.decrypt(encrypted.encode()).decode()
