import { Component, OnInit, OnDestroy, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MonitoringService, BusinessDashboard, MonitoringLogs } from '../../services/monitoring.service';

@Component({
  selector: 'app-business-monitoring',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './business-monitoring.component.html',
  styleUrl: './business-monitoring.component.css',
})
export class BusinessMonitoringComponent implements OnInit, OnDestroy {
  dashboard = signal<BusinessDashboard | null>(null);
  logs = signal<MonitoringLogs | null>(null);
  loading = signal(true);
  error = signal<string | null>(null);
  lastUpdated = signal<Date | null>(null);

  private refreshInterval: any;

  totalExpenses = computed(() => this.dashboard()?.metrics?.expenses?.total_count ?? 0);
  totalAmount = computed(() => this.dashboard()?.metrics?.expenses?.total_amount ?? 0);
  avgAmount = computed(() => this.dashboard()?.metrics?.expenses?.average_amount ?? 0);
  todayCount = computed(() => this.dashboard()?.metrics?.expenses?.today_count ?? 0);
  weekCount = computed(() => this.dashboard()?.metrics?.expenses?.week_count ?? 0);
  uniqueUsers = computed(() => this.dashboard()?.metrics?.expenses?.unique_users ?? 0);
  approvalRate = computed(() => this.dashboard()?.metrics?.approvals?.approval_rate ?? 0);
  totalPaid = computed(() => this.dashboard()?.metrics?.payouts?.total_paid ?? 0);
  payoutSuccess = computed(() => this.dashboard()?.metrics?.payouts?.success_rate ?? 0);

  budgetSpent = computed(() => this.dashboard()?.metrics?.budgets?.spent ?? 0);
  budgetTotal = computed(() => this.dashboard()?.metrics?.budgets?.total_budget ?? 10000);
  budgetRemaining = computed(() => this.dashboard()?.metrics?.budgets?.remaining ?? 0);
  budgetPercent = computed(() => {
    const total = this.budgetTotal();
    return total > 0 ? Math.round((this.budgetSpent() / total) * 100) : 0;
  });

  statusEntries = computed(() => {
    const counts = this.dashboard()?.metrics?.expenses?.status_counts ?? {};
    const total = this.totalExpenses();
    const order = [
      'DRAFT', 'SUBMITTED', 'APPROVED', 'REJECTED',
      'NEEDS_REVISION', 'BUDGET_CONFIRMED', 'BUDGET_DENIED', 'PAID', 'PAYOUT_FAILED'
    ];
    return order
      .filter(s => (counts[s] ?? 0) > 0)
      .map(s => ({
        status: s,
        label: this.statusLabel(s),
        count: counts[s],
        percent: total > 0 ? Math.round((counts[s] / total) * 100) : 0,
        cssClass: s.toLowerCase().replace(/_/g, '-'),
      }));
  });

  topCategories = computed(() => this.dashboard()?.metrics?.expenses?.top_categories ?? []);
  reviewers = computed(() => this.dashboard()?.metrics?.approvals?.reviewers ?? []);

  constructor(private monitoringService: MonitoringService) {}

  ngOnInit(): void {
    this.loadData();
    this.refreshInterval = setInterval(() => this.loadData(), 30000);
  }

  ngOnDestroy(): void {
    if (this.refreshInterval) {
      clearInterval(this.refreshInterval);
    }
  }

  loadData(): void {
    this.monitoringService.getBusinessDashboard().subscribe({
      next: (data) => {
        this.dashboard.set(data);
        this.lastUpdated.set(new Date());
        this.loading.set(false);
        this.error.set(null);
      },
      error: (err) => {
        this.error.set('Business-Dashboard-Daten konnten nicht geladen werden.');
        this.loading.set(false);
      },
    });

    this.monitoringService.getLogs().subscribe({
      next: (data) => this.logs.set(data),
      error: () => {},
    });
  }

  refresh(): void {
    this.loading.set(true);
    this.loadData();
  }

  statusLabel(status: string): string {
    const labels: Record<string, string> = {
      DRAFT: 'Entwurf',
      SUBMITTED: 'Eingereicht',
      APPROVED: 'Genehmigt',
      REJECTED: 'Abgelehnt',
      NEEDS_REVISION: 'Überarbeitung',
      BUDGET_CONFIRMED: 'Budget bestätigt',
      BUDGET_DENIED: 'Budget abgelehnt',
      PAID: 'Ausgezahlt',
      PAYOUT_FAILED: 'Auszahlung fehlgeschl.',
    };
    return labels[status] || status;
  }

  formatCurrency(value: number, currency: string = 'EUR'): string {
    return new Intl.NumberFormat('de-DE', {
      style: 'currency',
      currency: currency,
    }).format(value);
  }

  formatTime(dateStr: string): string {
    if (!dateStr) return '—';
    const d = new Date(dateStr);
    return d.toLocaleString('de-DE', {
      day: '2-digit',
      month: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    });
  }
}
