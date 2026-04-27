import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { Expense, ExpenseList, ExpenseCreate } from '../models/expense.model';
import { AuthService } from './auth.service';

const API_URL = 'http://localhost:8000/api/v1';

@Injectable({ providedIn: 'root' })
export class ExpenseService {
  constructor(private http: HttpClient, private auth: AuthService) {}

  /** Get all expenses */
  getExpenses(statusFilter?: string): Observable<ExpenseList> {
    let url = `${API_URL}/expenses`;
    if (statusFilter) {
      url += `?status_filter=${statusFilter}`;
    }
    return this.http.get<ExpenseList>(url);
  }

  /** Get a single expense by ID */
  getExpense(id: string): Observable<Expense> {
    return this.http.get<Expense>(`${API_URL}/expenses/${id}`);
  }

  /** Create a new expense */
  createExpense(data: ExpenseCreate): Observable<Expense> {
    return this.http.post<Expense>(`${API_URL}/expenses`, data);
  }

  /** Update an existing expense */
  updateExpense(id: string, data: Partial<ExpenseCreate>): Observable<Expense> {
    return this.http.put<Expense>(`${API_URL}/expenses/${id}`, data);
  }

  /** Delete an expense */
  deleteExpense(id: string): Observable<void> {
    return this.http.delete<void>(`${API_URL}/expenses/${id}`);
  }

  /** Submit an expense for approval */
  submitExpense(id: string): Observable<Expense> {
    return this.http.post<Expense>(`${API_URL}/expenses/${id}/submit`, {});
  }

  /** Cancel a submitted expense */
  cancelExpense(id: string): Observable<Expense> {
    return this.http.post<Expense>(`${API_URL}/expenses/${id}/cancel`, {});
  }

  /** Get approval record for an expense */
  getApprovalForExpense(expenseId: string): Observable<any> {
    return this.http.get<any>(`${API_URL}/approvals/expense/${expenseId}`);
  }

  /** Approve an approval record */
  approveExpense(recordId: string, reason?: string): Observable<any> {
    return this.http.post<any>(`${API_URL}/approvals/${recordId}/approve`, {
      reason: reason || 'Freigegeben durch Manager',
    });
  }

  /** Reject an approval record */
  rejectExpense(recordId: string, reason?: string): Observable<any> {
    return this.http.post<any>(`${API_URL}/approvals/${recordId}/reject`, {
      reason: reason || 'Abgelehnt durch Manager',
    });
  }

  /** Request revision for an approval record */
  requestRevisionExpense(recordId: string, reason?: string): Observable<any> {
    return this.http.post<any>(`${API_URL}/approvals/${recordId}/request_revision`, {
      reason: reason || 'Überarbeitung angefordert',
    });
  }

  /** Get budget check by expense id */
  getBudgetCheckForExpense(expenseId: string): Observable<any> {
    return this.http.get<any>(`${API_URL}/budgets/expense/${expenseId}`);
  }

  /** Send a manager message for an expense (e.g. budget denial info) */
  sendManagerMessage(expenseId: string, message: string): Observable<Expense> {
    return this.http.put<Expense>(`${API_URL}/expenses/${expenseId}/message`, { message });
  }

  /**
   * Follow a HATEOAS link.
   * This is the key method for navigating the API via hypermedia.
   */
  followLink(href: string, method: string, body?: any): Observable<any> {
    const url = href.startsWith('http') ? href : `http://localhost:8000${href}`;
    switch (method.toUpperCase()) {
      case 'GET':
        return this.http.get(url);
      case 'POST':
        return this.http.post(url, body || {});
      case 'PUT':
        return this.http.put(url, body || {});
      case 'DELETE':
        return this.http.delete(url);
      default:
        return this.http.get(url);
    }
  }
}
