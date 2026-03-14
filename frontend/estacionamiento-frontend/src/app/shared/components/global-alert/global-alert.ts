import { Component, inject, ChangeDetectionStrategy, signal, effect } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { AlertService } from '../../../core/services/alert';

@Component({
  selector: 'app-global-alert',
  standalone: true,
  imports: [FormsModule],
  templateUrl: './global-alert.html',
  styleUrls: ['./global-alert.css'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class GlobalAlert {

  alertService = inject(AlertService);

  mostrarNuevaPass = signal(false);
  mostrarConfirmarNuevaPass = signal(false);
  mostrarAdminPass = signal(false);

  constructor() {
    effect(() => {
      const type = this.alertService.alertState()?.type;
      if (type === 'reset-password-step1') {
        this.mostrarNuevaPass.set(false);
        this.mostrarConfirmarNuevaPass.set(false);
      } else if (type === 'reset-password-step2') {
        this.mostrarAdminPass.set(false);
      }
    });
  }

  get resetStep1Valid(): boolean {
    const a = this.alertService.alertState();
    return !!(a?.inputValue && a?.inputValue2 && a.inputValue === a.inputValue2);
  }

  toggleNuevaPass() { this.mostrarNuevaPass.update(v => !v); }
  toggleConfirmarNuevaPass() { this.mostrarConfirmarNuevaPass.update(v => !v); }
  toggleAdminPass() { this.mostrarAdminPass.update(v => !v); }

}
