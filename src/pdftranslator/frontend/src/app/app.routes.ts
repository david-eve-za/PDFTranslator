import { Routes } from '@angular/router';

export const routes: Routes = [
  {
    path: '',
    redirectTo: '/dashboard',
    pathMatch: 'full'
  },
  {
    path: 'dashboard',
    loadComponent: () =>
      import('./features/dashboard/dashboard.component').then(m => m.DashboardComponent)
  },
  {
    path: 'library',
    loadComponent: () =>
      import('./features/library/library.component').then(m => m.LibraryComponent)
  },
  {
    path: 'files',
    loadComponent: () =>
      import('./features/files/files.component').then(m => m.FilesComponent)
  },
  {
    path: 'translate',
    loadComponent: () =>
      import('./features/translate/translate.component').then(m => m.TranslateComponent)
  },
  {
    path: 'glossary',
    loadComponent: () =>
      import('./features/glossary/glossary.component').then(m => m.GlossaryComponent)
  },
  {
    path: 'split',
    loadComponent: () =>
      import('./features/split-chapters/split.component').then(m => m.SplitComponent)
  },
  {
    path: '**',
    redirectTo: '/dashboard'
  }
];
