import { Routes } from '@angular/router';
import { authGuard } from './guards/auth-guard';
import { turnoGuard } from './guards/turno-guard';
import { cierreTurnoGuard } from './guards/cierre-turno-guard';
import { entradasSalidasGuard } from './guards/entradas-salidas-guard';

export const routes: Routes = [
  {
    path: 'login',
    loadComponent: () => import('./pages/login/login').then(m => m.Login)
  },
  {
    path: 'dashboard',
    loadComponent: () => import('./pages/dashboard/dashboard').then(m => m.Dashboard),
    canActivate: [authGuard],
    children: [
      {
        path: '',
        loadComponent: () => import('./pages/dashboard/dashboard-main/dashboard-main').then(m => m.DashboardMain)
      },
      {
        path: 'apertura_turno',
        loadComponent: () => import('./pages/dashboard/apertura-turno/apertura-turno').then(m => m.AperturaTurno),
        canActivate: [turnoGuard]
      },
      {
        path: 'cierre_turno',
        loadComponent: () => import('./pages/dashboard/cierre-turno/cierre-turno').then(m => m.CierreTurno),
        canActivate: [cierreTurnoGuard]
      },
      {
        path: 'entradas_salidas',
        loadComponent: () => import('./pages/dashboard/entradas-salidas/entradas-salidas').then(m => m.EntradasSalidas),
        canActivate: [entradasSalidasGuard]
      },
      {
        path: 'corte_caja',
        loadComponent: () => import('./pages/dashboard/corte-caja/corte-caja').then(m => m.CorteCaja)
      },
      {
        path: 'tarifas',
        loadComponent: () => import('./pages/dashboard/tarifas/tarifas').then(m => m.Tarifas)
      }
    ]
  },
  { path: '', redirectTo: 'login', pathMatch: 'full' }
];
