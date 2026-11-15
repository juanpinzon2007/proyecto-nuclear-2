import { Component, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatDividerModule } from '@angular/material/divider';
import { AuthService } from '../../core/auth.service';
import { SchedulingService } from '../../core/scheduling.service';
import { IdentityService } from '../../core/identity.service';
import { ParticipationService } from '../../core/participation.service';
import { ComprobanteAdmision, DocumentoRespuesta } from '../../core/api.models';
import { mensajeError } from '../../core/api-error';

@Component({
  selector: 'app-estudiante-portal',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatCardModule,
    MatButtonModule,
    MatIconModule,
    MatFormFieldModule,
    MatInputModule,
    MatProgressSpinnerModule,
    MatDividerModule,
  ],
  template: `
    <div class="page" style="max-width: 800px;">
      <div class="page-header">
        <div>
          <h1>Portal del Estudiante</h1>
          <p class="muted">Preparación, consentimiento informado e inicio de simulación</p>
        </div>
      </div>

      @if (error()) {
        <div class="error-box">{{ error() }}</div>
      }
      @if (mensajeExito()) {
        <div class="success-box">{{ mensajeExito() }}</div>
      }

      <!-- Reanudar intento previo si está en memoria -->
      @if (intentoRecordado(); as idInt) {
        <mat-card style="border-left: 4px solid var(--mat-sys-primary); margin-bottom: 24px;">
          <mat-card-header>
            <mat-card-title>Tienes un intento en curso</mat-card-title>
          </mat-card-header>
          <mat-card-content style="padding-top: 12px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px;">
            <p style="margin: 0;">Intento activo #{{ idInt }}. Puedes continuar tu simulación directamente.</p>
            <button mat-flat-button color="primary" (click)="irAlSimulador(idInt)">
              <mat-icon>play_circle</mat-icon> Continuar Simulación
            </button>
          </mat-card-content>
        </mat-card>
      }

      <!-- Datos de la Convocatoria Actual -->
      <mat-card style="margin-bottom: 24px;">
        <mat-card-header>
          <mat-card-title>Datos de tu Convocatoria</mat-card-title>
        </mat-card-header>
        <mat-card-content style="padding-top: 16px;">
          <div class="stack">
            <div class="row">
              <mat-form-field appearance="outline">
                <mat-label>UUID de la Convocatoria</mat-label>
                <input matInput [(ngModel)]="convocatoriaId" name="convocatoriaId" placeholder="UUID de tu convocatoria" />
              </mat-form-field>

              <mat-form-field appearance="outline" style="max-width: 200px;">
                <mat-label>ID Asignación</mat-label>
                <input matInput type="number" [(ngModel)]="idAsignacion" name="idAsignacion" placeholder="1" />
              </mat-form-field>
            </div>

            <div style="display: flex; gap: 8px;">
              <button mat-stroked-button color="primary" (click)="verificarAdmision()" [disabled]="cargando()">
                Verificar Admisión a la Sesión
              </button>
              <button mat-stroked-button color="accent" (click)="cargarConsentimiento()" [disabled]="cargando()">
                Cargar Consentimiento Informado
              </button>
            </div>
          </div>
        </mat-card-content>
      </mat-card>

      <!-- Estado de Admisión y Sala de Espera -->
      @if (admision(); as adm) {
        <mat-card style="margin-bottom: 24px;">
          <mat-card-header>
            <mat-card-title>Comprobante de Admisión</mat-card-title>
            <mat-card-subtitle>
              Estado de la Sesión: <span class="chip">{{ adm.estado_sesion }}</span>
            </mat-card-subtitle>
          </mat-card-header>
          <mat-card-content style="padding-top: 16px;">
            <div class="stack">
              <div>
                <strong>Admisión concedida:</strong>
                <span class="chip" [class.ok]="adm.admitida" [class.warn]="!adm.admitida">
                  {{ adm.admitida ? 'ADMITIDO' : 'EN ESPERA' }}
                </span>
              </div>

              @if (!adm.admitida) {
                <div class="info-box">
                  <p>Aún no has ingresado a la lista de espera de esta sesión. Ingresa tu código de acceso para registrar tu turno:</p>
                  <div style="display: flex; gap: 8px; margin-top: 8px;">
                    <mat-form-field appearance="outline" style="flex: 1;">
                      <mat-label>Código de Acceso</mat-label>
                      <input matInput type="password" [(ngModel)]="codigoAcceso" name="codigoAcceso" />
                    </mat-form-field>
                    <button mat-flat-button color="primary" style="height: 56px;" (click)="solicitarEspera()" [disabled]="cargando()">
                      Registrar Espera
                    </button>
                  </div>
                </div>
              }
            </div>
          </mat-card-content>
        </mat-card>
      }

      <!-- Consentimiento Informado -->
      @if (documentoConsentimiento(); as doc) {
        <mat-card style="margin-bottom: 24px; border-left: 4px solid var(--mat-sys-tertiary);">
          <mat-card-header>
            <mat-card-title>Consentimiento Informado Institucional</mat-card-title>
            <mat-card-subtitle>Versión {{ doc.version }} · Ref: {{ doc.referencia }}</mat-card-subtitle>
          </mat-card-header>
          <mat-card-content style="padding-top: 16px;">
            <div style="background: var(--mat-sys-surface-container-low); padding: 16px; border-radius: 8px; max-height: 200px; overflow-y: auto; font-size: 13px; line-height: 1.6; margin-bottom: 16px;">
              {{ doc.texto }}
            </div>

            @if (consentimientoAceptado()) {
              <div class="chip ok" style="padding: 6px 12px; font-size: 13px;">
                <mat-icon style="font-size: 16px; vertical-align: middle;">check_circle</mat-icon>
                Consentimiento aceptado correctamente (ID: {{ idConsentimiento() }})
              </div>
            } @else {
              <button mat-flat-button color="primary" (click)="aceptarConsentimiento(doc)" [disabled]="cargando()">
                Acepto los términos del Consentimiento Informado
              </button>
            }
          </mat-card-content>
        </mat-card>
      }

      <!-- Botón de Inicio de Intento -->
      <mat-card>
        <mat-card-header>
          <mat-card-title>Iniciar Simulación</mat-card-title>
        </mat-card-header>
        <mat-card-content style="padding-top: 16px;">
          <p class="muted">
            Una vez cumplidos los requisitos de admisión y consentimiento, puedes comenzar tu intento formal de simulación.
          </p>
          <div class="row" style="margin-top: 12px;">
            <mat-form-field appearance="outline">
              <mat-label>Código de Acceso Individual</mat-label>
              <input matInput type="password" [(ngModel)]="codigoAcceso" name="codigoAcceso" placeholder="Código recibido" required />
            </mat-form-field>

            <div style="display: flex; align-items: center;">
              <button mat-flat-button color="primary" style="height: 56px; font-size: 16px;" (click)="iniciarSimulacion()" [disabled]="cargando()">
                @if (cargando()) {
                  <mat-spinner diameter="20"></mat-spinner>
                } @else {
                  <span>Comenzar Intento</span>
                }
              </button>
            </div>
          </div>
        </mat-card-content>
      </mat-card>
    </div>
  `,
})
export class EstudiantePortalComponent implements OnInit {
  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);
  private readonly schedulingService = inject(SchedulingService);
  private readonly identityService = inject(IdentityService);
  private readonly participationService = inject(ParticipationService);

  convocatoriaId = '';
  idAsignacion = 1;
  codigoAcceso = '';

  readonly admision = signal<ComprobanteAdmision | null>(null);
  readonly documentoConsentimiento = signal<DocumentoRespuesta | null>(null);
  readonly consentimientoAceptado = signal<boolean>(false);
  readonly idConsentimiento = signal<number | null>(null);
  readonly intentoRecordado = signal<number | null>(null);

  readonly cargando = signal<boolean>(false);
  readonly error = signal<string | null>(null);
  readonly mensajeExito = signal<string | null>(null);

  ngOnInit(): void {
    const cid = this.auth.convocatoriaId();
    if (cid) {
      this.convocatoriaId = cid;
    }
    const rec = this.participationService.intentoRecordado();
    if (rec) {
      this.intentoRecordado.set(rec);
    }
  }

  verificarAdmision(): void {
    if (!this.convocatoriaId) return;
    this.cargando.set(true);
    this.error.set(null);

    this.schedulingService.admision(this.convocatoriaId).subscribe({
      next: (res) => {
        this.admision.set(res);
        this.cargando.set(false);
      },
      error: (err) => {
        this.error.set(mensajeError(err));
        this.cargando.set(false);
      },
    });
  }

  solicitarEspera(): void {
    if (!this.convocatoriaId || !this.codigoAcceso) return;
    this.cargando.set(true);
    this.error.set(null);

    this.schedulingService.solicitarEspera(this.convocatoriaId, this.codigoAcceso).subscribe({
      next: (res) => {
        this.admision.set(res);
        this.mensajeExito.set('Registro en espera exitoso.');
        this.cargando.set(false);
      },
      error: (err) => {
        this.error.set(mensajeError(err));
        this.cargando.set(false);
      },
    });
  }

  cargarConsentimiento(): void {
    if (!this.convocatoriaId) return;
    this.cargando.set(true);
    this.error.set(null);

    this.identityService.documentoConsentimiento(this.convocatoriaId, this.idAsignacion).subscribe({
      next: (doc) => {
        this.documentoConsentimiento.set(doc);
        this.cargando.set(false);
      },
      error: (err) => {
        this.error.set(mensajeError(err));
        this.cargando.set(false);
      },
    });
  }

  aceptarConsentimiento(doc: DocumentoRespuesta): void {
    this.cargando.set(true);
    this.error.set(null);

    this.identityService.aceptarConsentimiento(this.convocatoriaId, this.idAsignacion, {
      id_version_documento: doc.id_version_documento,
      referencia: doc.referencia,
      huella: doc.huella,
      acepta: true,
    }).subscribe({
      next: (res) => {
        this.consentimientoAceptado.set(true);
        this.idConsentimiento.set(res.id_consentimiento);
        this.mensajeExito.set('Consentimiento firmado y registrado.');
        this.cargando.set(false);
      },
      error: (err) => {
        this.error.set(mensajeError(err));
        this.cargando.set(false);
      },
    });
  }

  iniciarSimulacion(): void {
    if (!this.convocatoriaId || !this.codigoAcceso) {
      this.error.set('Por favor ingresa la convocatoria y el código de acceso.');
      return;
    }
    this.cargando.set(true);
    this.error.set(null);

    this.participationService.iniciar(this.convocatoriaId, {
      id_asignacion: this.idAsignacion,
      codigo_acceso: this.codigoAcceso,
      id_consentimiento: this.idConsentimiento() ?? 1,
    }).subscribe({
      next: (intento) => {
        this.cargando.set(false);
        this.participationService.recordarIntento(intento.id_intento);
        this.irAlSimulador(intento.id_intento);
      },
      error: (err) => {
        this.error.set(mensajeError(err));
        this.cargando.set(false);
      },
    });
  }

  irAlSimulador(id: number): void {
    void this.router.navigate(['/estudiante/simulador', id]);
  }
}

