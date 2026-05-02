import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

const API_URL = 'http://localhost:8000/api/v1';

export interface ServiceHealth {
  service: string;
  status: 'healthy' | 'degraded' | 'unhealthy';
  response_time_ms: number;
  details: any;
}

export interface BusinessDashboard {
  timestamp: string;
  metrics: {
    expenses: any;
    approvals: any;
    budgets: any;
    payouts: any;
  };
}

export interface SystemDashboard {
  timestamp: string;
  overall_status: string;
  services: ServiceHealth[];
  system: {
    registered_users: number;
    services_count: number;
    healthy_services: number;
  };
}

export interface AuditLog {
  timestamp: string;
  service: string;
  action: string;
  details: string;
  user: string;
  currency?: string;
}

export interface MonitoringLogs {
  timestamp: string;
  total: number;
  logs: AuditLog[];
}

@Injectable({ providedIn: 'root' })
export class MonitoringService {
  constructor(private http: HttpClient) {}

  /** Fetch aggregated business monitoring data */
  getBusinessDashboard(): Observable<BusinessDashboard> {
    return this.http.get<BusinessDashboard>(`${API_URL}/monitoring/business`);
  }

  /** Fetch aggregated system monitoring data */
  getSystemDashboard(): Observable<SystemDashboard> {
    return this.http.get<SystemDashboard>(`${API_URL}/monitoring/system`);
  }

  /** Fetch recent activity logs */
  getLogs(): Observable<MonitoringLogs> {
    return this.http.get<MonitoringLogs>(`${API_URL}/monitoring/logs`);
  }
}
