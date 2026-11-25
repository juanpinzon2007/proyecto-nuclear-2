import { NgTemplateOutlet } from '@angular/common';
import { afterNextRender, Component, ElementRef, inject, Injector, signal, viewChild } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { Router } from '@angular/router';
import { mensajeError } from '../../core/api-error';
import { AuthService } from '../../core/auth.service';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [FormsModule, NgTemplateOutlet, MatIconModule, MatProgressSpinnerModule],
  templateUrl: './login.component.html',
  styleUrl: './login.component.scss',
})
export class LoginComponent {
  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);
  private readonly injector = inject(Injector);
  private readonly tituloAcceso = viewChild<ElementRef<HTMLHeadingElement>>('tituloAcceso');
  private readonly campoCredencial = viewChild<ElementRef<HTMLInputElement>>('campoCredencial');

  mostrarCredencial = false;
  readonly usandoConvocatoria = signal(false);
  mostrarNuevaClave = false;
  correo = '';
  credencial = '';
  codigoVerificacion = '';
  correoRecuperacion = '';
  codigoRecuperacion = '';
  nuevaClave = '';
  confirmarNuevaClave = '';
  errorLogin = signal<string | null>(null);
  infoVerificacion = signal<string | null>(null);
  cargando = signal<boolean>(false);
  verificacionPendiente = signal<{ correo: string; mensaje: string; expiraEnSegundos: number } | null>(null);
  recuperacionPaso = signal<'SOLICITAR' | 'CONFIRMAR' | null>(null);

  async iniciarSesion(): Promise<void> {
    this.errorLogin.set(null);
    this.infoVerificacion.set(null);
    this.cargando.set(true);
    try {
      const correo = this.correo.trim();
      const credencial = this.credencial.trim();
      const res = this.usandoConvocatoria()
        ? { estado: 'AUTENTICADO' as const, usuario: await this.auth.loginEstudiante(correo, credencial) }
        : await this.auth.loginUnificado(correo, credencial);
      if (res.estado === 'VERIFICACION_REQUERIDA') {
        this.codigoVerificacion = '';
        this.verificacionPendiente.set({
          correo: res.correo,
          mensaje: res.mensaje,
          expiraEnSegundos: res.expiraEnSegundos,
        });
        this.enfocarTitulo();
        return;
      }
      if (res.usuario) {
        this.credencial = '';
        this.codigoVerificacion = '';
        void this.router.navigateByUrl(this.auth.rutaInicio());
      } else {
        this.errorLogin.set('No se pudo obtener el perfil de usuario.');
      }
    } catch (err) {
      this.errorLogin.set(mensajeError(err));
    } finally {
      this.cargando.set(false);
    }
  }

  cambiarModoAcceso(): void {
    this.usandoConvocatoria.update((activo) => !activo);
    this.credencial = '';
    this.mostrarCredencial = false;
    this.errorLogin.set(null);
    this.infoVerificacion.set(null);
    afterNextRender(() => this.campoCredencial()?.nativeElement.focus(), { injector: this.injector });
  }

  async confirmarCodigoPrimerIngreso(): Promise<void> {
    const verif = this.verificacionPendiente();
    if (!verif) return;
    this.errorLogin.set(null);
    this.infoVerificacion.set(null);
    this.cargando.set(true);
    try {
      const u = await this.auth.verificarPrimerIngreso(verif.correo, this.codigoVerificacion.trim());
      if (u) {
        this.credencial = '';
        this.codigoVerificacion = '';
        this.verificacionPendiente.set(null);
        void this.router.navigateByUrl(this.auth.rutaInicio());
      } else {
        this.errorLogin.set('No se pudo obtener el perfil de usuario.');
      }
    } catch (err) {
      this.errorLogin.set(mensajeError(err));
    } finally {
      this.cargando.set(false);
    }
  }

  async reenviarCodigo(): Promise<void> {
    const verif = this.verificacionPendiente();
    if (!verif) return;
    this.errorLogin.set(null);
    this.infoVerificacion.set(null);
    this.cargando.set(true);
    try {
      const r = await this.auth.loginEstudiantePorClave(verif.correo, this.credencial.trim());
      if (r.requiere_verificacion) {
        this.infoVerificacion.set(r.mensaje ?? 'Revisa tu correo. Espera un minuto antes de pedir otro código.');
      } else if (r.access_token) {
        this.verificacionPendiente.set(null);
        await this.iniciarSesion();
      }
    } catch (err) {
      this.errorLogin.set(mensajeError(err));
    } finally {
      this.cargando.set(false);
    }
  }

  volverALogin(): void {
    this.verificacionPendiente.set(null);
    this.recuperacionPaso.set(null);
    this.codigoVerificacion = '';
    this.codigoRecuperacion = '';
    this.nuevaClave = '';
    this.confirmarNuevaClave = '';
    this.errorLogin.set(null);
    this.infoVerificacion.set(null);
    this.enfocarTitulo();
  }

  abrirRecuperacion(): void {
    this.errorLogin.set(null);
    this.infoVerificacion.set(null);
    this.verificacionPendiente.set(null);
    this.correoRecuperacion = this.correo.trim();
    this.codigoRecuperacion = '';
    this.nuevaClave = '';
    this.confirmarNuevaClave = '';
    this.recuperacionPaso.set('SOLICITAR');
    this.enfocarTitulo();
  }

  async enviarCodigoRecuperacion(): Promise<void> {
    const objetivo = this.correoRecuperacion.trim();
    if (!objetivo) return;
    this.errorLogin.set(null);
    this.infoVerificacion.set(null);
    this.cargando.set(true);
    try {
      const resp = await this.auth.solicitarRecuperacionContrasena(objetivo);
      this.recuperacionPaso.set('CONFIRMAR');
      this.infoVerificacion.set(resp.mensaje);
      this.enfocarTitulo();
    } catch (err) {
      this.errorLogin.set(mensajeError(err));
    } finally {
      this.cargando.set(false);
    }
  }

  async confirmarRecuperacionClave(): Promise<void> {
    if (this.nuevaClave !== this.confirmarNuevaClave) {
      this.errorLogin.set('Las contraseñas nuevas no coinciden.');
      return;
    }
    this.errorLogin.set(null);
    this.infoVerificacion.set(null);
    this.cargando.set(true);
    try {
      const resp = await this.auth.confirmarRecuperacionContrasena(
        this.correoRecuperacion.trim(),
        this.codigoRecuperacion.trim(),
        this.nuevaClave,
      );
      this.correo = this.correoRecuperacion.trim();
      this.credencial = '';
      this.recuperacionPaso.set(null);
      this.codigoRecuperacion = '';
      this.nuevaClave = '';
      this.confirmarNuevaClave = '';
      this.infoVerificacion.set(resp.mensaje);
      this.enfocarTitulo();
    } catch (err) {
      this.errorLogin.set(mensajeError(err));
    } finally {
      this.cargando.set(false);
    }
  }

  private enfocarTitulo(): void {
    afterNextRender(() => this.tituloAcceso()?.nativeElement.focus(), { injector: this.injector });
  }
}

