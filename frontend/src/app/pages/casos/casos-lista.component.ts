import { DatePipe } from '@angular/common';
import { Component, computed, OnInit, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatPaginatorModule } from '@angular/material/paginator';
import { firstValueFrom } from 'rxjs';
import { CasesService } from '../../core/cases.service';
import { AuthService } from '../../core/auth.service';
import { CasoPayload, CasoResumenResponse } from '../../core/api.models';
import { mensajeError } from '../../core/api-error';
import { UiDialogService } from '../../core/ui-dialog.service';
import { ListaPaginada } from '../../core/lista-paginada';

@Component({
  selector: 'app-casos-lista',
  standalone: true,
  imports: [
    DatePipe,
    FormsModule,
    RouterLink,
    MatCardModule,
    MatButtonModule,
    MatIconModule,
    MatFormFieldModule,
    MatInputModule,
    MatProgressSpinnerModule,
    MatPaginatorModule,
  ],
  templateUrl: './casos-lista.component.html',
  styleUrl: './casos-lista.component.scss',
})
export class CasosListaComponent implements OnInit {
  private readonly casesService = inject(CasesService);
  private readonly router = inject(Router);
  private readonly uiDialog = inject(UiDialogService);
  readonly auth = inject(AuthService);

  readonly casos = signal<CasoResumenResponse[]>([]);
  readonly listaCasos = new ListaPaginada(
    () => this.casos(), (caso) => `${caso.nombre} ${caso.estado} ${caso.numero}`,
  );
  readonly eliminando = signal(false);
  readonly resumen = computed(() => {
    const cantidades = { PUBLICADO: 0, BORRADOR: 0, ARCHIVADO: 0 };
    for (const { estado } of this.casos()) {
      cantidades[estado] += 1;
    }
    return cantidades;
  });
  readonly cargando = signal<boolean>(true);
  readonly guardando = signal<boolean>(false);
  readonly error = signal<string | null>(null);
  readonly mensajeExito = signal<string | null>(null);

  mostrarFormularioCrear = false;
  nuevoNombre = '';
  nuevoTiempo = 30;
  nuevoDesarrollo = '';
  nuevoContexto = '';

  ngOnInit(): void {
    this.cargarCasos();
  }

  cargarCasos(): void {
    this.cargando.set(true);
    this.error.set(null);
    this.casesService.listar().subscribe({
      next: (data) => {
        this.casos.set(data);
        this.cargando.set(false);
      },
      error: (err) => {
        this.error.set(mensajeError(err));
        this.cargando.set(false);
      },
    });
  }

  crearCaso(): void {
    this.guardando.set(true);
    this.error.set(null);
    this.mensajeExito.set(null);

    const payload: CasoPayload = {
      case: {
        nombre: this.nuevoNombre,
        tiempoEstimadoMin: this.nuevoTiempo,
        desarrolloSituacional: this.nuevoDesarrollo,
        contextoHistoria: this.nuevoContexto,
      },
      scenarios: [],
    };

    this.casesService.crear(payload).subscribe({
      next: (res) => {
        this.guardando.set(false);
        this.mostrarFormularioCrear = false;
        this.nuevoNombre = '';
        this.nuevoDesarrollo = '';
        this.nuevoContexto = '';
        this.mensajeExito.set('Caso creado como borrador. Abriendo el editor…');
        void this.router.navigate(['/casos', res.version_id, 'editar']);
      },
      error: (err) => {
        this.error.set(mensajeError(err));
        this.guardando.set(false);
      },
    });
  }

  async eliminarBorrador(caso: CasoResumenResponse): Promise<void> {
    if (this.eliminando()) return;
    this.eliminando.set(true);
    try {
      if (!await this.uiDialog.confirmar({
        titulo: '¿Eliminar este borrador?',
        mensaje: `Se eliminará la versión ${caso.numero} de «${caso.nombre}». Esta acción es permanente.`,
        botonConfirmar: 'Eliminar borrador',
        tono: 'warn',
      })) return;
      this.error.set(null);
      this.mensajeExito.set(null);
      await firstValueFrom(this.casesService.eliminarBorrador(caso.version_id));
      this.casos.update((filas) => filas.filter((fila) => fila.version_id !== caso.version_id));
      this.mensajeExito.set('Borrador eliminado.');
    } catch (err) {
      this.error.set(mensajeError(err));
    } finally {
      this.eliminando.set(false);
    }
  }

  async publicar(versionId: string): Promise<void> {
    const ok = await this.uiDialog.confirmar({
      eyebrow: 'Validación y publicación',
      titulo: 'Publicar versión del caso',
      mensaje: '¿Deseas validar el caso, completar su recorrido si falta y publicarlo? Una vez publicada la versión quedará inmutable y lista para programar sesiones.',
      botonConfirmar: 'Publicar caso',
      botonCancelar: 'Cancelar',
      tono: 'green',
    });
    if (!ok) return;
    this.error.set(null);
    this.mensajeExito.set(null);
    try {
      await this.casesService.publicarInteligente(versionId);
      this.mensajeExito.set('Caso validado y publicado exitosamente.');
      this.cargarCasos();
    } catch (err) {
      const msg = mensajeError(err);
      this.error.set(msg);
      const irEditar = await this.uiDialog.confirmar({
        eyebrow: 'Publicación incompleta',
        titulo: 'Faltan datos obligatorios',
        mensaje: `${msg}\n\n¿Deseas abrir el editor para completar la rúbrica, justificaciones o escenarios?`,
        botonConfirmar: 'Ir al editor',
        botonCancelar: 'Cerrar',
        tono: 'amber',
      });
      if (irEditar) {
        void this.router.navigate(['/casos', versionId, 'editar']);
      }
    }
  }

  async archivar(versionId: string): Promise<void> {
    const ok = await this.uiDialog.confirmar({
      eyebrow: 'Gestión de casos',
      titulo: 'Archivar caso',
      mensaje: '¿Deseas archivar esta versión del caso? Dejará de mostrarse como versión activa para nuevas sesiones, y podrás republicarla como nueva versión cuando quieras.',
      botonConfirmar: 'Archivar versión',
      botonCancelar: 'Cancelar',
      tono: 'warn',
    });
    if (!ok) return;
    this.error.set(null);
    this.mensajeExito.set(null);
    this.casesService.archivar(versionId).subscribe({
      next: () => {
        this.mensajeExito.set('Caso archivado. Puedes usar «Republicar» o «Nueva versión».');
        this.cargarCasos();
      },
      error: (err) => this.error.set(mensajeError(err)),
    });
  }

  async republicar(versionId: string): Promise<void> {
    const ok = await this.uiDialog.confirmar({
      eyebrow: 'Reactivación del caso',
      titulo: 'Republicar como nueva versión',
      mensaje: 'Se creará y publicará una nueva versión (v+1) con los mismos escenarios, rúbrica y grafo, conservando intacto el histórico de la versión archivada.',
      botonConfirmar: 'Republicar',
      botonCancelar: 'Cancelar',
      tono: 'green',
    });
    if (!ok) return;
    this.error.set(null);
    this.mensajeExito.set(null);
    try {
      const res = await firstValueFrom(this.casesService.republicar(versionId));
      this.mensajeExito.set(`Nueva versión publicada (${res.version_id.slice(0, 8)}…) lista para programar sesiones.`);
      this.cargarCasos();
    } catch (err) {
      this.error.set(mensajeError(err));
    }
  }

  async clonarComoBorrador(versionId: string): Promise<void> {
    const ok = await this.uiDialog.confirmar({
      eyebrow: 'Versiones del caso',
      titulo: 'Crear una versión en borrador',
      mensaje: 'Se creará un borrador editable (v+1) copiando escenarios, opciones y rúbrica de esta versión para modificarlo y volver a publicar.',
      botonConfirmar: 'Crear borrador y editar',
      botonCancelar: 'Cancelar',
      tono: 'cyan',
    });
    if (!ok) return;
    this.error.set(null);
    try {
      const res = await firstValueFrom(this.casesService.clonar(versionId));
      void this.router.navigate(['/casos', res.version_id, 'editar']);
    } catch (err) {
      this.error.set(mensajeError(err));
    }
  }
}

