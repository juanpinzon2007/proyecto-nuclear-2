import { CommonModule } from '@angular/common';
import { Component, OnInit, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatSelectModule } from '@angular/material/select';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatTableModule } from '@angular/material/table';
import { firstValueFrom } from 'rxjs';
import { mensajeError } from '../../core/api-error';
import { ConvocatoriaDetalleResponse, EstudianteDisponibleItem } from '../../core/api.models';
import { SchedulingService } from '../../core/scheduling.service';
import { avatarUsuario } from '../../core/user-avatar';

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
    MatSnackBarModule,
  ],
  template: `
    <div class="conv-wrap">
      <div class="page-header">
        <div style="display:flex; align-items:center; gap:10px;">
          <a mat-icon-button routerLink="/programacion"><mat-icon>arrow_back</mat-icon></a>
          <div>
            <p class="eyebrow">Control de Acceso</p>
            <h2>Convocatorias & Códigos de Autorización</h2>
            <p class="subtitle">Sesión <span class="mono">{{ sesionId }}</span></p>
          </div>
        </div>
      </div>

      @if (ultimoCodigo(); as code) {
        <div class="code-box">
          <div>
            <div class="mono green" style="font-weight:700;">CÓDIGO DE AUTORIZACIÓN INDIVIDUAL EMITIDO</div>
            <div class="subtitle">Entrégalo únicamente a {{ code.nombre }}. Con este código inicia sesión en el Portal Estudiantil.</div>
          </div>
          <div class="mono code-val">{{ code.codigo }}</div>
        </div>
      }

      <div class="grid-2">
        <mat-card class="panel panel-cyan-left">
          <mat-card-header>
            <mat-card-title>Emitir / Renovar Convocatoria</mat-card-title>
            <mat-card-subtitle>Selecciona el estudiante por nombre y correo</mat-card-subtitle>
          </mat-card-header>
          <mat-card-content style="padding-top:16px;">
            <form (ngSubmit)="convocar()" class="stack-form">
              <mat-form-field appearance="outline">
                <mat-label>Estudiante registrado</mat-label>
                <mat-select [(ngModel)]="estudianteSeleccionadoUuid" name="estUuid" required>
                  @for (e of estudiantesConUuid(); track e.id_usuario) {
                    <mat-option [value]="e.uuid_scheduling">{{ e.nombre }} — {{ e.correo }}</mat-option>
                  }
                </mat-select>
              </mat-form-field>
              <button mat-flat-button color="primary" type="submit" [disabled]="!estudianteSeleccionadoUuid || cargando()">
                <mat-icon>vpn_key</mat-icon> Generar código y convocar
              </button>
            </form>
          </mat-card-content>
        </mat-card>

        <mat-card class="panel">
          <mat-card-header>
            <mat-card-title>Estudiantes Convocados ({{ convocatorias().length }})</mat-card-title>
          </mat-card-header>
          <mat-card-content style="padding-top:12px;">
            <table mat-table [dataSource]="convocatorias()" style="width:100%;">
              <ng-container matColumnDef="estudiante">
                <th mat-header-cell *matHeaderCellDef>Estudiante</th>
                <td mat-cell *matCellDef="let c">
                  <div class="user-inline">
                    <img class="game-avatar" [src]="avatarEstudiante(c.estudiante_id)" [alt]="nombreEstudiante(c.estudiante_id)" />
                    <div>
                      <div style="font-weight:600;">{{ nombreEstudiante(c.estudiante_id) }}</div>
                      <div class="mono muted">{{ c.id }}</div>
                    </div>
                  </div>
                </td>
              </ng-container>
              <ng-container matColumnDef="estado">
                <th mat-header-cell *matHeaderCellDef>Estado</th>
                <td mat-cell *matCellDef="let c">
                  <span class="chip" [class.ok]="c.estado === 'ACTIVA'" [class.bad]="c.estado !== 'ACTIVA'">{{ c.estado }}</span>
                </td>
              </ng-container>
              <ng-container matColumnDef="acciones">
                <th mat-header-cell *matHeaderCellDef>Acciones</th>
                <td mat-cell *matCellDef="let c">
                  @if (c.estado === 'ACTIVA') {
                    <button mat-button color="warn" type="button" (click)="retirar(c.id)">Retirar</button>
                  }
                </td>
              </ng-container>
              <tr mat-header-row *matHeaderRowDef="['estudiante', 'estado', 'acciones']"></tr>
              <tr mat-row *matRowDef="let row; columns: ['estudiante', 'estado', 'acciones']"></tr>
            </table>
          </mat-card-content>
        </mat-card>
      </div>
    </div>
  `,
  styles: [`
    .conv-wrap { padding: 4px 0 36px; max-width: 1160px; margin: 0 auto; }
    .subtitle { margin: 4px 0 0; color: var(--muted); font-size: 13px; }
    .grid-2 { display: grid; grid-template-columns: 360px 1fr; gap: 20px; align-items: start; }
    @media (max-width: 950px) { .grid-2 { grid-template-columns: 1fr; } }
    .stack-form { display: flex; flex-direction: column; gap: 12px; }
    .code-box {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 12px;
      padding: 16px 20px;
      background: rgba(0, 232, 148, 0.08);
      border: 1px solid rgba(0, 232, 148, 0.55);
      border-left: 4px solid var(--green);
      margin-bottom: 18px;
      flex-wrap: wrap;
    }
    .code-val {
      font-size: 24px !important;
      font-weight: 800;
      color: var(--amber) !important;
      letter-spacing: 2px;
      padding: 6px 14px;
      background: #070a10;
      border: 1px solid rgba(255, 184, 0, 0.55);
    }
  `],
})
export class ConvocatoriasComponent implements OnInit {
  private readonly route = inject(ActivatedRoute);
  private readonly scheduling = inject(SchedulingService);
  private readonly snack = inject(MatSnackBar);

  sesionId = '';
  readonly cargando = signal(false);
  readonly convocatorias = signal<ConvocatoriaDetalleResponse[]>([]);
  readonly estudiantes = signal<EstudianteDisponibleItem[]>([]);
  readonly ultimoCodigo = signal<{ nombre: string; codigo: string } | null>(null);
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
      const [convs, ests] = await Promise.all([
        firstValueFrom(this.scheduling.convocatorias(this.sesionId)),
        firstValueFrom(this.scheduling.estudiantes()),
      ]);
      this.convocatorias.set(convs);
      this.estudiantes.set(ests);
    } catch (e) {
      this.snack.open(mensajeError(e), 'Cerrar', { duration: 4000 });
    } finally {
      this.cargando.set(false);
    }
  }

  async convocar(): Promise<void> {
    if (!this.estudianteSeleccionadoUuid) return;
    this.cargando.set(true);
    try {
      const res = await firstValueFrom(this.scheduling.crearConvocatoria(this.sesionId, this.estudianteSeleccionadoUuid));
      this.ultimoCodigo.set({
        nombre: this.nombreEstudiante(this.estudianteSeleccionadoUuid),
        codigo: res.codigo_acceso,
      });
      this.snack.open('Convocatoria generada y notificada al estudiante.', 'OK', { duration: 3000 });
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
    const e = this.estudiantes().find((x) => x.uuid_scheduling === uuid);
    return e ? `${e.nombre} (${e.correo})` : uuid;
  }

  avatarEstudiante(uuid: string): string {
    const e = this.estudiantes().find((x) => x.uuid_scheduling === uuid);
    return avatarUsuario({
      id_usuario: e?.id_usuario,
      nombre: e?.nombre,
      correo: e?.correo,
      rol: 'ESTUDIANTE',
    });
  }
}
