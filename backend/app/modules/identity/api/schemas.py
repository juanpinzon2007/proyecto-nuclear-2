from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, SecretStr, model_validator

from app.modules.identity.domain.entities import AutorizacionesDocente, Rol


IdPublico = Annotated[str, Field(strict=True, min_length=1, max_length=200, pattern=r"^\S+$")]
CodigoPermiso = Annotated[str, Field(strict=True, min_length=1, max_length=100)]


class EsquemaIdentity(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)


class SolicitudLogin(EsquemaIdentity):
    correo: Annotated[str, Field(strict=True, min_length=3, max_length=254)]
    codigo_convocatoria: Annotated[SecretStr, Field(min_length=1, max_length=256)]


class RespuestaToken(EsquemaIdentity):
    access_token: str
    token_type: Literal["bearer"] = "bearer"


class SolicitudLoginPersonal(EsquemaIdentity):
    correo: Annotated[str, Field(strict=True, min_length=3, max_length=254)]
    # Compatible con el alta existente; sin inventar complejidad o caducidad.
    clave: Annotated[SecretStr, Field(min_length=1, max_length=1024)]


class AutorizacionesDocenteSchema(EsquemaIdentity):
    roles: frozenset[Rol] = frozenset({Rol.DOCENTE})
    permisos: frozenset[CodigoPermiso] = frozenset()

    @model_validator(mode="after")
    def exigir_docente(self):
        if Rol.DOCENTE not in self.roles:
            raise ValueError("Debe conservarse el rol docente.")
        return self

    def a_dominio(self) -> AutorizacionesDocente:
        return AutorizacionesDocente(self.roles, self.permisos)


class CrearDocente(AutorizacionesDocenteSchema):
    correo: Annotated[str, Field(strict=True, min_length=3, max_length=254)]
    nombre: Annotated[str | None, Field(min_length=1, max_length=120)] = None
    clave: Annotated[SecretStr | None, Field(min_length=1, max_length=1024)] = None

    @model_validator(mode="after")
    def validar_datos_alta(self):
        if (self.nombre is None) != (self.clave is None):
            raise ValueError("Nombre y clave deben proporcionarse juntos.")
        return self


class UsuarioPublico(EsquemaIdentity):
    id_usuario: str
    correo: str
    roles: frozenset[Rol]
    permisos: frozenset[str]

    @classmethod
    def desde_contexto(cls, contexto):
        return cls(id_usuario=contexto.id_usuario, correo=contexto.correo,
                   roles=contexto.roles, permisos=contexto.permisos)


class SolicitudRepeticion(EsquemaIdentity):
    id_sesion: IdPublico
    id_estudiante: IdPublico


class SolicitudFeedback(EsquemaIdentity):
    texto: Annotated[str, Field(strict=True, min_length=1, max_length=10_000)]
