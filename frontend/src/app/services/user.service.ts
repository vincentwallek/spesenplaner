import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { UserInfo } from '../models/expense.model';

const API_URL = 'http://localhost:8000';

@Injectable({ providedIn: 'root' })
export class UserService {
  constructor(private http: HttpClient) {}

  /** Get all users */
  getUsers(): Observable<UserInfo[]> {
    return this.http.get<UserInfo[]>(`${API_URL}/users`);
  }

  /** Update user role */
  updateUserRole(username: string, role: string): Observable<UserInfo> {
    return this.http.patch<UserInfo>(`${API_URL}/users/${username}/role`, { role });
  }
}
