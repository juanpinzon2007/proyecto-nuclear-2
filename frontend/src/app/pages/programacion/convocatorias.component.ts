import { Component, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatTableModule } from '@angular/material/table';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { SchedulingService } from '../../core/scheduling.service';
import { ConvocatoriaDetalleResponse, ConvocatoriaResponse } from '../../core/api.models';
import { mensajeError } from '../../core/api-error';

@Component({
  selector: 'app-convocatorias',
  standalone: true,
  imports: [
    CommonModule,
    RouterLink,
    FormsModule,
    MatCardModule,
    MatButtonModule,
    MatIconModule,
    MatTableModule,
    MatFormFieldModule,
    MatInputModule,
    MatProgressSpinnerModule,
  ],
  template: `
    <div class="page">
      <div class="page-header">
        <div style="display: flex; align-items: center; gap: 8px;">
          <a mat-icon-button routerLink="/programacion" title="Volver a programación">
            <mat-icon>arrow_back</mat-icon>
          </a>
          <div>
            <h1>Convocatorias de la Sesión</h1>
            <p class="muted">Sesión ID: <span class="mono">{{ sesionId }}</span></p>
          </div>
        </div>
      </div>

      @if (error()) {
        <div class="error-box">{{ error() }}</div>
      }
      @if (mensajeExito()) {
        <div class="success-box">{{ mensajeExito() }}</div>
      }

      <!-- Tarjeta destacada cuando se genera un código nuevo -->
      @if (ultimoCodigoGenerado(); as cod) {
        <mat-card style="border-left: 4px solid #4caf50; margin-bottom: 20px;">
          <mat-card-header>
            <mat-card-title>¡Convocatoria Generada con Éxito!</mat-card-title>
          </mat-card-header>
          <mat-card-content style="padding-top: 12px;">
            <p>Comparte este código de acceso con el estudiante para que pueda ingresar al simulador:</p>
            <div style="display: flex; align-items: center; gap: 12px; margin-top: 8px;">
              <span class="mono" style="font-size: 20px; font-weight: 700; background: #e8f5e9; padding: 6px 16px; border-radius: 6px; letter-spacing: 1px;">
                {{ cod.codigo_acceso }}
              </span>
              <span class="muted mono" style="font-size: 12px;">ID Convocatoria: {{ cod.convocatoria_id }}</span>
            </div>
          </mat-card-content>
        </mat-card>
      }

      <!-- Formulario para agregar estudiante -->
      <mat-card style="margin-bottom: 24px;">
        <mat-card-header>
          <mat-card-title>Convocar Estudiante</mat-card-title>
        </mat-card-header>
        <mat-card-content style="padding-top: 16px;">
          <form (ngSubmit)="convocarEstudiante()" style="display: flex; gap: 12px; align-items: center; flex-wrap: wrap;">
            <mat-form-field appearance="outline" style="flex: 1; min-width: 300px;">
              <mat-label>UUID del Estudiante</mat-label>
              <input matInput [(ngModel)]="estudianteIdInput" name="estudianteIdInput" required placeholder="Ej: 550e8400-e29b-41d4-a716-446655440000" />
            </mat-form-field>
            <button mat-flat-button color="primary" type="submit" style="height: 56px;" [disabled]="guardando()">
              @if (guardando()) {
                <mat-spinner diameter="18"></mat-spinner>
              } @else {
                <span>Generar Convocatoria</span>
              }
            </button>
          </form>
        </mat-card-content>
      </mat-card>

      <!-- Tabla de convocatorias existentes -->
      @if (cargando()) {
        <div style="display: flex; justify-content: center; padding: 40px;">
          <mat-spinner diameter="40"></mat-spinner>
        </div>
      } @else if (convocatorias().length === 0) {
        <mat-card style="text-align: center; padding: 32px;">
          <mat-icon style="font-size: 48px; width: 48px; height: 48px; opacity: 0.5;">group_off</mat-icon>
          <h3>No hay estudiantes convocados en esta sesión</h3>
          <p class="muted">Ingresa el UUID del estudiante para generar su convocatoria y código individual.</p>
        </mat-card>
      } @else {
        <table mat-table [dataSource]="convocatorias()" class="mat-elevation-z1">
          <ng-container matColumnDef="estudiante">
            <th mat-header-cell *matHeaderCellDef>Estudiante (ID)</th>
            <td mat-cell *matCellDef="let c">
              <span class="mono">{{ c.estudiante_id }}</span>
            </td>
          </ng-container>

          <ng-container matColumnDef="convocatoria">
            <th mat-header-cell *matHeaderCellDef>Convocatoria ID</th>
            <td mat-cell *matCellDef="let c">
              <span class="mono muted" style="font-size: 11px;">{{ c.id }}</span>
            </td>
          </ng-container>

          <ng-container matColumnDef="estado">
            <th mat-header-cell *matHeaderCellDef>Estado</th>
            <td mat-cell *matCellDef="let c">
              <span class="chip" [class.ok]="c.estado === 'ACTIVA'" [class.bad]="c.estado === 'RETIRADA'">
                {{ c.estado }}
              </span>
            </td>
          </ng-container>

          <ng-container matColumnDef="acciones">
            <th mat-header-cell *matHeaderCellDef style="text-align: right;">Acciones</th>
            <td mat-cell *matCellDef="let c" style="text-align: right;">
              @if (c.estado !== 'RETIRADA') {
                <button mat-button color="warn" (click)="retirar(c.id)">
                  <mat-icon>person_remove</mat-icon> Retirar
                </button>
              }
            </td>
          </ng-container>

          <tr mat-header-row *matHeaderRowDef="columnas"></tr>
          <tr mat-row *matRowDef="let row; columns: columnas;"></tr>
        </table>
      }
    </div>
  `,
})
export class ConvocatoriasComponent implements OnInit {
  private readonly route = inject(ActivatedRoute);
  private readonly schedulingService = inject(SchedulingService);

  sesionId = '';
  readonly columnas = ['estudiante', 'convocatoria', 'estado', 'acciones'];
  readonly convocatorias = signal<ConvocatoriaDetalleResponse[]>([]);
  readonly cargando = signal<boolean>(true);
  readonly guardando = signal<boolean>(false);
  readonly error = signal<string | null>(null);
  readonly mensajeExito = signal<string | null>(null);

  estudianteIdInput = '';
  readonly ultimoCodigoGenerado = signal<ConvocatoriaResponse | null>(null);

  ngOnInit(): void {
    this.sesionId = this.route.snapshot.paramMap.get('id') ?? '';
    if (this.sesionId) {
      this.cargarConvocatorias();
    }
  }

  cargarConvocatorias(): void {
    this.cargando.set(true);
    this.error.set(null);
    this.schedulingService.convocatorias(this.sesionId).subscribe({
      next: (data) => {
        this.convocatorias.set(data);
        this.cargando.set(false);
      },
      error: (err) => {
        this.error.set(mensajeError(err));
        this.cargando.set(false);
      },
    });
  }

  convocarEstudiante(): void {
    if (!this.estudianteIdInput.trim()) return;
    this.guardando.set(true);
    this.error.set(null);
    this.mensajeExito.set(null);

    this.schedulingService.crearConvocatoria(this.sesionId, this.estudianteIdInput.trim()).subscribe({
      next: (res) => {
        this.ultimoCodigoGenerado.set(res);
        this.mensajeExito.set('Convocatoria creada y código de acceso emitido.');
        this.estudianteIdInput = '';
        this.guardando.set(false);
        this.cargarConvocatorias();
      },
      error: (err) => {
        this.error.set(mensajeError(err));
        this.guardando.set(false);
      },
    });
  }

  retirar(convocatoriaId: string): void {
    if (!confirm('¿Deseas retirar esta convocatoria? El estudiante ya no podrá ingresar a la sesión.')) return;
    this.error.set(null);
    this.schedulingService.retirarConvocatoria(this.sesionId, convocatoriaId).subscribe({
      next: () => {
        this.mensajeExito.set('Convocatoria retirada.');
        this.cargarConvocatorias();
      },
      error: (err) => this.error.set(mensajeError(err)),
    });
  }
}

