import { Routes } from '@angular/router';
import { authGuard } from './guards/auth-guard';
import { turnoGuard } from './guards/turno-guard';
import { cierreTurnoGuard } from './guards/cierre-turno-guard';
import { entradasSalidasGuard } from './guards/entradas-salidas-guard';
import { tarifasGuard } from './guards/tarifas-guard';
import { encargadosGuard } from './guards/encargados-guard';
import { corteCajaGuard } from './guards/corte-caja-guard';
import { configuracionGuard } from './guards/configuracion-guard';
import { configuracionCortesGuard } from './guards/configuracion-cortes-guard';

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
        loadComponent: () => import('./pages/dashboard/corte-caja/corte-caja').then(m => m.CorteCaja),
        canActivate: [corteCajaGuard]
      },
      {
        path: 'tarifas',
        loadComponent: () => import('./pages/dashboard/tarifas/tarifas').then(m => m.Tarifas),
        canActivate: [tarifasGuard]
      },
      {
        path: 'encargados',
        loadComponent: () => import('./pages/dashboard/encargados/encargados').then(m => m.Encargados),
        canActivate: [encargadosGuard]
      },
      {
        path: 'estacionados',
        loadComponent: () => import('./pages/dashboard/estacionados/estacionados').then(m => m.Estacionados)
      },
      {
        path: 'configuracion',
        loadComponent: () => import('./pages/dashboard/configuracion/configuracion').then(m => m.Configuracion),
        canActivate: [configuracionGuard]
      },
      {
        path: 'configuracion-cortes',
        loadComponent: () => import('./pages/dashboard/configuracion-cortes/configuracion-cortes').then(m => m.ConfiguracionCortes),
        canActivate: [configuracionCortesGuard]
      }

    ]
  },
  {
    path: 'acceso-movil',
    loadComponent: () => import('./pages/acceso-movil/acceso-movil').then(m => m.AccesoMovil),
    canActivate: [authGuard]
  },
  { path: '', redirectTo: 'login', pathMatch: 'full' }
];
