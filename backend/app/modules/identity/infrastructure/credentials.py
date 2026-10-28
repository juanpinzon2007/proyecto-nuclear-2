from functools import lru_cache

from pwdlib import PasswordHash


@lru_cache
def obtener_hasheador() -> PasswordHash:
    return PasswordHash.recommended()
