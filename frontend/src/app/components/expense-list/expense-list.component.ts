import { Component, OnInit, signal } from '@angular/core';
import { Router, RouterLink } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { ExpenseService } from '../../services/expense.service';
import { Expense, STATUS_LABELS, STATUS_CSS } from '../../models/expense.model';
import { DatePipe, DecimalPipe, KeyValuePipe } from '@angular/common';
import { AuthService } from '../../services/auth.service';

@Component({
  selector: 'app-expense-list',
  standalone: true,
  imports: [RouterLink, FormsModule, DatePipe, DecimalPipe, KeyValuePipe],
  template: `
    <div class="animate-in">
      <div class="page-header">
        <h1>Spesenanträge</h1>
        <a routerLink="/expenses/new" class="btn btn-primary" id="btn-new-expense">Neuer Antrag</a>
      </div>

      @if (getNeedsRevisionExpenses().length > 0) {
        <div class="glass-card mb-3" style="background: rgba(249, 115, 22, 0.1); border-color: rgba(249, 115, 22, 0.3);">
          <div style="display: flex; align-items: center; gap: 1rem;">
            <div style="font-size: 2rem;">⚠️</div>
            <div>
              <h3 style="color: #c2410c; margin-bottom: 0.25rem;">Überarbeitung erforderlich!</h3>
              <p class="text-sm text-secondary">
                Du hast <strong>{{ getNeedsRevisionExpenses().length }}</strong> Antrag/Anträge, die überarbeitet werden müssen.
                Bitte prüfe das Feedback im Antrag und reiche ihn erneut ein.
              </p>
            </div>
          </div>
        </div>
      }

      @if (getMessageNotifications().length > 0) {
        <div class="glass-card mb-3" style="background: rgba(59, 130, 246, 0.1); border-color: rgba(59, 130, 246, 0.3);">
          <div style="display: flex; align-items: center; gap: 1rem;">
            <div style="font-size: 2rem;">📩</div>
            <div>
              <h3 style="color: #2563eb; margin-bottom: 0.25rem;">Neue Nachricht(en) vom Manager</h3>
              <p class="text-sm text-secondary">
                Du hast <strong>{{ getMessageNotifications().length }}</strong> Antrag/Anträge mit einer Nachricht.
                Klicke auf Details, um die Nachricht zu lesen.
              </p>
            </div>
          </div>
        </div>
      }

      <div class="glass-card mb-3">
        <div class="filter-row">
          <label class="text-sm text-secondary">Status-Filter:</label>
          <select class="form-control" style="max-width:220px" [(ngModel)]="statusFilter" (ngModelChange)="load()" id="status-filter">
            <option value="">Alle</option>
            <option value="DRAFT">Entwurf</option>
            <option value="SUBMITTED">Eingereicht</option>
            <option value="APPROVED">Genehmigt</option>
            <option value="REJECTED">Abgelehnt</option>
            <option value="PAID">Ausgezahlt</option>
          </select>
        </div>
      </div>


      @if (router.url.includes('dashboard') && (auth.currentUser()?.role === 'admin' || auth.currentUser()?.role === 'manager') && expenses().length > 0 && !statusFilter) {
        <div class="glass-card mb-3 chart-card">
          <h3 class="mb-3">Ausgaben-Übersicht</h3>
          <div class="chart-container">
            <div class="pie-chart" [style.background]="getChartGradient()"></div>
            <div class="chart-legend">
              @for (item of getChartStats() | keyvalue; track item.key) {
                <div class="legend-item">
                  <span class="legend-color" [style.background]="item.value.color"></span>
                  <div class="legend-text">
                    <span class="legend-label">{{ getLabel(item.key) }}</span>
                    <span class="legend-value">{{ item.value.amount | number:'1.2-2' }} {{ item.value.currency || '€' }} ({{ item.value.count }})</span>
                  </div>
                </div>
              }
            </div>
          </div>
        </div>
      }

      @if (loading()) {
        <div class="loading-overlay"><div class="spinner"></div><span>Lade...</span></div>
      } @else if (expenses().length === 0) {
        <div class="glass-card text-center" style="padding:3rem">
          <p class="text-secondary">Keine Anträge gefunden.</p>
          <a routerLink="/expenses/new" class="btn btn-primary mt-2">Ersten Antrag erstellen</a>
        </div>
      } @else {
        <div class="glass-card">
          <div class="table-container">
            <table>
              <thead>
                <tr><th>Titel</th><th>Kategorie</th><th>Betrag</th><th>Status</th><th>Erstellt</th><th></th></tr>
              </thead>
              <tbody>
                @for (e of expenses(); track e.id) {
                  <tr>
                    <td><a [routerLink]="['/expenses', e.id]" class="expense-link">{{ e.title }}</a></td>
                    <td class="text-secondary text-sm">{{ e.category || '—' }}</td>
                    <td style="font-weight:600;font-variant-numeric:tabular-nums">{{ e.amount | number:'1.2-2' }} {{ e.currency }}</td>
                    <td><span class="badge" [class]="getCss(e.status)">{{ getLabel(e.status) }}</span></td>
                    <td class="text-secondary text-sm">{{ e.created_at | date:'dd.MM.yy' }}</td>
                    <td class="text-right"><a [routerLink]="['/expenses', e.id]" class="btn btn-secondary btn-sm">Details</a></td>
                  </tr>
                }
              </tbody>
            </table>
          </div>
        </div>
      }
    </div>
  `,
  styles: [`
    .page-header { display:flex; justify-content:space-between; align-items:center; margin-bottom:1.5rem; }
    .filter-row { display:flex; align-items:center; gap:1rem; }
    .expense-link { font-weight:500; color:var(--color-text-primary); }
    .expense-link:hover { color:var(--color-accent-secondary); }
    .chart-card { padding: 1.5rem; }
    .chart-container { display: flex; align-items: center; gap: 2rem; flex-wrap: wrap; }
    .pie-chart { width: 150px; height: 150px; border-radius: 50%; box-shadow: 0 4px 12px rgba(0,0,0,0.1); flex-shrink: 0; }
    .chart-legend { display: flex; flex-direction: column; gap: 0.75rem; flex-grow: 1; }
    .legend-item { display: flex; align-items: center; gap: 0.75rem; }
    .legend-color { width: 12px; height: 12px; border-radius: 50%; flex-shrink: 0; }
    .legend-text { display: flex; justify-content: space-between; flex-grow: 1; border-bottom: 1px solid rgba(255,255,255,0.05); padding-bottom: 0.25rem; }
    .legend-label { font-size: 0.875rem; color: var(--color-text-secondary); }
    .legend-value { font-size: 0.875rem; font-weight: 600; color: var(--color-text-primary); }

  `],
})
export class ExpenseListComponent implements OnInit {
  expenses = signal<Expense[]>([]);
  loading = signal(true);
  statusFilter = '';

  constructor(private svc: ExpenseService, public auth: AuthService, public router: Router) {}
  ngOnInit() { this.load(); }

  load() {
    this.loading.set(true);
    this.svc.getExpenses(this.statusFilter || undefined).subscribe({
      next: (d) => { this.expenses.set(d.items || []); this.loading.set(false); },
      error: () => this.loading.set(false),
    });
  }

  getLabel(s: string) { return STATUS_LABELS[s] || s; }
  getCss(s: string) { return STATUS_CSS[s] || 'badge-draft'; }

  getChartStats() {
    const stats: Record<string, { amount: number, count: number, color: string, currency: string }> = {};
    const colors: Record<string, string> = {
      'APPROVED': '#10b981', // success
      'PAID': '#3b82f6', // info
      'REJECTED': '#ef4444', // danger
      'BUDGET_DENIED': '#f59e0b', // warning
      'PAYOUT_FAILED': '#f43f5e', // rose
      'SUBMITTED': '#8b5cf6', // purple
      'DRAFT': '#6b7280', // gray
      'BUDGET_CONFIRMED': '#06b6d4', // cyan
      'NEEDS_REVISION': '#f97316', // orange
    };

    let total = 0;
    for (const e of this.expenses()) {
      if (!stats[e.status]) stats[e.status] = { amount: 0, count: 0, color: colors[e.status] || '#ccc', currency: e.currency };
      stats[e.status].amount += e.amount;
      stats[e.status].count++;
      total += e.amount;
    }
    
    // Sort by amount
    return Object.fromEntries(Object.entries(stats).sort((a, b) => b[1].amount - a[1].amount));
  }

  getChartGradient() {
    const stats = this.getChartStats();
    let totalAmount = 0;
    for (const key in stats) totalAmount += stats[key].amount;
    
    if (totalAmount === 0) return 'conic-gradient(#333 0% 100%)';

    let gradient = 'conic-gradient(';
    let currentPercentage = 0;
    
    const entries = Object.entries(stats);
    for (let i = 0; i < entries.length; i++) {
      const [key, stat] = entries[i];
      const percentage = (stat.amount / totalAmount) * 100;
      gradient += `${stat.color} ${currentPercentage}% ${currentPercentage + percentage}%`;
      if (i < entries.length - 1) gradient += ', ';
      currentPercentage += percentage;
    }
    gradient += ')';
    
    return gradient;
  }


  getNeedsRevisionExpenses(): Expense[] {
    const username = this.auth.currentUser()?.username;
    return this.expenses().filter(e => e.status === 'NEEDS_REVISION' && e.created_by === username);
  }

  getMessageNotifications(): Expense[] {
    const username = this.auth.currentUser()?.username;
    return this.expenses().filter(e => e.manager_message && e.created_by === username && e.status === 'BUDGET_DENIED');
  }
}
