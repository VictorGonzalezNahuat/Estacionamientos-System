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
import { reimpresionTicketsGuard } from './guards/reimpresion-tickets-guard';
import { ConfiguracionImpresora } from './pages/dashboard/configuracion-impresora/configuracion-impresora';
import { configuracionImpresoraGuard } from './guards/configuracion-impresora-guard';
import { cancelacionTicketsGuard } from './guards/cancelacion-tickets-guard';

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
      },
      {
        path: 'reimpresion-tickets',
        loadComponent: ()=> import('./pages/dashboard/reimpresion-tickets/reimpresion-tickets').then(m=> m.ReimpresionTickets),
        canActivate: [reimpresionTicketsGuard]
      },
      {
        path: 'configuracion-impresora',
        loadComponent: () => import('./pages/dashboard/configuracion-impresora/configuracion-impresora').then(m=>m.ConfiguracionImpresora),
        canActivate: [configuracionImpresoraGuard]
      },
      {
        path: 'cancelacion-tickets',
        loadComponent: () => import('./pages/dashboard/cancelacion-tickets/cancelacion-tickets').then(m=> m.CancelacionTickets),
        canActivate: [cancelacionTicketsGuard]
      }

    ]
  },
  {
    path: 'acceso-movil',
    loadComponent: () => import('./pages/acceso-movil/acceso-movil').then(m => m.AccesoMovil),
    canActivate: [authGuard]
  },
  {
    path: 'facturacion/registro-cliente',
    loadComponent: () => import('./pages/facturacion/registro-cliente/registro-cliente').then(m => m.RegistroCliente)
  },
  {
    path: 'facturacion',
    loadComponent: () => import('./pages/facturacion/facturacion').then(m => m.Facturacion)
  },
  {
    path: 'facturacion/descarga-documentos',
    loadComponent: () => import('./pages/facturacion/descarga-documentos/descarga-documentos').then(m => m.DescargaDocumentos)
  },
  { path: '', redirectTo: 'login', pathMatch: 'full' }
];
