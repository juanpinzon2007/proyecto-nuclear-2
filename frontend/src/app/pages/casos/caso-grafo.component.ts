import { Component, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { CasesService } from '../../core/cases.service';
import { GrafoResponse } from '../../core/api.models';
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
            <p class="muted">Estructura ramificada de transiciones entre escenas</p>
          </div>
        </div>
      </div>

      @if (error()) {
        <div class="error-box">{{ error() }}</div>
      }

      @if (cargando()) {
        <div style="display: flex; justify-content: center; padding: 40px;">
          <mat-spinner diameter="40"></mat-spinner>
        </div>
      } @else if (grafo(); as g) {
        @if (g.escenas.length === 0) {
          <mat-card style="text-align: center; padding: 32px;">
            <p class="muted">No hay escenas configuradas en el grafo para esta versión.</p>
          </mat-card>
        } @else {
          <div class="stack">
            @for (esc of g.escenas; track esc.id) {
              <mat-card class="escena-card" [class.inicial]="esc.inicial">
                <mat-card-header>
                  <mat-card-title style="display: flex; align-items: center; gap: 8px;">
                    @if (esc.inicial) {
                      <span class="chip ok">ESCENA INICIAL</span>
                    } @else {
                      <span class="chip">ESCENA</span>
                    }
                    <span class="mono" style="font-size: 13px;">{{ esc.id }}</span>
                  </mat-card-title>
                </mat-card-header>
                <mat-card-content style="padding-top: 12px;">
                  <p><strong>Contexto:</strong> {{ esc.contexto }}</p>

                  <div style="margin-top: 12px;">
                    <strong>Preguntas y Transiciones de Opción:</strong>
                    <div class="stack" style="margin-top: 8px;">
                      @for (p of esc.preguntas; track p.id) {
                        <div class="pregunta-grafo-box">
                          <div style="font-weight: 500;">{{ p.enunciado }}</div>
                          <div class="stack" style="margin-top: 6px;">
                            @for (op of p.opciones; track op.opcion_id) {
                              <div class="transicion-item">
                                <span style="flex: 1;">{{ op.texto }}</span>
                                <mat-icon style="font-size: 18px; width: 18px; height: 18px; color: gray;">arrow_forward</mat-icon>
                                <span class="chip" [class.ok]="op.tipo === 'ESCENA'" [class.bad]="op.tipo === 'FIN'">
                                  {{ op.tipo || 'SIN TRANSICIÓN' }}
                                </span>
                                @if (op.destino_id) {
                                  <span class="mono" style="font-size: 11px;">Destino: {{ op.destino_id }}</span>
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
    .escena-card {
      border-left: 4px solid var(--mat-sys-outline);
    }
    .escena-card.inicial {
      border-left: 4px solid #4caf50;
    }
    .pregunta-grafo-box {
      background: var(--mat-sys-surface-container-low);
      padding: 10px;
      border-radius: 6px;
    }
    .transicion-item {
      display: flex;
      align-items: center;
      gap: 8px;
      background: white;
      padding: 6px 10px;
      border-radius: 4px;
      border: 1px solid var(--mat-sys-outline-variant);
    }
  `],
})
export class CasoGrafoComponent implements OnInit {
  private readonly route = inject(ActivatedRoute);
  private readonly casesService = inject(CasesService);

  versionId = '';
  readonly grafo = signal<GrafoResponse | null>(null);
  readonly cargando = signal<boolean>(true);
  readonly error = signal<string | null>(null);

  ngOnInit(): void {
    this.versionId = this.route.snapshot.paramMap.get('id') ?? '';
    if (this.versionId) {
      this.cargarGrafo();
    }
  }

  cargarGrafo(): void {
    this.cargando.set(true);
    this.error.set(null);
    this.casesService.grafo(this.versionId).subscribe({
      next: (data) => {
        this.grafo.set(data);
        this.cargando.set(false);
      },
      error: (err) => {
        this.error.set(mensajeError(err));
        this.cargando.set(false);
      },
    });
  }
}

