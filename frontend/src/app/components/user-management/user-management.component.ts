import { Component, OnInit, signal } from '@angular/core';
import { UserService } from '../../services/user.service';
import { UserInfo } from '../../models/expense.model';
import { FormsModule } from '@angular/forms';
import { AuthService } from '../../services/auth.service';

@Component({
  selector: 'app-user-management',
  standalone: true,
  imports: [FormsModule],
  template: `
    <div class="animate-in">
      <div class="page-header">
        <h1>Benutzerverwaltung</h1>
        <p class="text-muted mt-1">Verwalten Sie hier die Rollen aller registrierten Benutzer.</p>
      </div>

      <div class="glass-card">
        @if (loading()) {
          <div class="loading-overlay"><div class="spinner"></div><span>Lade Benutzer...</span></div>
        } @else {
          <table class="data-table">
            <thead>
              <tr>
                <th>Benutzername</th>
                <th>Voller Name</th>
                <th>Rolle</th>
                <th class="text-right">Aktion</th>
              </tr>
            </thead>
            <tbody>
              @for (user of users(); track user.username) {
                <tr>
                  <td>
                    <div class="user-cell">
                      <div class="user-avatar-sm">{{ user.username.charAt(0).toUpperCase() }}</div>
                      <span class="font-medium">{{ user.username }}</span>
                    </div>
                  </td>
                  <td>{{ user.full_name || '—' }}</td>
                  <td>
                    <select class="form-control form-control-sm" [(ngModel)]="user.role" style="max-width: 150px;" [disabled]="!canEditRole(user)">
                      <option value="user">User</option>
                      <option value="manager">Manager</option>
                      <option value="admin">Admin</option>
                    </select>
                  </td>
                  <td class="text-right">
                    <button class="btn btn-sm btn-primary" (click)="updateRole(user)" [disabled]="actionLoading() === user.username || !canEditRole(user)">
                      @if (actionLoading() === user.username) {
                        Speichern...
                      } @else {
                        Speichern
                      }
                    </button>
                  </td>
                </tr>
              }
              @if (users().length === 0) {
                <tr>
                  <td colspan="4" class="text-center text-muted py-4">Keine Benutzer gefunden.</td>
                </tr>
              }
            </tbody>
          </table>
        }
      </div>

      @if (actionMsg()) {
        <div class="toast toast-success">{{ actionMsg() }}</div>
      }
      @if (errorMsg()) {
        <div class="toast toast-danger" style="background: var(--color-danger); color: white; border-color: rgba(239, 68, 68, 0.4);">
          {{ errorMsg() }}
        </div>
      }
    </div>
  `,
  styles: [`
    .page-header { margin-bottom: 2rem; }
    .data-table { width: 100%; border-collapse: collapse; }
    .data-table th { text-align: left; padding: 1rem; border-bottom: 1px solid rgba(255,255,255,0.1); color: var(--color-text-muted); font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.05em; font-weight: 600; }
    .data-table td { padding: 1rem; border-bottom: 1px solid rgba(255,255,255,0.05); vertical-align: middle; color: var(--color-text-primary); font-size: 0.875rem; }
    .data-table tbody tr:hover { background: rgba(255,255,255,0.02); }
    .user-cell { display: flex; align-items: center; gap: 0.75rem; }
    .user-avatar-sm { width: 28px; height: 28px; border-radius: 50%; background: linear-gradient(135deg, var(--color-accent-primary), #8b5cf6); display: flex; align-items: center; justify-content: center; font-weight: 700; font-size: 0.75rem; color: white; }
    .form-control-sm { padding: 0.375rem 0.75rem; font-size: 0.875rem; }
  `]
})
export class UserManagementComponent implements OnInit {
  users = signal<UserInfo[]>([]);
  loading = signal(true);
  actionLoading = signal<string | null>(null);
  actionMsg = signal('');
  errorMsg = signal('');

  constructor(private userService: UserService, public auth: AuthService) {}

  ngOnInit() {
    this.loadUsers();
  }

  canEditRole(user: UserInfo): boolean {
    const currentUser = this.auth.currentUser();
    if (!currentUser) return false;
    
    // Cannot edit self
    if (currentUser.username === user.username) return false;
    
    return true;
  }

  loadUsers() {
    this.loading.set(true);
    this.userService.getUsers().subscribe({
      next: (data) => {
        this.users.set(data);
        this.loading.set(false);
      },
      error: () => {
        this.loading.set(false);
        this.showError('Fehler beim Laden der Benutzer');
      }
    });
  }

  updateRole(user: UserInfo) {
    this.actionLoading.set(user.username);
    this.userService.updateUserRole(user.username, user.role).subscribe({
      next: (updatedUser) => {
        this.actionLoading.set(null);
        this.showMsg(`Rolle für ${user.username} aktualisiert!`);
        // Update user in the list
        this.users.update(users => users.map(u => u.username === updatedUser.username ? updatedUser : u));
      },
      error: () => {
        this.actionLoading.set(null);
        this.showError('Fehler beim Aktualisieren der Rolle');
      }
    });
  }

  private showMsg(msg: string) {
    this.actionMsg.set(msg);
    setTimeout(() => this.actionMsg.set(''), 3000);
  }

  private showError(msg: string) {
    this.errorMsg.set(msg);
    setTimeout(() => this.errorMsg.set(''), 3000);
  }
}
