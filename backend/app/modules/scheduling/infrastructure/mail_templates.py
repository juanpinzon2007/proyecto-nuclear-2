"""Identidad visual de los mensajes transaccionales de SPS."""

from html import escape
from datetime import datetime
from urllib.parse import urljoin, urlsplit


_FLUJOS = (
    ("Código de verificación", "Seguridad de la cuenta", "Verifica tu correo con el código de este mensaje."),
    ("Recuperación de contraseña", "Seguridad de la cuenta", "Usa tu código temporal para recuperar el acceso."),
    ("Cuenta ", "Acceso a SPS", "Tu cuenta ya está registrada en la plataforma."),
    ("Registro en grupo", "Grupos académicos", "Consulta los detalles de tu matrícula."),
    ("Caso creado", "Casos de estudio", "Tu nuevo caso quedó guardado como borrador."),
    ("Rúbrica asignada", "Evaluación", "La rúbrica quedó vinculada al caso."),
    ("Caso publicado", "Casos de estudio", "El caso ya está disponible para programar sesiones."),
    ("Convocatoria académica", "Simulación estudiantil", "Consulta el horario y conserva tu código personal."),
    ("Retiro de convocatoria", "Simulación estudiantil", "La autorización para esta sesión cambió."),
    ("Actualización en sesión", "Programación académica", "Consulta el horario y el lugar actualizados."),
    ("Resultados oficiales", "Seguimiento académico", "Ya puedes consultar tu resultado en la plataforma."),
    ("Nueva retroalimentación", "Seguimiento académico", "Tu docente agregó comentarios a tu participación."),
)
_CAMPOS = {"Caso", "Inicio programado", "Fin programado", "Lugar o enlace"}
_CAMPOS_CODIGO = {"Código individual", "Código de verificación", "Código de recuperación"}


def renderizar_correo(asunto: str, cuerpo: str, url_publica: str, codigo: str | None = None) -> str:
    enlace = escape(url_publica, quote=True)
    categoria, resumen = next(
        ((categoria, resumen) for prefijo, categoria, resumen in _FLUJOS if asunto.startswith(prefijo)),
        ("Notificación de SPS", "Tienes un mensaje del Simulador de Psicología Social."),
    )
    logo = ""
    if urlsplit(url_publica).scheme == "https":
        logo_url = escape(urljoin(url_publica, "/logo-sps.png"), quote=True)
        logo = (
            f'<img src="{logo_url}" width="40" height="40" alt="" '
            'style="display:block;border:0;border-radius:8px;margin:0 0 12px">'
        )

    parrafos = []
    for linea in cuerpo.splitlines():
        linea = linea.strip()
        if not linea or linea in {f"URL: {url_publica}", f"Plataforma: {url_publica}"}:
            continue
        etiqueta, separador, valor = linea.partition(": ")
        if codigo and separador and valor == codigo and etiqueta in _CAMPOS_CODIGO:
            parrafos.append(
                '<table role="presentation" width="100%" cellspacing="0" cellpadding="0" '
                'style="margin:0 0 16px"><tr><td bgcolor="#e8f7fa" '
                'style="padding:16px;color:#17394b;border:1px solid #a5dbe5;border-radius:10px">'
                f'<p style="margin:0 0 6px;font-size:14px">{escape(etiqueta)}</p>'
                '<p style="margin:0;font-family:monospace;font-size:23px;'
                f'font-weight:bold;letter-spacing:1px">{escape(codigo)}</p></td></tr></table>'
            )
            continue
        if separador and etiqueta in _CAMPOS:
            if etiqueta in {"Inicio programado", "Fin programado"}:
                try:
                    fecha = datetime.fromisoformat(valor)
                    valor = fecha.strftime("%d/%m/%Y · %H:%M")
                    offset = fecha.strftime("%z")
                    if offset:
                        valor += f" (UTC{offset[:3]}:{offset[3:]})"
                except ValueError:
                    pass
            parrafos.append(
                '<p style="margin:0 0 4px;padding:10px 12px;background:#f1f6fa;'
                'border-left:3px solid #4893aa;overflow-wrap:anywhere">'
                f'<strong style="font-size:13px;color:#334c61">{escape(etiqueta)}</strong><br>{escape(valor)}</p>'
            )
            continue
        parrafos.append(f'<p style="margin:0 0 14px;overflow-wrap:anywhere">{escape(linea)}</p>')

    return f"""<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>{escape(asunto)}</title>
</head>
<body style="margin:0;background:#edf3f8;color:#172b3c;font-family:Arial,sans-serif">
  <div style="display:none;max-height:0;overflow:hidden;mso-hide:all" aria-hidden="true">{resumen}</div>
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" bgcolor="#edf3f8">
    <tr><td align="center" style="padding:20px 10px">
      <!--[if mso]><table role="presentation" width="600" cellspacing="0" cellpadding="0"><tr><td><![endif]-->
      <table role="presentation" width="100%" cellspacing="0" cellpadding="0" bgcolor="#ffffff"
             style="max-width:600px;border:1px solid #cedce7;border-radius:14px">
        <tr><td bgcolor="#101b2a" style="padding:22px;color:#e6f9ff;border-top:4px solid #75d9ec;
                                       border-radius:13px 13px 0 0">
          {logo}<strong style="color:#e6f9ff">Simulador de Psicología Social</strong>
        </td></tr>
        <tr><td style="padding:22px;font-size:16px;line-height:1.55">
          <p style="margin:0 0 8px;color:#23576b;font-size:14px;font-weight:bold">{categoria}</p>
          <h1 style="margin:0 0 16px;color:#101b2a;font-size:25px;line-height:1.2">{escape(asunto)}</h1>
          {''.join(parrafos)}
          <table role="presentation" cellspacing="0" cellpadding="0" style="margin:20px 0 12px">
            <tr><td bgcolor="#b5e9f4" style="border-radius:8px;mso-padding-alt:11px 18px">
              <a href="{enlace}" style="display:inline-block;padding:11px 18px;color:#102c40;
                 text-decoration:none;font-weight:bold;mso-padding-alt:0">Abrir la plataforma SPS</a>
            </td></tr>
          </table>
          <p style="margin:0;font-size:13px;color:#405468;overflow-wrap:anywhere">
            Si el botón no abre, usa este enlace: <a href="{enlace}" style="color:#165068">{enlace}</a>
          </p>
        </td></tr>
        <tr><td bgcolor="#f3f7fb" style="padding:16px 22px;color:#405468;font-size:13px;
                                       line-height:1.5;border-radius:0 0 13px 13px">
          Mensaje automático del Simulador de Psicología Social. Si necesitas ayuda, contacta a tu institución.
        </td></tr>
      </table>
      <!--[if mso]></td></tr></table><![endif]-->
    </td></tr>
  </table>
</body>
</html>"""
