import { Component, OnInit, OnDestroy, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MonitoringService, SystemDashboard } from '../../services/monitoring.service';

@Component({
  selector: 'app-system-monitoring',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './system-monitoring.component.html',
  styleUrl: './system-monitoring.component.css',
})
export class SystemMonitoringComponent implements OnInit, OnDestroy {
  dashboard = signal<SystemDashboard | null>(null);
  loading = signal(true);
  error = signal<string | null>(null);
  lastUpdated = signal<Date | null>(null);

  private refreshInterval: any;

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
    this.monitoringService.getSystemDashboard().subscribe({
      next: (data) => {
        this.dashboard.set(data);
        this.lastUpdated.set(new Date());
        this.loading.set(false);
        this.error.set(null);
      },
      error: (err) => {
        this.error.set('System-Dashboard-Daten konnten nicht geladen werden.');
        this.loading.set(false);
      },
    });
  }

  refresh(): void {
    this.loading.set(true);
    this.loadData();
  }
}
