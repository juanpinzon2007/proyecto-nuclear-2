from app.modules.identity.application.ports import RepositorioUsuarios, TokensAcceso, ValidadorConvocatoria
from app.modules.identity.domain.entities import Rol, normalizar_correo, validar_id
from app.modules.identity.domain.errors import IntegracionPendiente, NoAutenticado, ReglaIdentidadInvalida


class ServicioAutenticacion:
    def __init__(self, usuarios: RepositorioUsuarios, convocatorias: ValidadorConvocatoria,
                 tokens: TokensAcceso, dominios_institucionales: tuple[str, ...]) -> None:
        self.usuarios = usuarios
        self.convocatorias = convocatorias
        self.tokens = tokens
        self.dominios = frozenset(d.strip().casefold() for d in dominios_institucionales if d.strip())

    def autenticar_estudiante(self, correo: str, codigo: str) -> str:
        if not self.dominios:
            raise IntegracionPendiente()
        try:
            correo = normalizar_correo(correo)
        except ReglaIdentidadInvalida:
            raise NoAutenticado() from None
        if correo.split("@")[1] not in self.dominios or not codigo.strip():
            raise NoAutenticado()
        acceso = self.convocatorias.validar(correo, codigo)
        if acceso is None:
            raise NoAutenticado()
        validar_id(acceso.id_usuario)
        validar_id(acceso.id_convocatoria)
        usuario = self.usuarios.obtener(acceso.id_usuario)
        if (usuario is None or not usuario.activo or usuario.id_usuario != acceso.id_usuario
                or Rol.ESTUDIANTE not in usuario.roles):
            raise NoAutenticado()
        try:
            coincide_correo = normalizar_correo(usuario.correo) == correo
        except ReglaIdentidadInvalida:
            raise NoAutenticado() from None
        if not coincide_correo:
            raise NoAutenticado()
        return self.tokens.emitir(usuario.id_usuario, acceso.id_convocatoria)
