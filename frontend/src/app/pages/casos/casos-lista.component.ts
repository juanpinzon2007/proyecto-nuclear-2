import { Component, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatTableModule } from '@angular/material/table';
import { MatDialogModule } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { CasesService } from '../../core/cases.service';
import { AuthService } from '../../core/auth.service';
import { CasoPayload, CasoResumenResponse } from '../../core/api.models';
import { mensajeError } from '../../core/api-error';
import { UiDialogService } from '../../core/ui-dialog.service';

@Component({
  selector: 'app-casos-lista',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    RouterLink,
    MatCardModule,
    MatButtonModule,
    MatIconModule,
    MatTableModule,
    MatDialogModule,
    MatFormFieldModule,
    MatInputModule,
    MatProgressSpinnerModule,
  ],
  template: `
    <div class="page">
      <div class="page-header">
        <div>
          <p class="eyebrow">Consola de Autoría // RF-05 · RF-09</p>
          <h1>Casos de Estudio</h1>
          <p class="muted">Gestión de casos, escenas situacionales, opciones de decisión y rúbricas de evaluación</p>
        </div>
        <div class="header-right">
          <div class="stat-tile">
            <small>CASOS</small>
            <b>{{ casos().length }}</b>
          </div>
          @if (auth.tienePermiso('CREAR_CASOS')) {
            <div style="display:flex; gap:10px; flex-wrap:wrap;">
              <a mat-flat-button color="primary" routerLink="/casos/nuevo">
                <mat-icon>add_circle</mat-icon> Nuevo Caso Completo
              </a>
              <button mat-stroked-button (click)="mostrarFormularioCrear = !mostrarFormularioCrear">
                <mat-icon>{{ mostrarFormularioCrear ? 'close' : 'flash_on' }}</mat-icon>
                {{ mostrarFormularioCrear ? 'Cancelar' : 'Borrador Rápido' }}
              </button>
            </div>
          } @else {
            <span class="chip">Solo lectura (sin permiso CREAR_CASOS)</span>
          }
        </div>
      </div>

      @if (error()) {
        <div class="error-box">{{ error() }}</div>
      }
      @if (mensajeExito()) {
        <div class="success-box">{{ mensajeExito() }}</div>
      }

      <!-- Formulario para crear caso rápido -->
      @if (mostrarFormularioCrear) {
        <mat-card class="crear-card">
          <mat-card-header>
            <mat-card-title>Nuevo Caso de Simulación</mat-card-title>
            <mat-card-subtitle>Creación directa en estado BORRADOR para edición posterior</mat-card-subtitle>
          </mat-card-header>
          <mat-card-content style="padding-top: 16px;">
            <form (ngSubmit)="crearCaso()" class="stack">
              <div class="row">
                <mat-form-field appearance="outline">
                  <mat-label>Nombre del Caso</mat-label>
                  <input matInput [(ngModel)]="nuevoNombre" name="nuevoNombre" required placeholder="Ej: Caso 1: Dilema de Conformidad Grupal" />
                </mat-form-field>
                <mat-form-field appearance="outline" style="max-width: 200px;">
                  <mat-label>Tiempo Estimado (min)</mat-label>
                  <input matInput type="number" [(ngModel)]="nuevoTiempo" name="nuevoTiempo" required min="5" max="180" />
                </mat-form-field>
              </div>

              <mat-form-field appearance="outline" class="full">
                <mat-label>Desarrollo Situacional</mat-label>
                <textarea matInput rows="3" [(ngModel)]="nuevoDesarrollo" name="nuevoDesarrollo" required placeholder="Descripción del contexto situacional en el que se ubicarán las decisiones..."></textarea>
              </mat-form-field>

              <mat-form-field appearance="outline" class="full">
                <mat-label>Contexto / Historia</mat-label>
                <textarea matInput rows="3" [(ngModel)]="nuevoContexto" name="nuevoContexto" required placeholder="Antecedentes y rol asumido por el estudiante..."></textarea>
              </mat-form-field>

              <div style="display: flex; gap: 8px; justify-content: flex-end;">
                <button mat-button type="button" (click)="mostrarFormularioCrear = false">Cancelar</button>
                <button mat-flat-button color="primary" type="submit" [disabled]="guardando()">
                  @if (guardando()) {
                    <mat-spinner diameter="18"></mat-spinner>
                  } @else {
                    Guardar Borrador
                  }
                </button>
              </div>
            </form>
          </mat-card-content>
        </mat-card>
      }

      @if (cargando()) {
        <div class="center-spin">
          <mat-spinner diameter="40"></mat-spinner>
        </div>
      } @else if (casos().length === 0) {
        <mat-card class="empty-panel">
          <mat-icon class="empty-ico">folder_open</mat-icon>
          <h3>No hay casos registrados aún</h3>
          <p class="muted">Crea el primer caso para diseñar escenarios y programar sesiones académicas.</p>
        </mat-card>
      } @else {
        <h2 class="section-title">Repositorio de Casos</h2>
        <div class="table-container stagger">
          <table mat-table [dataSource]="casos()" class="mat-elevation-z1">
            <ng-container matColumnDef="numero">
              <th mat-header-cell *matHeaderCellDef style="width: 70px;">#</th>
              <td mat-cell *matCellDef="let c"><strong class="mono cyan">0{{ c.numero }}</strong></td>
            </ng-container>

            <ng-container matColumnDef="nombre">
              <th mat-header-cell *matHeaderCellDef>Nombre del Caso</th>
              <td mat-cell *matCellDef="let c">
                <div style="font-weight: 600; color: var(--text);">{{ c.nombre }}</div>
                <div class="mono muted" style="font-size: 11px;">ID: {{ c.version_id }}</div>
              </td>
            </ng-container>

            <ng-container matColumnDef="tiempo">
              <th mat-header-cell *matHeaderCellDef>Tiempo</th>
              <td mat-cell *matCellDef="let c"><span class="mono">{{ c.tiempo_estimado_min }} MIN</span></td>
            </ng-container>

            <ng-container matColumnDef="estado">
              <th mat-header-cell *matHeaderCellDef>Estado</th>
              <td mat-cell *matCellDef="let c">
                <span class="chip" [class.ok]="c.estado === 'PUBLICADO'" [class.warn]="c.estado === 'BORRADOR'" [class.bad]="c.estado === 'ARCHIVADO'">
                  {{ c.estado }}
                </span>
              </td>
            </ng-container>

            <ng-container matColumnDef="creado">
              <th mat-header-cell *matHeaderCellDef>Fecha</th>
              <td mat-cell *matCellDef="let c"><span class="mono muted">{{ c.creado_en | date:'shortDate' }}</span></td>
            </ng-container>

            <ng-container matColumnDef="acciones">
              <th mat-header-cell *matHeaderCellDef style="text-align: right;">Acciones</th>
              <td mat-cell *matCellDef="let c" style="text-align: right;">
                <a mat-button color="primary" [routerLink]="['/casos', c.version_id]" title="Ver Escenarios y Rúbrica">
                  <mat-icon>visibility</mat-icon> Detalle
                </a>
                <a mat-button [routerLink]="['/casos', c.version_id, 'grafo']" title="Ver / Editar Grafo de Escenas">
                  <mat-icon>account_tree</mat-icon> Grafo
                </a>
                @if (c.estado === 'BORRADOR' && auth.tienePermiso('CREAR_CASOS')) {
                  <a mat-button [routerLink]="['/casos', c.version_id, 'editar']" title="Editar estructura completa y rúbrica">
                    <mat-icon>edit</mat-icon> Editar
                  </a>
                  <button mat-button color="accent" (click)="publicar(c.version_id)" title="Publicar caso para permitir sesiones">
                    <mat-icon>publish</mat-icon> Publicar
                  </button>
                }
                @if (c.estado === 'PUBLICADO' && auth.tienePermiso('CREAR_CASOS')) {
                  <button mat-button color="warn" (click)="archivar(c.version_id)" title="Archivar versión">
                    <mat-icon>archive</mat-icon> Archivar
                  </button>
                }
              </td>
            </ng-container>

            <tr mat-header-row *matHeaderRowDef="columnas"></tr>
            <tr mat-row *matRowDef="let row; columns: columnas;"></tr>
          </table>
        </div>
      }
    </div>
  `,
  styles: [`
    .header-right {
      display: flex;
      align-items: center;
      gap: 14px;
      flex-wrap: wrap;
    }
    .stat-tile {
      min-width: 88px;
      padding: 8px 14px;
      border: 1px solid var(--line-strong);
      background: #1a212b;
      font-family: var(--mono);
    }
    .stat-tile small {
      display: block;
      font-size: 10px;
      color: var(--cyan);
      letter-spacing: 1px;
    }
    .stat-tile b {
      font-size: 20px;
      color: var(--text);
    }
    .crear-card {
      margin-bottom: 24px;
      border-left: 4px solid var(--cyan) !important;
    }
    .empty-panel {
      text-align: center;
      padding: 42px 20px !important;
    }
    .empty-ico {
      font-size: 48px;
      width: 48px;
      height: 48px;
      color: var(--dim);
      margin-bottom: 8px;
    }
    .table-container {
      overflow-x: auto;
      background: rgba(16, 20, 27, 0.94);
      border: 1px solid var(--line);
      border-radius: 0;
    }
  `],
})
export class CasosListaComponent implements OnInit {
  private readonly casesService = inject(CasesService);
  private readonly router = inject(Router);
  private readonly uiDialog = inject(UiDialogService);
  readonly auth = inject(AuthService);

  readonly columnas = ['numero', 'nombre', 'tiempo', 'estado', 'creado', 'acciones'];
  readonly casos = signal<CasoResumenResponse[]>([]);
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
        this.mensajeExito.set('Caso creado en BORRADOR. Redirigiendo al editor para configurar escenarios y rúbrica...');
        void this.router.navigate(['/casos', res.version_id, 'editar']);
      },
      error: (err) => {
        this.error.set(mensajeError(err));
        this.guardando.set(false);
      },
    });
  }

  async publicar(versionId: string): Promise<void> {
    const ok = await this.uiDialog.confirmar({
      eyebrow: 'Validación y Publicación // RF-09',
      titulo: 'Publicar Versión del Caso',
      mensaje: '¿Deseas publicar esta versión del caso? Una vez publicada, quedará inmutable y disponible para programar sesiones académicas.',
      botonConfirmar: 'Publicar Caso',
      botonCancelar: 'Cancelar',
      tono: 'green',
    });
    if (!ok) return;
    this.error.set(null);
    this.casesService.publicar(versionId).subscribe({
      next: () => {
        this.mensajeExito.set('Caso publicado exitosamente.');
        this.cargarCasos();
      },
      error: (err) => this.error.set(mensajeError(err)),
    });
  }

  async archivar(versionId: string): Promise<void> {
    const ok = await this.uiDialog.confirmar({
      eyebrow: 'Gestión de Versiones // Casos',
      titulo: 'Archivar Caso',
      mensaje: '¿Deseas archivar esta versión del caso? Dejará de mostrarse como versión activa para nuevas sesiones.',
      botonConfirmar: 'Archivar Versión',
      botonCancelar: 'Cancelar',
      tono: 'warn',
    });
    if (!ok) return;
    this.error.set(null);
    this.casesService.archivar(versionId).subscribe({
      next: () => {
        this.mensajeExito.set('Caso archivado.');
        this.cargarCasos();
      },
      error: (err) => this.error.set(mensajeError(err)),
    });
  }
}

