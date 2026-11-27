import { expect, it } from 'vitest';
import { avatarUsuario, inferirGeneroUsuario } from './user-avatar';

it.each([
  ['admin@sps.edu.co', 1, 'male-1'], ['docente@sps.edu.co', 2, 'male-2'],
  ['estudiante@unihumboldt.edu.co', 3, 'female-1'], ['estudiante2@unihumboldt.edu.co', 5, 'male-3'],
] as const)('identifica la cuenta %s tanto por correo como por id', (correo, id_usuario, imagen) => {
  expect(avatarUsuario({ correo })).toBe('/avatars/' + imagen + '.jpg');
  expect(avatarUsuario({ id_usuario })).toBe('/avatars/' + imagen + '.jpg');
});

it.each([
  [{nombre: ' Dra. María '}, 'F'], [{nombre: 'Borja'}, 'M'],
  [{nombre: 'Helia'}, 'F'], [{nombre: 'Silvio'}, 'M'],
  [{correo: 'andrea@ejemplo.test'}, 'F'], [{correo: 'borja@ejemplo.test'}, 'M'],
  [{correo: 'helia@ejemplo.test'}, 'F'], [{}, 'M'],
  [{correo: 'estudiante@unihumboldt.edu.co'}, 'F'],
  [{correo: 'estudiante2@unihumboldt.edu.co'}, 'M'],
  [{correo: 'docente@sps.edu.co'}, 'M'], [{correo: 'admin@sps.edu.co'}, 'M'],
] as const)('selecciona la familia de avatar para %j', (datos, familia) => {
  expect(inferirGeneroUsuario(datos)).toBe(familia);
  expect(avatarUsuario(datos)).toMatch(familia === 'F' ? /female-[123]\.jpg$/ : /\/male-[123]\.jpg$/);
});
