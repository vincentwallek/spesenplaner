import { Component } from '@angular/core';
import { RouterOutlet, RouterLink, RouterLinkActive } from '@angular/router';
import { AuthService } from './services/auth.service';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterOutlet, RouterLink, RouterLinkActive],
  template: `
    <div class="app-layout">
      @if (auth.isAuthenticated()) {
        <nav class="sidebar">
          <div class="sidebar-header">
            <a class="logo" routerLink="/dashboard" title="Zum Dashboard">
              <span class="logo-mark">RP</span>
              <span class="logo-text">Reise-Spesen<span class="logo-accent">Planer</span></span>
            </a>
          </div>

          <ul class="nav-links">
            <li>
              <a routerLink="/dashboard" routerLinkActive="active" id="nav-dashboard">
                <span>Dashboard</span>
              </a>
            </li>
            <li>
              <a routerLink="/expenses" routerLinkActive="active" [routerLinkActiveOptions]="{exact: true}" id="nav-expenses">
                <span>Spesenanträge</span>
              </a>
            </li>
            <li>
              <a routerLink="/expenses/new" routerLinkActive="active" id="nav-new-expense">
                <span>Neuer Antrag</span>
              </a>
            </li>
            @if (auth.currentUser()?.role === 'admin' || auth.currentUser()?.role === 'manager') {
              <li>
                <a routerLink="/users" routerLinkActive="active" id="nav-users">
                  <span>Benutzerverwaltung</span>
                </a>
              </li>
            }
          </ul>

          <div class="sidebar-footer">
            <div class="user-info">
              <div class="user-avatar">{{ (auth.currentUser()?.full_name || auth.currentUser()?.username)?.charAt(0)?.toUpperCase() || '?' }}</div>
              <div class="user-details">
                <span class="user-name">{{ auth.currentUser()?.full_name || auth.currentUser()?.username }}</span>
                <span class="user-role">{{ auth.currentUser()?.role }}</span>
              </div>
            </div>
            <button class="btn btn-secondary btn-sm w-full" (click)="auth.logout()" id="btn-logout">
              Abmelden
            </button>
          </div>
        </nav>
      }

      <main class="main-content" [class.full-width]="!auth.isAuthenticated()">
        <router-outlet />
      </main>
    </div>
  `,
  styles: [`
    .app-layout {
      display: flex;
      min-height: 100vh;
    }

    .sidebar {
      width: 260px;
      background: #162035;
      backdrop-filter: blur(20px);
      border-right: 1px solid rgba(255, 255, 255, 0.06);
      display: flex;
      flex-direction: column;
      position: fixed;
      height: 100vh;
      z-index: 100;
    }

    .sidebar-header {
      padding: 1.5rem;
      border-bottom: 1px solid rgba(255, 255, 255, 0.06);
    }

    .logo {
      display: flex;
      align-items: center;
      gap: 0.75rem;
      color: inherit;
    }

    .logo-mark {
      width: 32px;
      height: 32px;
      border-radius: 8px;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      background: var(--color-accent-primary);
      color: #ffffff;
      font-size: 0.8125rem;
      font-weight: 700;
    }

    .logo-text {
      font-size: 1.25rem;
      font-weight: 700;
      color: #f1f5f9;
    }

    .logo-accent {
      color: #7fb1ff;
    }

    .nav-links {
      list-style: none;
      padding: 1rem 0.75rem;
      flex: 1;
    }

    .nav-links li { margin-bottom: 0.25rem; }

    .nav-links a {
      display: flex;
      align-items: center;
      gap: 0.75rem;
      padding: 0.75rem 1rem;
      border-radius: var(--border-radius-sm);
      color: var(--color-text-secondary);
      font-weight: 500;
      font-size: 0.9375rem;
      transition: var(--transition);
    }

    .nav-links a:hover {
      background: rgba(255, 255, 255, 0.05);
      color: var(--color-text-primary);
    }

    .nav-links a.active {
      background: linear-gradient(135deg, rgba(99, 102, 241, 0.15), rgba(139, 92, 246, 0.1));
      color: var(--color-accent-secondary);
      border: 1px solid rgba(99, 102, 241, 0.2);
    }

    .sidebar-footer {
      padding: 1rem 1.25rem;
      border-top: 1px solid rgba(255, 255, 255, 0.06);
    }

    .user-info {
      display: flex;
      align-items: center;
      gap: 0.75rem;
      margin-bottom: 0.75rem;
    }

    .user-avatar {
      width: 36px;
      height: 36px;
      border-radius: 50%;
      background: linear-gradient(135deg, var(--color-accent-primary), #8b5cf6);
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: 700;
      font-size: 0.875rem;
      color: white;
    }

    .user-details {
      display: flex;
      flex-direction: column;
    }

    .user-name {
      font-weight: 600;
      font-size: 0.875rem;
      color: #e2e8f0;
    }

    .user-role {
      font-size: 0.75rem;
      color: #a7b1c2;
      text-transform: capitalize;
    }

    .main-content {
      flex: 1;
      margin-left: 260px;
      padding: 2rem;
      min-height: 100vh;
    }

    .main-content.full-width {
      margin-left: 0;
    }
  `],
})
export class AppComponent {
  constructor(public auth: AuthService) {}
}
