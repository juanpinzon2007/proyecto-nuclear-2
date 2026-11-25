import { CommonModule } from '@angular/common';
import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatPaginatorModule } from '@angular/material/paginator';
import { MatSelectModule } from '@angular/material/select';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatTableModule } from '@angular/material/table';
import { firstValueFrom } from 'rxjs';
import { mensajeError } from '../../core/api-error';
import { ConvocatoriaDetalleResponse, EstudianteDisponibleItem } from '../../core/api.models';
import { SchedulingService } from '../../core/scheduling.service';
import { avatarUsuario } from '../../core/user-avatar';

import { etiquetaEstado, ListaPaginada } from '../../core/lista-paginada';

@Component({
  selector: 'app-convocatorias',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    RouterLink,
    MatCardModule,
    MatTableModule,
    MatFormFieldModule,
    MatSelectModule,
    MatButtonModule,
    MatIconModule,
    MatPaginatorModule,
    MatSnackBarModule,
  ],
  template: `
    <div class="conv-wrap">
      <div class="page-header">
        <div class="page-heading">
          <a mat-icon-button routerLink="/programacion" aria-label="Volver a programación" title="Volver a programación"><mat-icon>arrow_back</mat-icon></a>
          <div>
            <p class="eyebrow">Control de acceso</p>
            <h2>Convocatorias y códigos de autorización</h2>
            <p class="subtitle">Sesión <span class="mono">{{ sesionId }}</span></p>
          </div>
        </div>
      </div>

      <div class="grid-2">
        <mat-card class="panel panel-cyan-left">
          <mat-card-header>
            <mat-card-title>Emitir convocatoria</mat-card-title>
            @if (estadoSesion() === 'SIN_INICIAR') {
              <mat-card-subtitle>El estudiante recibirá su código de acceso en el correo institucional.</mat-card-subtitle>
            }
          </mat-card-header>
          <mat-card-content style="padding-top:16px;">
            @if (estadoSesion() === 'SIN_INICIAR') {
              <form (ngSubmit)="convocar()" class="stack-form">
                <mat-form-field appearance="outline">
                  <mat-label>Estudiante registrado</mat-label>
                  <mat-select [(ngModel)]="estudianteSeleccionadoUuid" name="estUuid" required>
                    @for (e of estudiantesConUuid(); track e.id_usuario) {
                      <mat-option [value]="e.uuid_scheduling">{{ e.nombre }} — {{ e.correo }}</mat-option>
                    }
                  </mat-select>
                </mat-form-field>
                <div class="action-group form-actions">
                  <button mat-flat-button color="primary" type="submit" [disabled]="!estudianteSeleccionadoUuid || cargando()">
                    <mat-icon>mail_outline</mat-icon> Convocar por correo
                  </button>
                </div>
              </form>
            } @else {
              <p class="muted" role="status">
                @if (cargando()) { Consultando el estado de la sesión… }
                @else if (estadoSesion()) { Las convocatorias se emiten antes de iniciar la sesión. }
                @else { El estado de esta sesión no está disponible. }
              </p>
            }
          </mat-card-content>
        </mat-card>

        <mat-card class="panel">
          <mat-card-header>
            <mat-card-title>Estudiantes convocados ({{ convocatorias().length }})</mat-card-title>
          </mat-card-header>
          <mat-card-content class="invitation-content" [attr.aria-busy]="cargando()">
            @if (convocatorias().length) {
              <label class="list-search invitation-search">
                <span>Buscar convocatoria</span>
                <input type="search" placeholder="Estudiante, correo o estado" [value]="lista.busqueda()"
                       (input)="lista.buscar($any($event.target).value)" />
              </label>
              <div class="invitation-scroll" tabindex="0" role="region" aria-label="Tabla de convocatorias">
                <table mat-table [dataSource]="lista.visibles()" class="invitation-table" aria-label="Estudiantes convocados">
                  <ng-container matColumnDef="estudiante">
                    <th mat-header-cell *matHeaderCellDef>Estudiante</th>
                    <td mat-cell *matCellDef="let c">
                      <div class="user-inline">
                        @let estudiante = estudiantesPorUuid().get(c.estudiante_id);
                        <img class="game-avatar" [src]="avatarEstudiante(estudiante)" alt="" />
                        <div>
                          <strong>{{ estudiante?.nombre || 'Estudiante convocado' }}</strong>
                          @if (estudiante) {
                            <div class="muted invitation-ref">{{ estudiante.correo }}</div>
                          } @else {
                            <div class="mono muted invitation-ref">{{ c.estudiante_id }}</div>
                          }
                        </div>
                      </div>
                    </td>
                  </ng-container>
                  <ng-container matColumnDef="estado">
                    <th mat-header-cell *matHeaderCellDef>Estado</th>
                    <td mat-cell *matCellDef="let c">
                      <span class="chip" [class.ok]="c.estado === 'ACTIVA'" [class.bad]="c.estado !== 'ACTIVA'">{{ etiquetaEstado(c.estado) }}</span>
                    </td>
                  </ng-container>
                  <ng-container matColumnDef="acciones">
                    <th mat-header-cell *matHeaderCellDef>Acción</th>
                    <td mat-cell *matCellDef="let c">
                      @if (c.estado === 'ACTIVA') {
                        <button mat-stroked-button color="warn" type="button" (click)="retirar(c.id)"
                                [disabled]="cargando()">Retirar</button>
                      }
                    </td>
                  </ng-container>
                  <tr mat-header-row *matHeaderRowDef="['estudiante', 'estado', 'acciones']"></tr>
                  <tr mat-row *matRowDef="let row; columns: ['estudiante', 'estado', 'acciones']"></tr>
                  <tr *matNoDataRow>
                    <td class="muted" colspan="3">No hay convocatorias que coincidan con la búsqueda.</td>
                  </tr>
                </table>
              </div>
              <mat-paginator [length]="lista.filtrados().length" [pageIndex]="lista.pagina()"
                             [pageSize]="lista.tamano()" [pageSizeOptions]="[10, 20, 50]"
                             (page)="lista.cambiar($event)" showFirstLastButtons
                             aria-label="Paginación de convocatorias" />
            } @else {
              <p class="muted" role="status">
                {{ cargando() ? 'Cargando estudiantes convocados…' : 'Aún no hay estudiantes convocados.' }}
              </p>
            }
          </mat-card-content>
        </mat-card>
      </div>
    </div>
  `,
  styles: [`
    .conv-wrap { padding: 4px 0 36px; max-width: 1160px; margin: 0 auto; }
    .subtitle { margin: 4px 0 0; color: var(--muted); font-size: 13px; }
    .grid-2 { display: grid; grid-template-columns: minmax(0, 21rem) minmax(0, 1fr); gap: 20px; align-items: start; }
    @media (max-width: 950px) { .grid-2 { grid-template-columns: minmax(0, 1fr); gap: 0; } }
    .stack-form { display: flex; flex-direction: column; gap: 12px; }
    .invitation-content { min-width: 0; padding-top: 12px; }
    .invitation-search { margin-bottom: 12px; }
    .invitation-scroll { overflow-x: auto; }
    .invitation-table { width: 100%; min-width: 17rem; table-layout: fixed; }
    .invitation-table :is(th, td) { padding: 8px; }
    .invitation-table .mat-column-estudiante { overflow-wrap: anywhere; }
    .invitation-table .mat-column-estudiante .user-inline > div { min-width: 0; }
    .invitation-table .mat-column-estado { width: 6rem; }
    .invitation-table .mat-column-acciones { width: 6.5rem; text-align: end; }
    .invitation-ref { font-size: var(--type-meta); }
    @media (max-width: 500px) {
      .invitation-table .game-avatar { display: none; }
      .invitation-table .mat-column-estado { width: 4.5rem; }
      .invitation-table .mat-column-acciones { width: 4.75rem; }
      .invitation-table button { min-width: 0; padding-inline: 6px; }
    }
  `],
})
export class ConvocatoriasComponent implements OnInit {
  readonly etiquetaEstado = etiquetaEstado;
  private readonly route = inject(ActivatedRoute);
  private readonly scheduling = inject(SchedulingService);
  private readonly snack = inject(MatSnackBar);

  sesionId = '';
  readonly cargando = signal(false);
  readonly estadoSesion = signal<string | null>(null);
  readonly convocatorias = signal<ConvocatoriaDetalleResponse[]>([]);
  readonly estudiantes = signal<EstudianteDisponibleItem[]>([]);
  readonly estudiantesPorUuid = computed(() => new Map(
    this.estudiantesConUuid().map((estudiante) => [estudiante.uuid_scheduling, estudiante]),
  ));
  readonly lista = new ListaPaginada(
    this.convocatorias,
    (convocatoria) => `${this.nombreEstudiante(convocatoria.estudiante_id)} ${etiquetaEstado(convocatoria.estado)}`,
  );
  estudianteSeleccionadoUuid = '';

  ngOnInit(): void {
    this.sesionId = this.route.snapshot.paramMap.get('id') ?? '';
    if (this.sesionId) void this.cargar();
  }

  estudiantesConUuid(): EstudianteDisponibleItem[] {
    return this.estudiantes().filter((e) => !!e.uuid_scheduling);
  }

  async cargar(): Promise<void> {
    this.cargando.set(true);
    try {
      const [convs, ests, sesion] = await Promise.all([
        firstValueFrom(this.scheduling.convocatorias(this.sesionId)),
        firstValueFrom(this.scheduling.estudiantes()),
        firstValueFrom(this.scheduling.sesion(this.sesionId)),
      ]);
      this.convocatorias.set(convs);
      this.estudiantes.set(ests);
      this.estadoSesion.set(sesion.estado);
    } catch (e) {
      this.snack.open(mensajeError(e), 'Cerrar', { duration: 4000 });
    } finally {
      this.cargando.set(false);
    }
  }

  async convocar(): Promise<void> {
    if (!this.estudianteSeleccionadoUuid || this.estadoSesion() !== 'SIN_INICIAR' || this.cargando()) return;
    this.cargando.set(true);
    try {
      await firstValueFrom(this.scheduling.crearConvocatoria(this.sesionId, this.estudianteSeleccionadoUuid));
      this.snack.open('Convocatoria registrada. El código quedó en cola para enviarse por correo.', 'Cerrar', { duration: 4000 });
      await this.cargar();
    } catch (e) {
      this.snack.open(mensajeError(e), 'Cerrar', { duration: 4500 });
    } finally {
      this.cargando.set(false);
    }
  }

  async retirar(convId: string): Promise<void> {
    this.cargando.set(true);
    try {
      await firstValueFrom(this.scheduling.retirarConvocatoria(this.sesionId, convId));
      this.snack.open('Convocatoria retirada.', 'OK', { duration: 2500 });
      await this.cargar();
    } catch (e) {
      this.snack.open(mensajeError(e), 'Cerrar', { duration: 4000 });
    } finally {
      this.cargando.set(false);
    }
  }

  nombreEstudiante(uuid: string): string {
    const e = this.estudiantesPorUuid().get(uuid);
    return e ? `${e.nombre} (${e.correo})` : uuid;
  }

  avatarEstudiante(e: EstudianteDisponibleItem | undefined): string {
    return avatarUsuario({
      id_usuario: e?.id_usuario,
      nombre: e?.nombre,
      correo: e?.correo,
      rol: 'ESTUDIANTE',
    });
  }
}
