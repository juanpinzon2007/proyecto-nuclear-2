import { Component, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatTableModule } from '@angular/material/table';
import { MatDialogModule } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { CasesService } from '../../core/cases.service';
import { CasoPayload, CasoResumenResponse } from '../../core/api.models';
import { mensajeError } from '../../core/api-error';

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
          <h1>Casos de Estudio</h1>
          <p class="muted">Gestión de casos, escenas situacionales, opciones de decisión y rúbricas de evaluación</p>
        </div>
        <button mat-flat-button color="primary" (click)="mostrarFormularioCrear = !mostrarFormularioCrear">
          <mat-icon>{{ mostrarFormularioCrear ? 'close' : 'add' }}</mat-icon>
          {{ mostrarFormularioCrear ? 'Cancelar' : 'Crear Caso' }}
        </button>
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
        <div style="display: flex; justify-content: center; padding: 40px;">
          <mat-spinner diameter="40"></mat-spinner>
        </div>
      } @else if (casos().length === 0) {
        <mat-card style="text-align: center; padding: 40px;">
          <mat-icon style="font-size: 48px; width: 48px; height: 48px; opacity: 0.5;">folder_open</mat-icon>
          <h3>No hay casos registrados aún</h3>
          <p class="muted">Crea el primer caso para diseñar escenarios y programar sesiones académicas.</p>
        </mat-card>
      } @else {
        <div class="table-container">
          <table mat-table [dataSource]="casos()" class="mat-elevation-z1">
            <ng-container matColumnDef="numero">
              <th mat-header-cell *matHeaderCellDef style="width: 70px;">#</th>
              <td mat-cell *matCellDef="let c"><strong>{{ c.numero }}</strong></td>
            </ng-container>

            <ng-container matColumnDef="nombre">
              <th mat-header-cell *matHeaderCellDef>Nombre del Caso</th>
              <td mat-cell *matCellDef="let c">
                <div style="font-weight: 500;">{{ c.nombre }}</div>
                <div class="mono muted" style="font-size: 11px;">ID: {{ c.version_id }}</div>
              </td>
            </ng-container>

            <ng-container matColumnDef="tiempo">
              <th mat-header-cell *matHeaderCellDef>Tiempo</th>
              <td mat-cell *matCellDef="let c">{{ c.tiempo_estimado_min }} min</td>
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
              <td mat-cell *matCellDef="let c">{{ c.creado_en | date:'shortDate' }}</td>
            </ng-container>

            <ng-container matColumnDef="acciones">
              <th mat-header-cell *matHeaderCellDef style="text-align: right;">Acciones</th>
              <td mat-cell *matCellDef="let c" style="text-align: right;">
                <a mat-button color="primary" [routerLink]="['/casos', c.version_id]" title="Ver Escenarios y Rúbrica">
                  <mat-icon>visibility</mat-icon> Detalle
                </a>
                <a mat-button [routerLink]="['/casos', c.version_id, 'grafo']" title="Ver Flujo de Escenas">
                  <mat-icon>account_tree</mat-icon> Grafo
                </a>
                @if (c.estado === 'BORRADOR') {
                  <button mat-button color="accent" (click)="publicar(c.version_id)" title="Publicar caso para permitir sesiones">
                    <mat-icon>publish</mat-icon> Publicar
                  </button>
                }
                @if (c.estado === 'PUBLICADO') {
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
    .crear-card {
      margin-bottom: 24px;
      border-left: 4px solid var(--mat-sys-primary);
    }
    .table-container {
      overflow-x: auto;
      background: white;
      border-radius: 8px;
    }
  `],
})
export class CasosListaComponent implements OnInit {
  private readonly casesService = inject(CasesService);

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
      next: () => {
        this.guardando.set(false);
        this.mostrarFormularioCrear = false;
        this.nuevoNombre = '';
        this.nuevoDesarrollo = '';
        this.nuevoContexto = '';
        this.mensajeExito.set('Caso creado correctamente en estado BORRADOR.');
        this.cargarCasos();
      },
      error: (err) => {
        this.error.set(mensajeError(err));
        this.guardando.set(false);
      },
    });
  }

  publicar(versionId: string): void {
    if (!confirm('¿Deseas publicar esta versión del caso? Una vez publicada, estará disponible para sesiones académicas.')) return;
    this.error.set(null);
    this.casesService.publicar(versionId).subscribe({
      next: () => {
        this.mensajeExito.set('Caso publicado exitosamente.');
        this.cargarCasos();
      },
      error: (err) => this.error.set(mensajeError(err)),
    });
  }

  archivar(versionId: string): void {
    if (!confirm('¿Deseas archivar esta versión del caso?')) return;
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

