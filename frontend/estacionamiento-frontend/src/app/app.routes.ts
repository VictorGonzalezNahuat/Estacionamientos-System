import { Routes } from '@angular/router';
import { Login } from './pages/login/login';
import { Dashboard } from './pages/dashboard/dashboard';
import { DashboardMain } from './pages/dashboard/dashboard-main/dashboard-main';
import { AperturaTurno } from './pages/dashboard/apertura-turno/apertura-turno';
import { turnoGuard } from './guards/turno-guard';

export const routes: Routes = [
  { path: 'login', component: Login },
  {
  path: 'dashboard',
    component: Dashboard,
    children: [
        { path: '', component: DashboardMain },
        { 
            path: 'apertura_turno', 
            component: AperturaTurno,
            canActivate: [turnoGuard]   // 🔥 AQUÍ
            }
    ]
    },
  { path: '', redirectTo: 'login', pathMatch: 'full' }
];
