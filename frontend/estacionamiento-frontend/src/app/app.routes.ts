import { Routes } from '@angular/router';
import { Login } from './pages/login/login';
import { Dashboard } from './pages/dashboard/dashboard';
import { DashboardMain } from './pages/dashboard/dashboard-main/dashboard-main';
import { AperturaTurno } from './pages/dashboard/apertura-turno/apertura-turno';
import { turnoGuard } from './guards/turno-guard';
import { authGuard } from './guards/auth-guard';
import { CierreTurno } from './pages/dashboard/cierre-turno/cierre-turno';
import { cierreTurnoGuard } from './guards/cierre-turno-guard';
import { EntradasSalidas } from './pages/dashboard/entradas-salidas/entradas-salidas';
import { entradasSalidasGuard } from './guards/entradas-salidas-guard';
import { CorteCaja } from './pages/dashboard/corte-caja/corte-caja';

export const routes: Routes = [
  { path: 'login', component: Login },
  {
  path: 'dashboard',
  component: Dashboard,
  canActivate: [authGuard],
  children: [
        { path: '', component: DashboardMain },
        { 
            path: 'apertura_turno', 
            component: AperturaTurno,
            canActivate: [turnoGuard] 
        },
        {
          path: 'cierre_turno',
          component: CierreTurno,
          canActivate: [cierreTurnoGuard]
        },
        {
          path:'entradas_salidas',
          component: EntradasSalidas,
          canActivate: [entradasSalidasGuard]
        },
        {
          path: 'corte_caja',
          component: CorteCaja,
        }
    ]
    },
  { path: '', redirectTo: 'login', pathMatch: 'full' }
];
