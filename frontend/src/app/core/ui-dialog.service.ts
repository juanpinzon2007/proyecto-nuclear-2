import { CommonModule } from '@angular/common';
import { Component, Injectable, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MAT_DIALOG_DATA, MatDialog, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { firstValueFrom } from 'rxjs';

export type NeuroDialogTono = 'cyan' | 'green' | 'amber' | 'warn';

export interface NeuroDialogData {
  modo: 'confirm' | 'prompt';
  tono: NeuroDialogTono;
  eyebrow: string;
  titulo: string;
  mensaje: string;
  etiquetaCampo?: string;
  placeholder?: string;
  botonConfirmar: string;
  botonCancelar: string;
}

@Component({
  selector: 'app-neuro-dialog',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatDialogModule,
    MatButtonModule,
    MatIconModule,
    MatFormFieldModule,
    MatInputModule,
  ],
  template: `
    <div class="nd-shell" [ngClass]="'tone-' + data.tono">
      <div class="nd-head">
        <div class="nd-ico">
          <mat-icon>{{ iconoPorTono() }}</mat-icon>
        </div>
        <div class="nd-head-copy">
          <p class="nd-eyebrow">{{ data.eyebrow }}</p>
          <h2 class="nd-title">{{ data.titulo }}</h2>
        </div>
      </div>

      <p class="nd-msg">{{ data.mensaje }}</p>

      @if (data.modo === 'prompt') {
        <mat-form-field appearance="outline" class="nd-field">
          <mat-label>{{ data.etiquetaCampo || 'Motivo o detalle' }}</mat-label>
          <textarea
            matInput
            rows="3"
            [(ngModel)]="texto"
            name="ndTexto"
            [placeholder]="data.placeholder || 'Escribe aquí...'"
            (keydown.control.enter)="aceptar()"
          ></textarea>
        </mat-form-field>
        @if (errorRequerido) {
          <div class="nd-err">Debes ingresar un texto antes de confirmar.</div>
        }
      }

      <div class="nd-actions">
        <button mat-stroked-button type="button" (click)="cancelar()">
          {{ data.botonCancelar }}
        </button>
        <button
          mat-flat-button
          [color]="data.tono === 'warn' ? 'warn' : 'primary'"
          type="button"
          (click)="aceptar()"
        >
          <mat-icon>{{ data.tono === 'warn' ? 'warning_amber' : 'check_circle' }}</mat-icon>
          {{ data.botonConfirmar }}
        </button>
      </div>
    </div>
  `,
  styles: [`
    .nd-shell {
      padding: 22px 24px 20px;
      background: linear-gradient(160deg, rgba(16, 22, 31, 0.99), rgba(8, 12, 18, 0.99));
      border: 1px solid var(--line-strong);
      border-left: 4px solid var(--cyan);
      color: var(--text);
      display: grid;
      gap: 14px;
      min-width: min(86vw, 440px);
      max-width: 92vw;
      box-sizing: border-box;
    }
    @media (max-width: 480px) {
      .nd-shell { min-width: 0; width: 100%; padding: 18px 16px; }
      .nd-title { font-size: 22px; }
    }
    .nd-shell.tone-green { border-left-color: var(--green); }
    .nd-shell.tone-amber { border-left-color: var(--amber); }
    .nd-shell.tone-warn { border-left-color: var(--red); border-color: rgba(232, 67, 81, 0.45); }

    .nd-head {
      display: flex;
      align-items: center;
      gap: 14px;
    }
    .nd-ico {
      width: 44px;
      height: 44px;
      flex: 0 0 auto;
      display: grid;
      place-items: center;
      border: 1px solid rgba(0, 229, 244, 0.42);
      background: rgba(0, 229, 244, 0.1);
      color: var(--cyan);
    }
    .tone-green .nd-ico {
      border-color: rgba(0, 232, 148, 0.45);
      background: rgba(0, 232, 148, 0.1);
      color: var(--green);
    }
    .tone-amber .nd-ico {
      border-color: rgba(255, 184, 0, 0.5);
      background: rgba(255, 184, 0, 0.1);
      color: var(--amber);
    }
    .tone-warn .nd-ico {
      border-color: rgba(232, 67, 81, 0.5);
      background: rgba(232, 67, 81, 0.12);
      color: var(--coral);
    }
    .nd-head-copy { min-width: 0; }
    .nd-eyebrow {
      margin: 0 0 3px;
      font-family: var(--mono);
      font-size: 11px;
      letter-spacing: 1.5px;
      text-transform: uppercase;
      color: var(--cyan);
    }
    .tone-green .nd-eyebrow { color: var(--green); }
    .tone-amber .nd-eyebrow { color: var(--amber); }
    .tone-warn .nd-eyebrow { color: var(--coral); }

    .nd-title {
      margin: 0;
      font-family: var(--display);
      font-size: 26px;
      line-height: 1.05;
      text-transform: uppercase;
      color: var(--text);
    }
    .nd-msg {
      margin: 0;
      font-size: 14px;
      line-height: 1.55;
      color: var(--muted);
    }
    .nd-field { width: 100%; }
    .nd-err {
      margin-top: -8px;
      color: var(--coral);
      font-family: var(--mono);
      font-size: 12px;
    }
    .nd-actions {
      display: flex;
      justify-content: flex-end;
      gap: 10px;
      flex-wrap: wrap;
      padding-top: 6px;
      border-top: 1px dashed rgba(184, 211, 214, 0.18);
    }
  `],
})
export class NeuroDialogComponent {
  readonly data = inject<NeuroDialogData>(MAT_DIALOG_DATA);
  private readonly ref = inject(MatDialogRef<NeuroDialogComponent>);

  texto = '';
  errorRequerido = false;

  iconoPorTono(): string {
    switch (this.data.tono) {
      case 'green':
        return 'task_alt';
      case 'amber':
        return 'help_outline';
      case 'warn':
        return 'warning_amber';
      default:
        return 'verified_user';
    }
  }

  cancelar(): void {
    this.ref.close(this.data.modo === 'confirm' ? false : null);
  }

  aceptar(): void {
    if (this.data.modo === 'prompt') {
      const limpio = this.texto.trim();
      if (!limpio) {
        this.errorRequerido = true;
        return;
      }
      this.ref.close(limpio);
      return;
    }
    this.ref.close(true);
  }
}

export interface ConfirmarOpciones {
  titulo: string;
  mensaje: string;
  eyebrow?: string;
  botonConfirmar?: string;
  botonCancelar?: string;
  tono?: NeuroDialogTono;
}

export interface SolicitarTextoOpciones {
  titulo: string;
  mensaje: string;
  eyebrow?: string;
  etiquetaCampo?: string;
  placeholder?: string;
  botonConfirmar?: string;
  botonCancelar?: string;
  tono?: NeuroDialogTono;
}

@Injectable({ providedIn: 'root' })
export class UiDialogService {
  private readonly dialog = inject(MatDialog);

  async confirmar(opts: ConfirmarOpciones): Promise<boolean> {
    const ref = this.dialog.open(NeuroDialogComponent, {
      panelClass: 'neuro-dialog-panel',
      backdropClass: 'neuro-backdrop',
      maxWidth: '520px',
      data: {
        modo: 'confirm',
        tono: opts.tono ?? 'cyan',
        eyebrow: opts.eyebrow ?? 'Protocolo de Confirmación',
        titulo: opts.titulo,
        mensaje: opts.mensaje,
        botonConfirmar: opts.botonConfirmar ?? 'Confirmar',
        botonCancelar: opts.botonCancelar ?? 'Cancelar',
      } satisfies NeuroDialogData,
    });
    const res = await firstValueFrom(ref.afterClosed());
    return res === true;
  }

  async solicitarTexto(opts: SolicitarTextoOpciones): Promise<string | null> {
    const ref = this.dialog.open(NeuroDialogComponent, {
      panelClass: 'neuro-dialog-panel',
      backdropClass: 'neuro-backdrop',
      maxWidth: '520px',
      data: {
        modo: 'prompt',
        tono: opts.tono ?? 'amber',
        eyebrow: opts.eyebrow ?? 'Registro Académico',
        titulo: opts.titulo,
        mensaje: opts.mensaje,
        etiquetaCampo: opts.etiquetaCampo ?? 'Motivo académico',
        placeholder: opts.placeholder ?? 'Describe brevemente el motivo...',
        botonConfirmar: opts.botonConfirmar ?? 'Registrar',
        botonCancelar: opts.botonCancelar ?? 'Cancelar',
      } satisfies NeuroDialogData,
    });
    const res = await firstValueFrom(ref.afterClosed());
    return typeof res === 'string' && res.trim() ? res.trim() : null;
  }
}
