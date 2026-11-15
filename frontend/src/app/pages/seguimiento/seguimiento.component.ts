import { Component, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatTableModule } from '@angular/material/table';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { IdentityService } from '../../core/identity.service';
import { ResumenCaso, ResumenParticipacion } from '../../core/api.models';
import { mensajeError } from '../../core/api-error';

@Component({
  selector: 'app-seguimiento',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    RouterLink,
    MatCardModule,
    MatButtonModule,
    MatIconModule,
    MatTableModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    MatProgressSpinnerModule,
  ],
  template: `
    <div class="page">
      <div class="page-header">
        <div>
          <h1>Seguimiento Académico</h1>
          <p class="muted">Supervisión de participaciones de estudiantes, retroalimentación y descarga de reportes oficiales</p>
        </div>
      </div>

      @if (error()) {
        <div class="error-box">{{ error() }}</div>
      }
      @if (mensajeExito()) {
        <div class="success-box">{{ mensajeExito() }}</div>
      }

      <!-- Generador y Descarga de Reporte Oficial de Sesión -->
      <mat-card style="margin-bottom: 24px; border-left: 4px solid var(--mat-sys-tertiary);">
        <mat-card-header>
          <mat-card-title>Descargar Reporte Oficial de Sesión</mat-card-title>
        </mat-card-header>
        <mat-card-content style="padding-top: 16px;">
          <form (ngSubmit)="descargarReporte()" style="display: flex; gap: 12px; align-items: center; flex-wrap: wrap;">
            <mat-form-field appearance="outline" style="flex: 1; min-width: 250px;">
              <mat-label>UUID de la Sesión</mat-label>
              <input matInput [(ngModel)]="reporteSesionId" name="reporteSesionId" required placeholder="Ingresa el ID de la sesión finalizada" />
            </mat-form-field>

            <mat-form-field appearance="outline" style="width: 140px;">
              <mat-label>Formato</mat-label>
              <mat-select [(ngModel)]="reporteFormato" name="reporteFormato">
                <mat-option value="xlsx">Excel (XLSX)</mat-option>
                <mat-option value="pdf">Documento (PDF)</mat-option>
              </mat-select>
            </mat-form-field>

            <button mat-flat-button color="primary" type="submit" style="height: 56px;" [disabled]="descargandoReporte()">
              @if (descargandoReporte()) {
                <mat-spinner diameter="18"></mat-spinner>
              } @else {
                <span>Generar Reporte</span>
              }
            </button>
          </form>
        </mat-card-content>
      </mat-card>

      <!-- Casos para seguimiento -->
      <div class="row">
        <!-- Lista de Casos -->
        <mat-card style="flex: 1 1 350px;">
          <mat-card-header>
            <mat-card-title>Casos con Participación</mat-card-title>
          </mat-card-header>
          <mat-card-content style="padding-top: 16px;">
            @if (cargandoCasos()) {
              <div style="display: flex; justify-content: center; padding: 24px;">
                <mat-spinner diameter="30"></mat-spinner>
              </div>
            } @else if (casos().length === 0) {
              <p class="muted">No hay registros de seguimiento de casos disponibles.</p>
            } @else {
              <div class="stack">
                @for (c of casos(); track c.id_caso) {
                  <div class="caso-item" [class.seleccionado]="casoSeleccionado()?.id_caso === c.id_caso" (click)="seleccionarCaso(c)">
                    <div>
                      <div style="font-weight: 500;">{{ c.nombre }}</div>
                      <div class="mono muted" style="font-size: 11px;">ID: {{ c.id_caso }}</div>
                    </div>
                    <mat-icon color="primary">chevron_right</mat-icon>
                  </div>
                }
              </div>
            }
          </mat-card-content>
        </mat-card>

        <!-- Lista de Participaciones del Caso Seleccionado -->
        <mat-card style="flex: 2 1 500px;">
          <mat-card-header>
            <mat-card-title>
              Participaciones del Caso
              @if (casoSeleccionado(); as sc) {
                <span class="muted" style="font-size: 14px;">: {{ sc.nombre }}</span>
              }
            </mat-card-title>
          </mat-card-header>
          <mat-card-content style="padding-top: 16px;">
            @if (!casoSeleccionado()) {
              <p class="muted">Selecciona un caso de la lista para ver las participaciones registradas.</p>
            } @else if (cargandoParticipaciones()) {
              <div style="display: flex; justify-content: center; padding: 24px;">
                <mat-spinner diameter="30"></mat-spinner>
              </div>
            } @else if (participaciones().length === 0) {
              <p class="muted">No hay participaciones registradas para este caso aún.</p>
            } @else {
              <table mat-table [dataSource]="participaciones()" class="mat-elevation-z1">
                <ng-container matColumnDef="estudiante">
                  <th mat-header-cell *matHeaderCellDef>Estudiante</th>
                  <td mat-cell *matCellDef="let p">
                    <span class="mono">{{ p.id_estudiante }}</span>
                  </td>
                </ng-container>

                <ng-container matColumnDef="estado">
                  <th mat-header-cell *matHeaderCellDef>Estado</th>
                  <td mat-cell *matCellDef="let p">
                    <span class="chip" [class.ok]="p.estado === 'FINALIZADO' || p.estado === 'COMPLETA'">
                      {{ p.estado }}
                    </span>
                  </td>
                </ng-container>

                <ng-container matColumnDef="acciones">
                  <th mat-header-cell *matHeaderCellDef style="text-align: right;">Acciones</th>
                  <td mat-cell *matCellDef="let p" style="text-align: right;">
                    <a mat-button color="primary" [routerLink]="['/seguimiento/participaciones', p.id_participacion]">
                      <mat-icon>rate_review</mat-icon> Ver Respuestas y Feedback
                    </a>
                  </td>
                </ng-container>

                <tr mat-header-row *matHeaderRowDef="columnasParticipaciones"></tr>
                <tr mat-row *matRowDef="let row; columns: columnasParticipaciones;"></tr>
              </table>
            }
          </mat-card-content>
        </mat-card>
      </div>
    </div>
  `,
  styles: [`
    .caso-item {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 10px 12px;
      border-radius: 6px;
      cursor: pointer;
      border: 1px solid var(--mat-sys-outline-variant);
      background: white;
      transition: background 0.15s;
    }
    .caso-item:hover {
      background: var(--mat-sys-surface-container-low);
    }
    .caso-item.seleccionado {
      border-color: var(--mat-sys-primary);
      background: var(--mat-sys-primary-container);
    }
  `],
})
export class SeguimientoComponent implements OnInit {
  private readonly identityService = inject(IdentityService);

  readonly columnasParticipaciones = ['estudiante', 'estado', 'acciones'];
  readonly casos = signal<ResumenCaso[]>([]);
  readonly casoSeleccionado = signal<ResumenCaso | null>(null);
  readonly participaciones = signal<ResumenParticipacion[]>([]);

  readonly cargandoCasos = signal<boolean>(true);
  readonly cargandoParticipaciones = signal<boolean>(false);
  readonly descargandoReporte = signal<boolean>(false);
  readonly error = signal<string | null>(null);
  readonly mensajeExito = signal<string | null>(null);

  reporteSesionId = '';
  reporteFormato: 'xlsx' | 'pdf' = 'xlsx';

  ngOnInit(): void {
    this.cargarCasos();
  }

  cargarCasos(): void {
    this.cargandoCasos.set(true);
    this.identityService.casosSeguimiento().subscribe({
      next: (data) => {
        this.casos.set(data);
        this.cargandoCasos.set(false);
      },
      error: (err) => {
        this.error.set(mensajeError(err));
        this.cargandoCasos.set(false);
      },
    });
  }

  seleccionarCaso(c: ResumenCaso): void {
    this.casoSeleccionado.set(c);
    this.cargandoParticipaciones.set(true);
    this.identityService.participacionesCaso(c.id_caso).subscribe({
      next: (parts) => {
        this.participaciones.set(parts);
        this.cargandoParticipaciones.set(false);
      },
      error: (err) => {
        this.error.set(mensajeError(err));
        this.cargandoParticipaciones.set(false);
      },
    });
  }

  descargarReporte(): void {
    if (!this.reporteSesionId.trim()) return;
    this.descargandoReporte.set(true);
    this.error.set(null);

    this.identityService.reporteSesion(this.reporteSesionId.trim(), { formato: this.reporteFormato }).subscribe({
      next: (blob) => {
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `reporte_sesion_${this.reporteSesionId}.${this.reporteFormato}`;
        a.click();
        window.URL.revokeObjectURL(url);
        this.descargandoReporte.set(false);
        this.mensajeExito.set('Reporte generado y descargado correctamente.');
      },
      error: (err) => {
        this.error.set(mensajeError(err));
        this.descargandoReporte.set(false);
      },
    });
  }
}

