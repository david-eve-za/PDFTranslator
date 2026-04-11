import { Routes } from '@angular/router';

export const routes: Routes = [
  {
    path: '',
    redirectTo: '/translate',
    pathMatch: 'full',
  },
  {
    path: 'translate',
    loadComponent: () =>
      import('./features/translate/translate.component').then(
        (m) => m.TranslateComponent
      ),
  },
  {
    path: 'glossary',
    loadComponent: () =>
      import('./features/glossary/glossary.component').then(
        (m) => m.GlossaryComponent
      ),
  },
  {
    path: '**',
    redirectTo: '/translate',
  },
];
