"""Cifrado de URLs de cámara: pueden contener usuario y clave."""

from cryptography.fernet import Fernet, InvalidToken

from bandit.cameras.domain.ports import UnreadableUrlError


class FernetUrlCipher:
    def __init__(self, key: str) -> None:
        self._fernet = Fernet(key.encode())

    def encrypt(self, url: str) -> str:
        return self._fernet.encrypt(url.encode()).decode()

    def decrypt(self, encrypted: str) -> str:
        try:
            return self._fernet.decrypt(encrypted.encode()).decode()
        except InvalidToken as error:
            raise UnreadableUrlError(
                "La cámara se guardó con otra CAMERA_ENCRYPTION_KEY"
            ) from error
