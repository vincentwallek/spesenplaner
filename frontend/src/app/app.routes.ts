import { Routes } from '@angular/router';
import { authGuard } from './guards/auth.guard';

export const routes: Routes = [
  {
    path: 'login',
    loadComponent: () =>
      import('./components/login/login.component').then((m) => m.LoginComponent),
  },
  {
    path: '',
    canActivate: [authGuard],
    children: [
      {
        path: 'dashboard',
        loadComponent: () =>
          import('./components/expense-list/expense-list.component').then((m) => m.ExpenseListComponent),
      },
      {
        path: 'expenses',
        loadComponent: () =>
          import('./components/expense-list/expense-list.component').then((m) => m.ExpenseListComponent),
      },
      {
        path: 'expenses/new',
        loadComponent: () =>
          import('./components/expense-form/expense-form.component').then((m) => m.ExpenseFormComponent),
      },
      {
        path: 'expenses/:id',
        loadComponent: () =>
          import('./components/expense-detail/expense-detail.component').then((m) => m.ExpenseDetailComponent),
      },
      {
        path: 'expenses/:id/edit',
        loadComponent: () =>
          import('./components/expense-form/expense-form.component').then((m) => m.ExpenseFormComponent),
      },
      {
        path: 'users',
        loadComponent: () =>
          import('./components/user-management/user-management.component').then((m) => m.UserManagementComponent),
      },
      { path: '', redirectTo: 'dashboard', pathMatch: 'full' },
    ],
  },
  { path: '**', redirectTo: 'dashboard' },
];
