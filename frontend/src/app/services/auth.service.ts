import { Injectable, signal, computed } from '@angular/core';
import { HttpClient, HttpHeaders, HttpErrorResponse } from '@angular/common/http';
import { Router } from '@angular/router';
import { Observable, tap, catchError, of } from 'rxjs';
import { AuthToken, UserInfo } from '../models/expense.model';

const API_URL = 'http://localhost:8000';

@Injectable({ providedIn: 'root' })
export class AuthService {
  private tokenSignal = signal<string | null>(localStorage.getItem('access_token'));
  private userSignal = signal<UserInfo | null>(this.getStoredUser());

  isAuthenticated = computed(() => !!this.tokenSignal());
  currentUser = computed(() => this.userSignal());
  token = computed(() => this.tokenSignal());

  constructor(private http: HttpClient, private router: Router) {
    // Load user info if token exists
    if (this.tokenSignal()) {
      this.loadUserInfo();
    }
  }

  login(username: string, password: string): Observable<AuthToken> {
    const body = new URLSearchParams();
    body.set('username', username);
    body.set('password', password);

    const headers = new HttpHeaders({
      'Content-Type': 'application/x-www-form-urlencoded',
    });

    return this.http.post<AuthToken>(`${API_URL}/token`, body.toString(), { headers }).pipe(
      tap((response) => {
        localStorage.setItem('access_token', response.access_token);
        this.tokenSignal.set(response.access_token);
        this.loadUserInfo();
      })
    );
  }

  register(username: string, password: string, fullName: string): Observable<any> {
    return this.http.post(`${API_URL}/register`, {
      username,
      password,
      full_name: fullName,
      role: 'user',
    });
  }

  logout(): void {
    localStorage.removeItem('access_token');
    localStorage.removeItem('user_info');
    this.tokenSignal.set(null);
    this.userSignal.set(null);
    this.router.navigate(['/login']);
  }

  getToken(): string | null {
    return this.tokenSignal();
  }

  private getStoredUser(): UserInfo | null {
    try {
      const stored = localStorage.getItem('user_info');
      return stored ? JSON.parse(stored) : null;
    } catch {
      return null;
    }
  }

  private loadUserInfo(): void {
    const token = this.tokenSignal();
    if (!token) return;

    const headers = new HttpHeaders({
      Authorization: `Bearer ${token}`,
    });

    this.http.get<UserInfo>(`${API_URL}/users/me`, { headers }).pipe(
      catchError((err: HttpErrorResponse) => {
        // Only force logout on explicit auth errors.
        // Network/server hiccups during refresh should not drop the session.
        if (err?.status === 401 || err?.status === 403) {
          this.logout();
        }
        return of(null);
      })
    ).subscribe((user) => {
      if (user) {
        localStorage.setItem('user_info', JSON.stringify(user));
        this.userSignal.set(user);
      }
    });
  }
}
