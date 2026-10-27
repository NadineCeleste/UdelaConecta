import { Routes } from '@angular/router';
import { Home } from './componentes/home/home';
import { authGuard } from './servicios/guards/authGuard';

export const routes: Routes = [
  { path: '', component: Home },
  { path: 'home', loadComponent: () => import('./componentes/home/home').then((m) => m.Home) },
  {
    path: 'contratos',
    canActivate: [authGuard],
    loadComponent: () => import('./componentes/contratos/contratos').then((m) => m.Contratos),
  },
  {
    path: 'profile',
    canActivate: [authGuard],
    loadComponent: () =>
      import('./componentes/profile/profile').then((m) => m.ProfileComponent),
  },
  {
    path: 'miproyecto',
    canActivate: [authGuard],
    loadComponent: () => import('./componentes/miproyecto/miproyecto').then((m) => m.Miproyecto),
  },
  {
    path: 'formcreateproyect',
    canActivate: [authGuard],
    loadComponent: () => import('./views/formcreateproyect/formcreateproyect').then((m) => m.Formcreateproyect)
  },
  {
    path: 'formcreateproyect/:email',
    canActivate: [authGuard],
    loadComponent: () => import('./views/formcreateproyect/formcreateproyect').then((m) => m.Formcreateproyect)
  },
  {
    path: 'formcreatecontract',
    canActivate: [authGuard],
    loadComponent: () => import('./views/formcreatecontract/formcreatecontract').then((m) => m.Formcreatecontract)
  },
  {
    path: 'formcreatecontract/:project_id',
    canActivate: [authGuard],
    loadComponent: () => import('./views/formcreatecontract/formcreatecontract').then((m) => m.Formcreatecontract)
  },
  {
    path: 'profile/:email',
    canActivate: [authGuard],
    loadComponent: () =>
      import('./componentes/profile/profile').then((m) => m.ProfileComponent)
  },
];