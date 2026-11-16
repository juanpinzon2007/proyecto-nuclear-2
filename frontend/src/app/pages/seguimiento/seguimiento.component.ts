import { CommonModule } from '@angular/common';
import { Component, OnInit, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSelectModule } from '@angular/material/select';
import { MatTableModule } from '@angular/material/table';
import { firstValueFrom } from 'rxjs';
import { mensajeError } from '../../core/api-error';
import { ResumenCaso, ResumenParticipacion, SesionResponse } from '../../core/api.models';
import { IdentityService } from '../../core/identity.service';
import { SchedulingService } from '../../core/scheduling.service';

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
    MatSelectModule,
    MatProgressSpinnerModule,
  ],
  template: `
    <div class="page">
      <div class="page-header">
        <div>
          <h1>Seguimiento Académico y Reportes (RF-15 · RF-16)</h1>
          <p class="muted">Consulta participaciones por caso, revisa calificaciones, emite feedback docente y descarga actas oficiales.</p>
        </div>
      </div>

      @if (error()) { <div class="error-box">{{ error() }}</div> }
      @if (mensajeExito()) { <div class="success-box">{{ mensajeExito() }}</div> }

      <!-- Reporte Oficial RF-16 -->
      <mat-card style="margin-bottom: 24px; border-left: 4px solid #fbbf24;">
        <mat-card-header>
          <mat-card-title>Descargar Reporte Oficial de Sesión (RF-16)</mat-card-title>
          <mat-card-subtitle>Solo sesiones finalizadas con publicación oficial aprobada</mat-card-subtitle>
        </mat-card-header>
        <mat-card-content style="padding-top: 16px;">
          <form (ngSubmit)="descargarReporte()" style="display: flex; gap: 12px; align-items: center; flex-wrap: wrap;">
            <mat-form-field appearance="outline" style="flex: 1; min-width: 280px;">
              <mat-label>Seleccionar sesión</mat-label>
              <mat-select [(ngModel)]="reporteSesionId" name="reporteSesionId" required>
                @for (s of sesiones(); track s.id) {
                  <mat-option [value]="s.id">
                    {{ s.fecha_inicio | date:'short' }} · {{ s.estado }} ({{ s.lugar || 'Virtual' }})
                  </mat-option>
                }
              </mat-select>
            </mat-form-field>

            <mat-form-field appearance="outline" style="width: 150px;">
              <mat-label>Formato</mat-label>
              <mat-select [(ngModel)]="reporteFormato" name="reporteFormato">
                <mat-option value="xlsx">Excel (.xlsx)</mat-option>
                <mat-option value="pdf">PDF (.pdf)</mat-option>
              </mat-select>
            </mat-form-field>

            <button mat-flat-button color="primary" type="submit" [disabled]="descargandoReporte() || !reporteSesionId">
              <mat-icon>download</mat-icon> Descargar Reporte
            </button>
          </form>
        </mat-card-content>
      </mat-card>

      <div class="seg-grid">
        <!-- Casos con participaciones -->
        <mat-card>
          <mat-card-header>
            <mat-card-title>Casos con Participaciones ({{ casos().length }})</mat-card-title>
          </mat-card-header>
          <mat-card-content style="padding-top: 14px;">
            @if (cargandoCasos()) {
              <div style="display:flex; justify-content:center; padding:24px;"><mat-spinner diameter="30"></mat-spinner></div>
            } @else if (!casos().length) {
              <p class="muted">No hay participaciones estudiantiles registradas en tus casos aún.</p>
            } @else {
              <div class="stack" style="gap: 8px;">
                @for (c of casos(); track c.id_caso) {
                  <div class="caso-item" [class.seleccionado]="casoSeleccionado()?.id_caso === c.id_caso"
                       (click)="seleccionarCaso(c)">
                    <div>
                      <div style="font-weight: 600; color:#f8fafc;">{{ c.nombre }}</div>
                      <div class="mono muted" style="font-size: 11px;">{{ c.id_caso }}</div>
                    </div>
                    <mat-icon color="primary">chevron_right</mat-icon>
                  </div>
                }
              </div>
            }
          </mat-card-content>
        </mat-card>

        <!-- Participaciones del caso -->
        <mat-card>
          <mat-card-header>
            <mat-card-title>
              Participaciones del Caso
              @if (casoSeleccionado(); as sc) { <span>: {{ sc.nombre }}</span> }
            </mat-card-title>
          </mat-card-header>
          <mat-card-content style="padding-top: 14px;">
            @if (!casoSeleccionado()) {
              <p class="muted">Selecciona un caso para ver los estudiantes participantes.</p>
            } @else if (cargandoParticipaciones()) {
              <div style="display:flex; justify-content:center; padding:24px;"><mat-spinner diameter="30"></mat-spinner></div>
            } @else if (!participaciones().length) {
              <p class="muted">Sin participaciones registradas aún.</p>
            } @else {
              <table mat-table [dataSource]="participaciones()" style="width:100%;">
                <ng-container matColumnDef="estudiante">
                  <th mat-header-cell *matHeaderCellDef>Estudiante</th>
                  <td mat-cell *matCellDef="let p">
                    <div style="font-weight:600; color:#f8fafc;">{{ p.nombre_estudiante || 'Estudiante #' + p.id_estudiante }}</div>
                    <div class="muted" style="font-size:12px;">{{ p.correo_estudiante }}</div>
                  </td>
                </ng-container>

                <ng-container matColumnDef="nota">
                  <th mat-header-cell *matHeaderCellDef>Nota</th>
                  <td mat-cell *matCellDef="let p">
                    @if (p.nota_final !== null && p.nota_final !== undefined) {
                      <strong class="nota-txt">{{ p.nota_final | number:'1.1-2' }} / 100</strong>
                      <div class="muted" style="font-size:11px;">{{ p.modalidad }}</div>
                    } @else {
                      <span class="muted">Pendiente</span>
                    }
                  </td>
                </ng-container>

                <ng-container matColumnDef="estado">
                  <th mat-header-cell *matHeaderCellDef>Estado</th>
                  <td mat-cell *matCellDef="let p">
                    <span class="chip" [class.ok]="p.estado === 'finalizada' || p.estado === 'COMPLETA'">
                      {{ p.estado }}
                    </span>
                  </td>
                </ng-container>

                <ng-container matColumnDef="acciones">
                  <th mat-header-cell *matHeaderCellDef style="text-align:right;">Auditoría</th>
                  <td mat-cell *matCellDef="let p" style="text-align:right;">
                    <a mat-stroked-button color="primary" [routerLink]="['/seguimiento/participaciones', p.id_participacion]">
                      <mat-icon>rate_review</mat-icon> Respuestas & Feedback
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
    .seg-grid { display: grid; grid-template-columns: 320px 1fr; gap: 20px; align-items: start; }
    @media (max-width: 960px) { .seg-grid { grid-template-columns: 1fr; } }
    .caso-item {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 12px 14px;
      border-radius: 10px;
      cursor: pointer;
      border: 1px solid rgba(255, 255, 255, 0.1);
      background: rgba(6, 11, 22, 0.65);
      transition: all 0.2s ease;
    }
    .caso-item:hover { border-color: rgba(16, 185, 129, 0.45); background: rgba(16, 185, 129, 0.06); }
    .caso-item.seleccionado { border-color: #10b981; background: rgba(16, 185, 129, 0.14); }
    .nota-txt { color: #34d399; }
    .success-box { background: rgba(16, 185, 129, 0.14); border: 1px solid rgba(16, 185, 129, 0.45); color: #a7f3d0; padding: 12px; border-radius: 8px; margin-bottom: 12px; }
  `],
})
export class SeguimientoComponent implements OnInit {
  private readonly identityService = inject(IdentityService);
  private readonly schedulingService = inject(SchedulingService);

  readonly columnasParticipaciones = ['estudiante', 'nota', 'estado', 'acciones'];
  readonly casos = signal<ResumenCaso[]>([]);
  readonly sesiones = signal<SesionResponse[]>([]);
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
    void this.cargarInicial();
  }

  async cargarInicial(): Promise<void> {
    this.cargandoCasos.set(true);
    try {
      const [casos, ses] = await Promise.all([
        firstValueFrom(this.identityService.casosSeguimiento()),
        firstValueFrom(this.schedulingService.sesiones()),
      ]);
      this.casos.set(casos);
      this.sesiones.set(ses);
      if (ses.length) {
        const fin = ses.find((s) => s.estado === 'FINALIZADO');
        this.reporteSesionId = fin ? fin.id : ses[0].id;
      }
      if (casos.length) {
        this.seleccionarCaso(casos[0]);
      }
    } catch (err) {
      this.error.set(mensajeError(err));
    } finally {
      this.cargandoCasos.set(false);
    }
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
