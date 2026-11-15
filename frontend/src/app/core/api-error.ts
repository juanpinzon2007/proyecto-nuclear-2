import { HttpErrorResponse } from '@angular/common/http';

/** Convierte cualquier error HTTP del backend en un mensaje legible en español. */
export function mensajeError(err: unknown): string {
  if (err instanceof HttpErrorResponse) {
    if (err.status === 0) {
      return 'No hay conexión con el backend. Verifica que la API esté corriendo en http://localhost:8000.';
    }
    const detail = (err.error && typeof err.error === 'object') ? (err.error as { detail?: unknown }).detail : undefined;
    let texto = '';
    if (typeof detail === 'string') {
      texto = detail;
    } else if (Array.isArray(detail)) {
      // Errores de validación de FastAPI (422)
      texto = detail
        .map((d: { loc?: unknown[]; msg?: string }) => `${(d.loc ?? []).slice(1).join('.')}: ${d.msg ?? ''}`)
        .join(' · ');
    } else if (detail && typeof detail === 'object') {
      const d = detail as { mensaje?: string; codigo?: string; campos?: string[] | null };
      texto = d.mensaje ?? d.codigo ?? '';
      if (d.campos?.length) texto += ` (campos: ${d.campos.join(', ')})`;
    }
    const porEstado: Record<number, string> = {
      401: 'Sesión no válida o expirada. Inicia sesión nuevamente.',
      403: 'No tienes permiso para realizar esta acción.',
      404: 'Recurso no encontrado.',
      409: 'Conflicto con el estado actual del recurso.',
      422: 'Datos inválidos.',
      503: 'Funcionalidad no disponible en este momento (integración o configuración pendiente en el servidor).',
    };
    const base = porEstado[err.status] ?? `Error ${err.status}.`;
    return texto ? `${base} ${texto}` : base;
  }
  return err instanceof Error ? err.message : 'Error inesperado.';
}

