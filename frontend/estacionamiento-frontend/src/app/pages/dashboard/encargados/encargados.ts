import {
  ChangeDetectionStrategy,
  Component,
  OnInit,
  inject,
  signal,
} from '@angular/core';
import {
  AbstractControl,
  FormBuilder,
  FormGroup,
  FormControl,
  ReactiveFormsModule,
  ValidationErrors,
  Validators,
} from '@angular/forms';
import { DecimalPipe } from '@angular/common';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { firstValueFrom } from 'rxjs';
import { ConfigService } from '../../../services/config.service';
import { AlertService } from '../../../core/services/alert';

interface RolUsuario {
  admin: boolean;
  encargado: boolean;
}

interface Usuario {
  id: number;
  codigo: number;
  nombre: string | null;
  comision: number | null;
  rol: RolUsuario | string | null;
  observaciones: string | null;
  email: string | null;
}

interface UsuarioPayload {
  codigo: number;
  nombre: string;
  comision: number;
  rol: RolUsuario;
  observaciones: string;
  email: string;
  password: string;
}

interface UsuarioUpdatePayload {
  codigo: number;
  nombre: string;
  comision: number;
  rol: RolUsuario;
  observaciones: string;
  email: string;
  password: string;
}

@Component({
  selector: 'app-encargados',
  standalone: true,
  imports: [ReactiveFormsModule, DecimalPipe],
  templateUrl: './encargados.html',
  styleUrls: ['./encargados.css'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class Encargados implements OnInit {
  private fb = inject(FormBuilder);
  private http = inject(HttpClient);
  private configService = inject(ConfigService);
  private alertService = inject(AlertService);

  encargadoForm!: FormGroup;
  usuarios = signal<Usuario[]>([]);
  guardando = signal(false);
  editandoCodigo = signal<number | null>(null);
  mostrarPassword = signal(false);
  mostrarConfirmPassword = signal(false);
  private currentUserCodigo: number | null = null;

  constructor() {
    this.initializeForm();
  }

  ngOnInit(): void {
    this.cargarUsuarios();
    this.http.get<{ codigo: number }>(`${this.configService.apiUrl}/auth/me`).subscribe({
      next: (user) => { this.currentUserCodigo = user.codigo; },
      error: () => {},
    });
  }

  private initializeForm(): void {
    this.encargadoForm = this.fb.group(
      {
        codigo: ['', [Validators.required, Validators.min(0)]],
        nombre: ['', Validators.required],
        comision: [0, [Validators.required, Validators.min(0)]],
        rol: this.fb.group(
          {
            admin: [false],
            encargado: [true],
          }
        ),
        observaciones: [''],
        email: ['', [Validators.required, Validators.email]],
        password: ['', [Validators.required, Validators.minLength(1)]],
        confirmPassword: ['', [Validators.required, Validators.minLength(1)]],
      },
      { validators: [this.passwordsMatchValidator] }
    );
  }

  private get passwordControl(): FormControl {
    return this.encargadoForm.get('password') as FormControl;
  }

  private get confirmPasswordControl(): FormControl {
    return this.encargadoForm.get('confirmPassword') as FormControl;
  }

  private setPasswordValidationForMode(isEditing: boolean): void {
    if (isEditing) {
      this.passwordControl.clearValidators();
      this.confirmPasswordControl.clearValidators();
    } else {
      this.passwordControl.setValidators([Validators.required, Validators.minLength(1)]);
      this.confirmPasswordControl.setValidators([Validators.required, Validators.minLength(1)]);
    }

    this.passwordControl.updateValueAndValidity();
    this.confirmPasswordControl.updateValueAndValidity();
  }

  private passwordsMatchValidator(control: AbstractControl): ValidationErrors | null {
    const password = control.get('password')?.value;
    const confirmPassword = control.get('confirmPassword')?.value;

    if (!password || !confirmPassword) {
      return null;
    }

    return password === confirmPassword ? null : { passwordMismatch: true };
  }

  cargarUsuarios(): void {
    const apiUrl = `${this.configService.apiUrl}/usuarios/`;

    this.http.get<Usuario[]>(apiUrl).subscribe({
      next: (data) => {
        const usuariosOrdenados = [...data].sort((a, b) => a.codigo - b.codigo);
        this.usuarios.set(usuariosOrdenados);
      },
      error: (err) => {
        console.error('Error al cargar usuarios:', err);
        this.alertService.error('No se pudieron cargar los usuarios');
        this.usuarios.set([]);
      },
    });
  }

  guardarUsuario(): void {
    if (this.encargadoForm.invalid || this.guardando()) {
      this.alertService.error('Por favor completa todos los campos requeridos');
      return;
    }

    this.estaEditando() ? this.actualizarUsuario() : this.crearUsuario();
  }

  private crearUsuario(): void {
    this.guardando.set(true);

    const formData = this.encargadoForm.getRawValue();
    const payload: UsuarioPayload = {
      codigo: Number(formData.codigo),
      nombre: String(formData.nombre).trim(),
      comision: Number(formData.comision ?? 0),
      rol: {
        admin: Boolean(formData.rol?.admin),
        encargado: Boolean(formData.rol?.encargado),
      },
      observaciones: String(formData.observaciones ?? '').trim(),
      email: String(formData.email ?? '').trim(),
      password: String(formData.password),
    };

    const apiUrl = `${this.configService.apiUrl}/usuarios/`;

    this.http.post<Usuario>(apiUrl, payload).subscribe({
      next: () => {
        this.alertService.success('Usuario creado correctamente');
        this.guardando.set(false);
        this.cargarUsuarios();
        this.limpiarFormulario();
      },
      error: (err) => {
        console.error('Error al crear usuario:', err);
        this.alertService.error(this.getErrorMessage(err, 'No se pudo crear el usuario'));
        this.guardando.set(false);
      },
    });
  }

  private async actualizarUsuario(): Promise<void> {
    const codigo = this.editandoCodigo();

    if (codigo === null) {
      this.alertService.error('No se encontro el usuario a editar');
      return;
    }

    const adminPassword = await this.alertService.requestPassword(
      'Confirmar contraseña',
      'Ingresa la contraseña del administrador en sesion para actualizar el usuario'
    );

    if (!adminPassword) {
      return;
    }

    this.guardando.set(true);

    const formData = this.encargadoForm.getRawValue();
    const payload: UsuarioUpdatePayload = {
      codigo: Number(formData.codigo),
      nombre: String(formData.nombre).trim(),
      comision: Number(formData.comision ?? 0),
      rol: {
        admin: Boolean(formData.rol?.admin),
        encargado: Boolean(formData.rol?.encargado),
      },
      observaciones: String(formData.observaciones ?? '').trim(),
      email: String(formData.email ?? '').trim(),
      password: adminPassword,
    };

    const apiUrl = `${this.configService.apiUrl}/usuarios/${codigo}`;

    this.http.put<Usuario>(apiUrl, payload).subscribe({
      next: () => {
        this.alertService.success('Usuario actualizado correctamente');
        this.guardando.set(false);
        this.cargarUsuarios();
        this.limpiarFormulario();
      },
      error: (err) => {
        console.error('Error al actualizar usuario:', err);
        this.alertService.error(this.getErrorMessage(err, 'No se pudo actualizar el usuario'));
        this.guardando.set(false);
      },
    });
  }

  async iniciarResetPassword(usuario: Usuario): Promise<void> {
    const nombre = usuario.nombre ?? `Código ${usuario.codigo}`;
    const result = await this.alertService.requestResetPassword(`Restablecer contraseña — ${nombre}`);
    if (!result) return;

    // Verificar la contraseña del administrador antes de ejecutar el reset
    const body = new URLSearchParams();
    body.set('username', String(this.currentUserCodigo ?? ''));
    body.set('password', result.admin);

    try {
      await firstValueFrom(
        this.http.post<any>(
          `${this.configService.apiUrl}/auth/login`,
          body.toString(),
          { headers: new HttpHeaders({ 'Content-Type': 'application/x-www-form-urlencoded' }) }
        )
      );
    } catch {
      this.alertService.error('Contraseña de administrador incorrecta');
      return;
    }

    const apiUrl = `${this.configService.apiUrl}/usuarios/${usuario.codigo}/reset-password`;
    this.http.patch<{ msg: string }>(apiUrl, null, {
      params: {
        codigo_usuario: String(usuario.codigo),
        nueva_pass: result.nueva,
      },
    }).subscribe({
      next: () => {
        this.alertService.success(`Contraseña de ${nombre} restablecida correctamente`);
      },
      error: (err) => {
        console.error('Error al restablecer contraseña:', err);
        this.alertService.error(this.getErrorMessage(err, 'No se pudo restablecer la contraseña'));
      },
    });
  }

  editarUsuario(usuario: Usuario): void {
    this.setPasswordValidationForMode(true);

    this.encargadoForm.patchValue({
      codigo: usuario.codigo,
      nombre: usuario.nombre ?? '',
      comision: usuario.comision ?? 0,
      rol: this.normalizarRol(usuario.rol),
      observaciones: usuario.observaciones ?? '',
      email: usuario.email ?? '',
      password: '',
      confirmPassword: '',
    });

    this.editandoCodigo.set(usuario.codigo);
    this.mostrarPassword.set(false);
    this.mostrarConfirmPassword.set(false);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  cancelarEdicion(): void {
    this.limpiarFormulario();
  }

  async eliminarUsuario(codigo: number): Promise<void> {
    const confirmed = await this.alertService.confirm(
      '¿Estás seguro de que deseas eliminar este usuario?',
      'Eliminar usuario'
    );

    if (!confirmed) {
      return;
    }

    this.guardando.set(true);
    const apiUrl = `${this.configService.apiUrl}/usuarios/${codigo}`;

    this.http.delete<{ mensaje: string }>(apiUrl).subscribe({
      next: () => {
        this.alertService.success('Usuario eliminado correctamente');

        if (this.editandoCodigo() === codigo) {
          this.limpiarFormulario();
        }

        this.cargarUsuarios();
        this.guardando.set(false);
      },
      error: (err) => {
        console.error('Error al eliminar usuario:', err);
        this.alertService.error(this.getErrorMessage(err, 'No se pudo eliminar el usuario'));
        this.guardando.set(false);
      },
    });
  }

  limpiarFormulario(): void {
    this.setPasswordValidationForMode(false);

    this.encargadoForm.reset({
      codigo: '',
      nombre: '',
      comision: 0,
      rol: {
        admin: false,
        encargado: true,
      },
      observaciones: '',
      email: '',
      password: '',
      confirmPassword: '',
    });
    this.mostrarPassword.set(false);
    this.mostrarConfirmPassword.set(false);
    this.editandoCodigo.set(null);
  }

  obtenerResumenRolesFormulario(): string {
    return this.formatearRol(this.encargadoForm.get('rol')?.value ?? null);
  }

  rolesSinPermisosSeleccionados(): boolean {
    const rolNormalizado = this.normalizarRol(this.encargadoForm.get('rol')?.value ?? null);
    return !rolNormalizado.admin && !rolNormalizado.encargado;
  }

  passwordConfirmacionInvalida(): boolean {
    const confirmControl = this.encargadoForm.get('confirmPassword');

    return Boolean(
      this.encargadoForm.hasError('passwordMismatch') &&
      confirmControl &&
      (confirmControl.touched || confirmControl.dirty)
    );
  }

  passwordConfirmacionValida(): boolean {
    const confirmControl = this.encargadoForm.get('confirmPassword');
    const password = this.encargadoForm.get('password')?.value;
    const confirmPassword = confirmControl?.value;

    return Boolean(
      password &&
      confirmPassword &&
      !this.encargadoForm.hasError('passwordMismatch') &&
      (confirmControl?.dirty || confirmControl?.touched)
    );
  }

  estadoConfirmacionPassword(): string {
    if (this.passwordConfirmacionValida()) {
      return 'Contrasenas coinciden';
    }

    if (this.passwordConfirmacionInvalida()) {
      return 'Las contrasenas no coinciden';
    }

    return 'Escribe la misma contraseña para confirmar';
  }

  alternarPassword(): void {
    this.mostrarPassword.update((value) => !value);
  }

  alternarConfirmPassword(): void {
    this.mostrarConfirmPassword.update((value) => !value);
  }

  estaEditando(): boolean {
    return this.editandoCodigo() !== null;
  }

  formatearRol(rol: RolUsuario | string | null): string {
    const rolNormalizado = this.normalizarRol(rol);
    const etiquetas: string[] = [];

    if (rolNormalizado.admin) {
      etiquetas.push('Administrador');
    }

    if (rolNormalizado.encargado) {
      etiquetas.push('Encargado');
    }

    return etiquetas.length > 0 ? etiquetas.join(' / ') : 'Sin roles';
  }

  obtenerClasesRol(rol: RolUsuario | string | null): string[] {
    const rolNormalizado = this.normalizarRol(rol);
    const clases: string[] = [];

    if (rolNormalizado.admin) {
      clases.push('Administrador');
    }

    if (rolNormalizado.encargado) {
      clases.push('Encargado');
    }

    return clases;
  }

  private normalizarRol(rol: RolUsuario | string | null): RolUsuario {
    if (!rol) {
      return { admin: false, encargado: false };
    }

    if (typeof rol === 'string') {
      try {
        const parsedRol = JSON.parse(rol) as Partial<RolUsuario>;
        return {
          admin: Boolean(parsedRol.admin),
          encargado: Boolean(parsedRol.encargado),
        };
      } catch {
        const rolTexto = rol.toLowerCase();
        return {
          admin: rolTexto.includes('admin'),
          encargado: rolTexto.includes('encargado'),
        };
      }
    }

    return {
      admin: Boolean(rol.admin),
      encargado: Boolean(rol.encargado),
    };
  }

  private getErrorMessage(err: any, fallback: string): string {
    return err?.error?.detail || err?.error?.message || fallback;
  }

}
