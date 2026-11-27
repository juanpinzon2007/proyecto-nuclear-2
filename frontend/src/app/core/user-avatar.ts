export interface DatosAvatarUsuario {
  id_usuario?: string | number | null;
  correo?: string | null;
  nombre?: string | null;
  rol?: string | null;
}

const AVATARES_MASCULINOS = [
  '/avatars/male-1.jpg',
  '/avatars/male-2.jpg',
  '/avatars/male-3.jpg',
] as const;

const AVATARES_FEMENINOS = [
  '/avatars/female-1.jpg',
  '/avatars/female-2.jpg',
  '/avatars/female-3.jpg',
] as const;

const NOMBRES_FEMENINOS = new Set([
  'sofia', 'maria', 'laura', 'camila', 'valentina', 'paula', 'carolina', 'andrea',
  'natalia', 'daniela', 'juliana', 'luisa', 'mariana', 'alejandra', 'claudia',
  'patricia', 'diana', 'monica', 'elena', 'sara', 'lucia', 'gabriela', 'angela',
  'isabel', 'carmen', 'rosa', 'karen', 'estefania', 'adriana', 'marcela', 'johana',
  'jenny', 'veronica', 'tatiana', 'lina', 'ingrid', 'nancy', 'gloria', 'esperanza',
  'marisol', 'fernanda', 'valeria', 'catalina', 'manuela', 'salome', 'victoria',
  'clara', 'ana', 'juliet', 'julieta', 'alba', 'liliana', 'sandry', 'sandra',
  'beatriz', 'rocio', 'pilar', 'olga', 'martha', 'marta', 'ines', 'nora',
  'esther', 'silvia', 'miriam', 'katherine', 'karina', 'vanesa', 'vanessa',
  'jessica', 'yesica', 'paulina', 'amanda', 'stella', 'ruth', 'nohemi', 'raquel',
  'profesora', 'docente', 'administradora', 'dra', 'estudiante1',
]);

const EXCEPCIONES_MASCULINAS = new Set([
  'borja', 'luca', 'joshua', 'noa', 'garcia', 'silva', 'molina', 'bautista', 'mejía', 'mejia',
  'admin', 'administrador', 'docente', 'profesor', 'prof', 'carlos',
]);

function limpiarTexto(valor: string): string {
  return valor
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .trim();
}

export function inferirGeneroUsuario(datos: DatosAvatarUsuario): 'F' | 'M' {
  const correo = limpiarTexto(datos.correo ?? '');
  if (correo === 'estudiante@unihumboldt.edu.co') return 'F';
  if (correo === 'estudiante2@unihumboldt.edu.co' || correo === 'docente@sps.edu.co' || correo === 'admin@sps.edu.co') {
    return 'M';
  }

  const tokensNombre = limpiarTexto(datos.nombre ?? '')
    .split(/[^a-z]+/)
    .filter((t) => t.length >= 2 && !['prof', 'dr', 'ing', 'lic', 'sr', 'sra', 'estudiante', 'demo'].includes(t));

  for (const tok of tokensNombre) {
    if (NOMBRES_FEMENINOS.has(tok)) return 'F';
    if (EXCEPCIONES_MASCULINAS.has(tok)) return 'M';
  }
  if (tokensNombre.length > 0) {
    const primero = tokensNombre[0];
    if (primero.endsWith('a') && !EXCEPCIONES_MASCULINAS.has(primero)) return 'F';
    return 'M';
  }

  const localCorreo = correo.split('@', 1)[0];
  const tokensCorreo = localCorreo.split(/[^a-z]+/).filter((t) => t.length >= 2);
  for (const tok of tokensCorreo) {
    if (NOMBRES_FEMENINOS.has(tok)) return 'F';
    if (EXCEPCIONES_MASCULINAS.has(tok)) return 'M';
  }
  if (tokensCorreo.length > 0 && tokensCorreo[0].endsWith('a') && !EXCEPCIONES_MASCULINAS.has(tokensCorreo[0])) {
    return 'F';
  }

  return 'M';
}

function hashClave(clave: string): number {
  let h = 2166136261;
  for (let i = 0; i < clave.length; i++) {
    h ^= clave.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return Math.abs(h);
}

/**
 * Devuelve un avatar estilo videojuego 3D acorde al género del usuario y único para las cuentas base.
 */
export function avatarUsuario(datos: DatosAvatarUsuario): string {
  const correo = limpiarTexto(datos.correo ?? '');
  const idStr = String(datos.id_usuario ?? '').trim();

  // Asignación distinta garantizada para cada cuenta principal de la plataforma
  if (correo === 'admin@sps.edu.co' || idStr === '1') return '/avatars/male-1.jpg';
  if (correo === 'docente@sps.edu.co' || idStr === '2') return '/avatars/male-2.jpg';
  if (correo === 'estudiante@unihumboldt.edu.co' || idStr === '3') return '/avatars/female-1.jpg';
  if (correo === 'estudiante2@unihumboldt.edu.co' || idStr === '5') return '/avatars/male-3.jpg';

  const genero = inferirGeneroUsuario(datos);
  const pool = genero === 'F' ? AVATARES_FEMENINOS : AVATARES_MASCULINOS;
  const semilla = `${idStr}:${correo || limpiarTexto(datos.nombre ?? 'user')}`;

  return pool[hashClave(semilla) % pool.length];
}
