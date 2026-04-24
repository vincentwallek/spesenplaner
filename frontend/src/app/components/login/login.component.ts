import { Component, signal } from '@angular/core';
import { Router } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { AuthService } from '../../services/auth.service';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [FormsModule],
  template: `
    <div class="login-wrapper">
      <div class="login-card glass-card animate-in">
        <div class="login-header">
          <h1>Reise- und Spesenportal</h1>
          <p class="text-secondary">Melden Sie sich an, um fortzufahren</p>
        </div>

        @if (isRegistering()) {
          <form (ngSubmit)="onRegister()" class="login-form">
            <div class="form-group">
              <label for="reg-username">Benutzername</label>
              <input
                id="reg-username"
                class="form-control"
                type="text"
                [(ngModel)]="regUsername"
                name="regUsername"
                placeholder="Benutzername wählen"
                required
              />
            </div>
            <div class="form-group">
              <label for="reg-fullname">Vollständiger Name</label>
              <input
                id="reg-fullname"
                class="form-control"
                type="text"
                [(ngModel)]="regFullName"
                name="regFullName"
                placeholder="Max Mustermann"
              />
            </div>
            <div class="form-group">
              <label for="reg-password">Passwort</label>
              <input
                id="reg-password"
                class="form-control"
                type="password"
                [(ngModel)]="regPassword"
                name="regPassword"
                placeholder="Passwort wählen"
                required
              />
              <small class="field-hint">Mindestens 4 Zeichen</small>
            </div>

            @if (error()) {
              <div class="error-message">{{ error() }}</div>
            }
            @if (successMsg()) {
              <div class="success-message">{{ successMsg() }}</div>
            }

            <button type="submit" class="btn btn-primary w-full" [disabled]="loading()" id="btn-register">
              @if (loading()) { <span class="spinner" style="width:18px;height:18px;border-width:2px"></span> }
              Registrieren
            </button>
            <p class="toggle-text">
              Bereits registriert?
              <a href="javascript:void(0)" (click)="isRegistering.set(false)">Anmelden</a>
            </p>
          </form>
        } @else {
          <form (ngSubmit)="onLogin()" class="login-form">
            <div class="form-group">
              <label for="login-username">Benutzername</label>
              <input
                id="login-username"
                class="form-control"
                type="text"
                [(ngModel)]="username"
                name="username"
                placeholder="z.B. demo"
                required
              />
            </div>
            <div class="form-group">
              <label for="login-password">Passwort</label>
              <input
                id="login-password"
                class="form-control"
                type="password"
                [(ngModel)]="password"
                name="password"
                placeholder="Passwort eingeben"
                required
              />
            </div>

            @if (error()) {
              <div class="error-message">{{ error() }}</div>
            }

            <button type="submit" class="btn btn-primary w-full" [disabled]="loading()" id="btn-login">
              @if (loading()) { <span class="spinner" style="width:18px;height:18px;border-width:2px"></span> }
              Anmelden
            </button>

            <p class="toggle-text">
              Noch kein Konto?
              <a href="javascript:void(0)" (click)="isRegistering.set(true)">Registrieren</a>
            </p>

            <div class="demo-credentials">
              <p class="text-sm text-muted">Demo-Zugangsdaten:</p>
              <div class="cred-row">
                <code>demo / demo123</code>
                <code>manager / manager123</code>
                <code>admin / admin123</code>
              </div>
            </div>
          </form>
        }
      </div>
    </div>
  `,
  styles: [`
    .login-wrapper {
      display: flex;
      align-items: center;
      justify-content: center;
      min-height: 100vh;
      padding: 2rem;
    }

    .login-card {
      width: 100%;
      max-width: 420px;
      padding: 2.5rem;
    }

    .login-header {
      text-align: center;
      margin-bottom: 2rem;
    }

    .login-header h1 {
      font-size: 1.5rem;
      margin-bottom: 0.5rem;
    }

    .accent {
      color: var(--color-accent-primary);
    }

    .login-form {
      display: flex;
      flex-direction: column;
      gap: 0.25rem;
    }

    .error-message {
      padding: 0.75rem;
      background: var(--color-danger-bg);
      border: 1px solid rgba(239, 68, 68, 0.3);
      border-radius: var(--border-radius-sm);
      color: var(--color-danger);
      font-size: 0.875rem;
      margin-bottom: 0.5rem;
    }

    .success-message {
      padding: 0.75rem;
      background: var(--color-success-bg);
      border: 1px solid rgba(16, 185, 129, 0.3);
      border-radius: var(--border-radius-sm);
      color: var(--color-success);
      font-size: 0.875rem;
      margin-bottom: 0.5rem;
    }

    .toggle-text {
      text-align: center;
      margin-top: 1rem;
      font-size: 0.875rem;
      color: var(--color-text-secondary);
    }

    .demo-credentials {
      margin-top: 1.5rem;
      padding: 1rem;
      background: rgba(255, 255, 255, 0.03);
      border-radius: var(--border-radius-sm);
      border: 1px solid rgba(255, 255, 255, 0.06);
      text-align: center;
    }

    .field-hint {
      display: block;
      margin-top: 0.375rem;
      color: var(--color-text-muted);
      font-size: 0.75rem;
    }

    .cred-row {
      display: flex;
      flex-direction: column;
      gap: 0.25rem;
      margin-top: 0.5rem;
    }

    .cred-row code {
      font-size: 0.8125rem;
      color: var(--color-accent-secondary);
      background: rgba(99, 102, 241, 0.1);
      padding: 0.25rem 0.5rem;
      border-radius: 4px;
    }
  `],
})
export class LoginComponent {
  username = '';
  password = '';
  regUsername = '';
  regPassword = '';
  regFullName = '';

  loading = signal(false);
  error = signal('');
  successMsg = signal('');
  isRegistering = signal(false);

  constructor(private auth: AuthService, private router: Router) {
    if (auth.isAuthenticated()) {
      router.navigate(['/dashboard']);
    }
  }

  onLogin(): void {
    this.loading.set(true);
    this.error.set('');

    this.auth.login(this.username, this.password).subscribe({
      next: () => {
        this.loading.set(false);
        this.router.navigate(['/dashboard']);
      },
      error: (err) => {
        this.loading.set(false);
        this.error.set(this.getApiErrorMessage(err, 'Anmeldung fehlgeschlagen'));
      },
    });
  }

  onRegister(): void {
    this.loading.set(true);
    this.error.set('');
    this.successMsg.set('');

    this.auth.register(this.regUsername, this.regPassword, this.regFullName).subscribe({
      next: () => {
        this.loading.set(false);
        this.successMsg.set('Registrierung erfolgreich! Sie können sich jetzt anmelden.');
        setTimeout(() => this.isRegistering.set(false), 2000);
      },
      error: (err) => {
        this.loading.set(false);
        this.error.set(this.getApiErrorMessage(err, 'Registrierung fehlgeschlagen'));
      },
    });
  }

  private getApiErrorMessage(err: any, fallback: string): string {
    const detail = err?.error?.detail;
    if (!detail) return fallback;
    if (typeof detail === 'string') return detail;
    if (Array.isArray(detail)) {
      const messages = detail
        .map((item) => item?.msg || item?.message)
        .filter((msg) => typeof msg === 'string');
      if (messages.length > 0) return messages.join(' | ');
    }
    return fallback;
  }
}
