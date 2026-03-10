import { Component, HostListener, inject, OnInit, ChangeDetectionStrategy, signal } from '@angular/core';
import { Router, RouterOutlet, RouterLink } from "@angular/router";
import { AuthService } from '../../services/auth.service';
import { TariffService } from '../../services/tariff.service';
import { AlertService } from '../../core/services/alert';

@Component({
  selector: 'app-dashboard',
  templateUrl: './dashboard.html',
  styleUrl: './dashboard.css',
  imports: [RouterOutlet, RouterLink],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class Dashboard implements OnInit {

  private router = inject(Router);
  private authService = inject(AuthService);
  private tariffService = inject(TariffService);
  private alertService = inject(AlertService);

  openMenu = signal<string | null>(null);
  currentUser = signal<any>(null);
  currentTariff = signal<any>(null);
  userInitials = signal('');

  ngOnInit(): void {
    this.loadUserData();
    this.loadTariffData();
  }

  loadUserData(): void {
    this.authService.getCurrentUser().subscribe({
      next: (response: any) => {
        this.currentUser.set({
          codigo: response.codigo,
          nombre: response.nombre
        });
        this.generateInitials();
      },
      error: (error) => {
        console.error('Error cargando usuario:', error);
        this.currentUser.set({ codigo: 'N/A', nombre: 'Usuario' });
      }
    });
  }

  loadTariffData(): void {
    this.tariffService.getDefaultTariff().subscribe({
      next: (response: any) => {
        this.currentTariff.set({
          hora: response.hora,
          medio_dia: response.medio_dia,
          fraccion: response.fraccion,
          diario: response.diario,
          tipo_vehiculo: response.tipo_vehiculo
        });
      },
      error: (error) => {
        console.error('Error cargando tarifa:', error);
        this.currentTariff.set({
          hora: 'N/A',
          medio_dia: 'N/A',
          fraccion: 'N/A',
          diario: 'N/A',
          tipo_vehiculo: 'N/A'
        });
      }
    });
  }

  generateInitials(): void {
    const user = this.currentUser();
    if (user?.nombre) {
      const names = user.nombre.split(' ');
      this.userInitials.set(names.map((n: string) => n.charAt(0).toUpperCase()).join(''));
    }
  }

  toggleMenu(menu: string): void {
    this.openMenu.set(this.openMenu() === menu ? null : menu);
  }

  navigate(): void {
    this.openMenu.set(null);
  }

  @HostListener('document:click')
  closeMenu(): void {
    this.openMenu.set(null);
  }

  logout(): void {
    const message = '¿Deseas cerrar tu sesión?\n\nEsta acción no sustituye el cierre de turno';
    this.alertService.confirm(
      message,
      'Cerrar Sesión',
      'Cerrar Sesión',
      'Cancelar'
    ).then((confirmed) => {
      if (confirmed) {
        localStorage.removeItem('token');
        this.router.navigate(['/login']);
      }
    });
  }

}
