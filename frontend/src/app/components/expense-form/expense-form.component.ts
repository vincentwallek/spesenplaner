import { Component, OnInit, signal } from '@angular/core';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { ExpenseService } from '../../services/expense.service';
import { ExpenseCreate } from '../../models/expense.model';

@Component({
  selector: 'app-expense-form',
  standalone: true,
  imports: [FormsModule, RouterLink],
  template: `
    <div class="animate-in">
      <div class="page-header">
        <h1>{{ isEdit() ? 'Antrag bearbeiten' : 'Neuer Spesenantrag' }}</h1>
      </div>
      <div class="glass-card form-card">
        <form (ngSubmit)="onSubmit()">
          <div class="form-group">
            <label for="title">Titel *</label>
            <input id="title" class="form-control" [(ngModel)]="form.title" name="title" placeholder="z.B. Dienstreise Berlin" required />
          </div>
          <div class="form-row">
            <div class="form-group">
              <label for="amount">Betrag (€) *</label>
              <input id="amount" class="form-control" type="number" step="0.01" min="0.01" [(ngModel)]="form.amount" name="amount" placeholder="0.00" required />
            </div>
            <div class="form-group">
              <label for="currency">Währung</label>
              <select id="currency" class="form-control" [(ngModel)]="form.currency" name="currency">
                <option value="EUR">EUR</option>
                <option value="USD">USD</option>
                <option value="CHF">CHF</option>
                <option value="GBP">GBP</option>
              </select>
            </div>
            <div class="form-group">
              <label for="category">Kategorie</label>
              <select id="category" class="form-control" [(ngModel)]="form.category" name="category">
                <option value="">— Wählen —</option>
                <option value="travel">Reise</option>
                <option value="hotel">Hotel</option>
                <option value="food">Verpflegung</option>
                <option value="transport">Transport</option>
                <option value="equipment">Ausstattung</option>
                <option value="other">Sonstiges</option>
              </select>
            </div>
          </div>
          <div class="form-group">
            <label for="description">Beschreibung</label>
            <textarea id="description" class="form-control" [(ngModel)]="form.description" name="description" placeholder="Optionale Beschreibung..." rows="3"></textarea>
          </div>
          @if (error()) {
            <div class="error-message">{{ error() }}</div>
          }
          <div class="form-actions">
            <a routerLink="/expenses" class="btn btn-secondary">Abbrechen</a>
            <button type="submit" class="btn btn-primary" [disabled]="saving()" id="btn-save-expense">
              @if (saving()) { <span class="spinner" style="width:16px;height:16px;border-width:2px"></span> }
              {{ isEdit() ? 'Speichern' : 'Erstellen' }}
            </button>
          </div>
        </form>
      </div>
    </div>
  `,
  styles: [`
    .page-header { margin-bottom:1.5rem; }
    .form-card { max-width:700px; }
    .form-row { display:grid; grid-template-columns:1fr 1fr 1fr; gap:1rem; }
    .form-actions { display:flex; gap:1rem; justify-content:flex-end; margin-top:1.5rem; }
    .error-message { padding:0.75rem; background:var(--color-danger-bg); border:1px solid rgba(239,68,68,0.3); border-radius:var(--border-radius-sm); color:var(--color-danger); font-size:0.875rem; }
  `],
})
export class ExpenseFormComponent implements OnInit {
  form: ExpenseCreate = { title: '', amount: 0, currency: 'EUR', category: '', description: '' };
  isEdit = signal(false);
  saving = signal(false);
  error = signal('');
  private editId = '';

  constructor(private svc: ExpenseService, private route: ActivatedRoute, private router: Router) {}

  ngOnInit() {
    const id = this.route.snapshot.paramMap.get('id');
    if (id) {
      this.isEdit.set(true);
      this.editId = id;
      this.svc.getExpense(id).subscribe({
        next: (e) => { this.form = { title: e.title, amount: e.amount, currency: e.currency, category: e.category || '', description: e.description || '' }; },
        error: () => this.router.navigate(['/expenses']),
      });
    }
  }

  onSubmit() {
    if (!this.form.title || !this.form.amount) { this.error.set('Titel und Betrag sind Pflichtfelder.'); return; }
    this.saving.set(true);
    this.error.set('');
    const obs = this.isEdit() ? this.svc.updateExpense(this.editId, this.form) : this.svc.createExpense(this.form);
    obs.subscribe({
      next: (e) => { this.saving.set(false); this.router.navigate(['/expenses', e.id]); },
      error: (err) => { this.saving.set(false); this.error.set(err?.error?.detail || 'Fehler beim Speichern'); },
    });
  }
}
