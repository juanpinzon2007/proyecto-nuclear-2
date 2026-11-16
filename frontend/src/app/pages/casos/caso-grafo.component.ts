import { Component, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { firstValueFrom } from 'rxjs';
import { AuthService } from '../../core/auth.service';
import { CasesService } from '../../core/cases.service';
import { GrafoResponse, TransicionSolicitud } from '../../core/api.models';
import { mensajeError } from '../../core/api-error';

@Component({
  selector: 'app-caso-grafo',
  standalone: true,
  imports: [
    CommonModule,
    RouterLink,
    FormsModule,
    MatCardModule,
    MatButtonModule,
    MatIconModule,
    MatProgressSpinnerModule,
  ],
  template: `
    <div class="page">
      <div class="page-header">
        <div style="display: flex; align-items: center; gap: 8px;">
          <a mat-icon-button [routerLink]="['/casos', versionId]" title="Volver al caso">
            <mat-icon>arrow_back</mat-icon>
          </a>
          <div>
            <h1>Grafo de Navegación del Caso</h1>
            <p class="muted">Configuración de escena inicial y transiciones ramificadas entre escenas</p>
          </div>
        </div>
        @if (editable()) {
          <div style="display:flex; gap:10px; flex-wrap:wrap;">
            <button mat-stroked-button type="button" (click)="autoconfigurarLineal()" [disabled]="guardando()">
              <mat-icon>auto_fix_high</mat-icon> Autoconfigurar Lineal
            </button>
            <button mat-flat-button color="primary" type="button" (click)="guardarGrafo()" [disabled]="guardando()">
              <mat-icon>save</mat-icon> Guardar Recorrido
            </button>
          </div>
        }
      </div>

      @if (error()) { <div class="error-box">{{ error() }}</div> }
      @if (exito()) { <div class="success-box">{{ exito() }}</div> }

      @if (cargando()) {
        <div style="display: flex; justify-content: center; padding: 40px;">
          <mat-spinner diameter="40"></mat-spinner>
        </div>
      } @else if (grafo(); as g) {
        @if (g.escenas.length === 0) {
          <mat-card style="text-align: center; padding: 32px;">
            <p class="muted">No hay escenas en esta versión. Agrégalas en el editor del caso.</p>
          </mat-card>
        } @else {
          <div class="stack">
            @for (esc of g.escenas; track esc.id; let ei = $index) {
              <mat-card class="escena-card" [class.inicial]="escenarioInicialId === esc.id">
                <mat-card-header>
                  <mat-card-title style="display: flex; align-items: center; gap: 10px; width:100%;">
                    @if (editable()) {
                      <label style="display:flex; align-items:center; gap:6px; cursor:pointer; font-size:13px;">
                        <input type="radio" name="esc_inicial" [value]="esc.id" [(ngModel)]="escenarioInicialId" />
                        <span>{{ escenarioInicialId === esc.id ? 'ESCENA INICIAL' : 'Marcar inicial' }}</span>
                      </label>
                    } @else {
                      <span class="chip" [class.ok]="esc.inicial">{{ esc.inicial ? 'ESCENA INICIAL' : 'ESCENA' }}</span>
                    }
                    <span>Escenario #{{ ei + 1 }}</span>
                    <span class="mono" style="font-size: 11px; color:#94a3b8;">{{ esc.id }}</span>
                  </mat-card-title>
                </mat-card-header>
                <mat-card-content style="padding-top: 12px;">
                  <p><strong>Contexto:</strong> {{ esc.contexto }}</p>

                  <div style="margin-top: 12px;">
                    <strong>Preguntas y Transiciones de Opción:</strong>
                    <div class="stack" style="margin-top: 8px;">
                      @for (p of esc.preguntas; track p.id) {
                        <div class="pregunta-grafo-box">
                          <div style="font-weight: 500; margin-bottom:8px;">{{ p.enunciado }}</div>
                          <div class="stack" style="gap: 8px;">
                            @for (op of p.opciones; track op.opcion_id) {
                              <div class="transicion-item">
                                <span style="flex: 1;">{{ op.texto }}</span>
                                <mat-icon style="font-size: 18px; width: 18px; height: 18px; color: #94a3b8;">arrow_forward</mat-icon>
                                @if (editable() && transicionesEdit[op.opcion_id]) {
                                  <select class="dark-sel" [(ngModel)]="transicionesEdit[op.opcion_id].tipo" [name]="'t_' + op.opcion_id">
                                    <option value="ESCENA">Ir a ESCENA</option>
                                    <option value="FIN">FIN del caso</option>
                                  </select>
                                  @if (transicionesEdit[op.opcion_id].tipo === 'ESCENA') {
                                    <select class="dark-sel" [(ngModel)]="transicionesEdit[op.opcion_id].destino_id" [name]="'d_' + op.opcion_id">
                                      <option [ngValue]="null">Seleccionar escena destino...</option>
                                      @for (cand of g.escenas; track cand.id; let ci = $index) {
                                        @if (cand.id !== esc.id) {
                                          <option [ngValue]="cand.id">Escenario #{{ ci + 1 }} ({{ cand.contexto | slice:0:35 }})</option>
                                        }
                                      }
                                    </select>
                                  }
                                } @else {
                                  <span class="chip" [class.ok]="op.tipo === 'ESCENA'" [class.bad]="op.tipo === 'FIN'">
                                    {{ op.tipo || 'SIN TRANSICIÓN' }}
                                  </span>
                                  @if (op.destino_id) {
                                    <span class="mono" style="font-size: 11px;">Destino: {{ op.destino_id }}</span>
                                  }
                                }
                              </div>
                            }
                          </div>
                        </div>
                      }
                    </div>
                  </div>
                </mat-card-content>
              </mat-card>
            }
          </div>
        }
      }
    </div>
  `,
  styles: [`
    .escena-card { border-left: 4px solid rgba(255,255,255,0.2); margin-bottom: 12px; }
    .escena-card.inicial { border-left: 4px solid #10b981; }
    .pregunta-grafo-box { background: rgba(6, 11, 22, 0.65); padding: 12px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.08); }
    .transicion-item { display: flex; align-items: center; gap: 10px; background: rgba(15, 23, 42, 0.8); padding: 8px 12px; border-radius: 6px; border: 1px solid rgba(255,255,255,0.1); flex-wrap: wrap; }
    .dark-sel { background: #0f172a; color: #f8fafc; border: 1px solid rgba(255,255,255,0.2); border-radius: 6px; padding: 6px 8px; font-size: 12px; }
    .success-box { background: rgba(16,185,129,0.15); border: 1px solid rgba(16,185,129,0.45); color: #a7f3d0; padding: 10px 14px; border-radius: 8px; margin-bottom: 12px; }
  `],
})
export class CasoGrafoComponent implements OnInit {
  private readonly route = inject(ActivatedRoute);
  private readonly casesService = inject(CasesService);
  private readonly auth = inject(AuthService);

  versionId = '';
  readonly grafo = signal<GrafoResponse | null>(null);
  readonly cargando = signal(true);
  readonly guardando = signal(false);
  readonly editable = signal(false);
  readonly error = signal<string | null>(null);
  readonly exito = signal<string | null>(null);

  escenarioInicialId = '';
  transicionesEdit: Record<string, { tipo: 'ESCENA' | 'FIN'; destino_id: string | null }> = {};

  ngOnInit(): void {
    this.versionId = this.route.snapshot.paramMap.get('id') ?? '';
    if (this.versionId) void this.cargarGrafo();
  }

  async cargarGrafo(): Promise<void> {
    this.cargando.set(true);
    this.error.set(null);
    try {
      const [g, detalle] = await Promise.all([
        firstValueFrom(this.casesService.grafo(this.versionId)),
        firstValueFrom(this.casesService.obtener(this.versionId)),
      ]);
      this.grafo.set(g);
      this.editable.set(detalle.estado === 'BORRADOR' && this.auth.tienePermiso('CREAR_CASOS'));

      const inicial = g.escenas.find((e) => e.inicial) ?? g.escenas[0];
      this.escenarioInicialId = inicial ? inicial.id : '';
      this.transicionesEdit = {};
      g.escenas.forEach((esc, ei) => {
        const sig = g.escenas[ei + 1];
        for (const p of esc.preguntas) {
          for (const op of p.opciones) {
            this.transicionesEdit[op.opcion_id] = {
              tipo: op.tipo === 'FIN' || (!op.tipo && !sig) ? 'FIN' : 'ESCENA',
              destino_id: op.destino_id ?? (sig ? sig.id : null),
            };
          }
        }
      });
    } catch (err) {
      this.error.set(mensajeError(err));
    } finally {
      this.cargando.set(false);
    }
  }

  autoconfigurarLineal(): void {
    const g = this.grafo();
    if (!g || !g.escenas.length) return;
    this.escenarioInicialId = g.escenas[0].id;
    g.escenas.forEach((esc, ei) => {
      const sig = g.escenas[ei + 1];
      for (const p of esc.preguntas) {
        for (const op of p.opciones) {
          this.transicionesEdit[op.opcion_id] = sig
            ? { tipo: 'ESCENA', destino_id: sig.id }
            : { tipo: 'FIN', destino_id: null };
        }
      }
    });
    void this.guardarGrafo();
  }

  async guardarGrafo(): Promise<void> {
    const g = this.grafo();
    if (!g || !this.escenarioInicialId) return;
    this.guardando.set(true);
    this.error.set(null);
    this.exito.set(null);
    try {
      const transiciones: TransicionSolicitud[] = [];
      for (const esc of g.escenas) {
        for (const p of esc.preguntas) {
          for (const op of p.opciones) {
            const cfg = this.transicionesEdit[op.opcion_id];
            transiciones.push({
              opcion_id: op.opcion_id,
              tipo: cfg.tipo,
              destino_id: cfg.tipo === 'ESCENA' ? cfg.destino_id : null,
            });
          }
        }
      }
      const actualizado = await firstValueFrom(
        this.casesService.guardarGrafo(this.versionId, {
          escenario_inicial_id: this.escenarioInicialId,
          transiciones,
        }),
      );
      this.grafo.set(actualizado);
      this.exito.set('Grafo de transiciones guardado y validado correctamente.');
    } catch (err) {
      this.error.set(mensajeError(err));
    } finally {
      this.guardando.set(false);
    }
  }
}
