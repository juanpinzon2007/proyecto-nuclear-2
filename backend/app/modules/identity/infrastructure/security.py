"""JWT de acceso: algoritmo fijo, firma, emisor, audiencia y claims obligatorios."""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt
from jwt.exceptions import InvalidTokenError

from app.modules.identity.domain.entities import validar_id
from app.modules.identity.domain.errors import NoAutenticado, ReglaIdentidadInvalida


@dataclass(frozen=True)
class IdentidadToken:
    id_usuario: str
    id_convocatoria: str | None


class TokensJWT:
    def __init__(self, secreto: str, emisor: str, audiencia: str, minutos: int = 15) -> None:
        if len(secreto.encode("utf-8")) < 32 or not emisor.strip() or not audiencia.strip():
            raise ValueError("Configuración JWT incompleta.")
        if type(minutos) is not int or not 1 <= minutos <= 60:
            raise ValueError("Duración JWT inválida.")
        self._secreto = secreto
        self._emisor = emisor
        self._audiencia = audiencia
        self._duracion = timedelta(minutes=minutos)

    def emitir(self, id_usuario: str, id_convocatoria: str | None = None) -> str:
        validar_id(id_usuario)
        if id_convocatoria is not None:
            validar_id(id_convocatoria)
        ahora = int(datetime.now(UTC).timestamp())
        claims = {
            "sub": id_usuario, "iss": self._emisor, "aud": self._audiencia,
            "iat": ahora, "nbf": ahora, "exp": ahora + int(self._duracion.total_seconds()),
            "jti": str(uuid4()), "token_type": "access",
        }
        if id_convocatoria is not None:
            claims["convocatoria_id"] = id_convocatoria
        return jwt.encode(claims, self._secreto, algorithm="HS256")

    def verificar(self, token: str) -> IdentidadToken:
        try:
            claims = jwt.decode(
                token, self._secreto, algorithms=["HS256"],
                issuer=self._emisor, audience=self._audiencia,
                options={"require": ["sub", "iss", "aud", "iat", "nbf", "exp", "jti", "token_type"],
                         "strict_aud": True},
            )
            if (claims["token_type"] != "access" or claims["iss"] != self._emisor
                    or claims["aud"] != self._audiencia):
                raise NoAutenticado()
            if any(type(claims[c]) is not int for c in ("iat", "nbf", "exp")):
                raise NoAutenticado()
            if (claims["nbf"] != claims["iat"] or not 0 < claims["exp"] - claims["iat"] <= self._duracion.total_seconds()):
                raise NoAutenticado()
            validar_id(claims["sub"])
            validar_id(claims["jti"])
            convocatoria = claims.get("convocatoria_id")
            if "convocatoria_id" in claims:
                validar_id(convocatoria)
            return IdentidadToken(claims["sub"], convocatoria)
        except (InvalidTokenError, ReglaIdentidadInvalida, TypeError, ValueError):
            raise NoAutenticado() from None
