import { Component, OnInit, signal } from '@angular/core';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { ExpenseService } from '../../services/expense.service';
import { Expense, STATUS_LABELS, STATUS_CSS, HATEOASLink } from '../../models/expense.model';
import { DatePipe, DecimalPipe, KeyValuePipe } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { AuthService } from '../../services/auth.service';

@Component({
  selector: 'app-expense-detail',
  standalone: true,
  imports: [RouterLink, DatePipe, DecimalPipe, KeyValuePipe, FormsModule],
  template: `
    <div class="animate-in">
      @if (loading()) {
        <div class="loading-overlay"><div class="spinner"></div><span>Lade...</span></div>
      } @else if (expense()) {
        <div class="page-header">
          <div>
            <a routerLink="/expenses" class="back-link text-secondary text-sm">← Zurück zur Liste</a>
            <h1>{{ expense()!.title }}</h1>
          </div>
          <span class="badge badge-lg" [class]="getCss(expense()!.status)">
            {{ getLabel(expense()!.status) }}
          </span>
        </div>

        <div class="detail-grid">
          <!-- Info Card -->
          <div class="glass-card">
            <h3 class="mb-2">Details</h3>
            <div class="info-grid">
              <div class="info-item">
                <span class="info-label">Betrag</span>
                <span class="info-value amount">{{ expense()!.amount | number:'1.2-2' }} {{ expense()!.currency }}</span>
              </div>
              <div class="info-item">
                <span class="info-label">Kategorie</span>
                <span class="info-value">{{ expense()!.category || '—' }}</span>
              </div>
              <div class="info-item">
                <span class="info-label">Erstellt von</span>
                <span class="info-value">{{ expense()!.created_by }}</span>
              </div>
              <div class="info-item">
                <span class="info-label">Erstellt am</span>
                <span class="info-value">{{ expense()!.created_at | date:'dd.MM.yyyy HH:mm' }}</span>
              </div>
              <div class="info-item">
                <span class="info-label">Zuletzt aktualisiert</span>
                <span class="info-value">{{ expense()!.updated_at | date:'dd.MM.yyyy HH:mm' }}</span>
              </div>
              @if (approvalDecisionBy()) {
                <div class="info-item">
                  <span class="info-label">Entschieden von</span>
                  <span class="info-value">{{ approvalDecisionBy() }}</span>
                </div>
              }
              @if (approvalDecisionAt()) {
                <div class="info-item">
                  <span class="info-label">Entscheidung am</span>
                  <span class="info-value">{{ approvalDecisionAt() | date:'dd.MM.yyyy HH:mm' }}</span>
                </div>
              }
            </div>
            @if (expense()!.description) {
              <div class="mt-2">
                <span class="info-label">Beschreibung</span>
                <p class="mt-1">{{ expense()!.description }}</p>
              </div>
            }
            @if (approvalReason()) {
              <div class="mt-2 status-note" [class.status-note-warning]="expense()!.status === 'NEEDS_REVISION'" [class.status-note-danger]="expense()!.status === 'REJECTED'">
                <span class="info-label">Begründung / Feedback</span>
                <p class="mt-1 font-semibold">{{ approvalReason() }}</p>
              </div>
            }
            @if (expense()!.manager_message && isCreator()) {
              <div class="mt-2 status-note status-note-info">
                <span class="info-label">📩 Nachricht vom Manager</span>
                <p class="mt-1 font-semibold">{{ expense()!.manager_message }}</p>
              </div>
            }
          </div>

          <!-- Actions Card (HATEOAS) -->
          <div class="glass-card">
            <h3 class="mb-2">Aktionen</h3>
            @if (canManageApproval() && expense()!.status === 'SUBMITTED') {
              <div class="status-note status-note-info">
                Du kannst diesen Antrag jetzt prüfen und entscheiden.
              </div>
            }
            @if (!canManageApproval() && expense()!.status === 'SUBMITTED') {
              <div class="status-note status-note-info">
                Wartet auf Freigabe durch einen Manager.
              </div>
            }
            @if (expense()!.status === 'APPROVED') {
              <div class="status-note status-note-info">
                Budgetprüfung läuft oder ist als nächster Schritt fällig.
              </div>
            } @else if (expense()!.status === 'BUDGET_CONFIRMED') {
              <div class="status-note status-note-success">
                Budgetprüfung erfolgreich abgeschlossen. Auszahlung wurde angestoßen.
              </div>
            } @else if (expense()!.status === 'BUDGET_DENIED') {
              <div class="status-note status-note-warning">
                Budgetprüfung abgeschlossen: nicht ausreichend Budget verfügbar.
              </div>
              @if (canManageApproval() || auth.currentUser()?.role === 'manager' || auth.currentUser()?.role === 'admin') {
                <div class="manager-message-box">
                  <span class="info-label">📩 Nachricht an {{ expense()!.created_by }} verfassen</span>
                  <textarea class="form-control mt-1" [ngModel]="managerMessage()" (ngModelChange)="managerMessage.set($event)" rows="3" placeholder="Nachricht eingeben..."></textarea>
                  <button class="btn btn-warning w-full mt-1" (click)="sendMessage()" [disabled]="actionLoading() || !managerMessage()">
                    Nachricht senden
                  </button>
                </div>
              }
            }
            <p class="text-sm text-muted mb-2">Verfügbare Aktionen basierend auf dem aktuellen Status:</p>
            <div class="actions-list">
              @if (canManageApproval() && expense()!.status === 'SUBMITTED') {
                <div class="form-group mb-2">
                  <label for="decisionReason">Begründung / Feedback (optional)</label>
                  <textarea id="decisionReason" class="form-control" [ngModel]="decisionReason()" (ngModelChange)="decisionReason.set($event)" placeholder="Warum wird abgelehnt oder eine Überarbeitung gefordert?"></textarea>
                </div>
                <button class="btn btn-success w-full" (click)="approveByManager()" [disabled]="actionLoading() || !approvalRecordId()">
                  Genehmigen
                </button>
                <div class="info-grid mt-1">
                  <button class="btn btn-warning w-full" (click)="requestRevisionByManager()" [disabled]="actionLoading() || !approvalRecordId()" style="background-color: #ea580c; color: white;">
                    Überarbeitung anfordern
                  </button>
                  <button class="btn btn-danger w-full" (click)="rejectByManager()" [disabled]="actionLoading() || !approvalRecordId()">
                    Ablehnen
                  </button>
                </div>
              }
              @if (expense()!._links['update'] && isCreator()) {
                @if (expense()!.status === 'NEEDS_REVISION') {
                  <div class="revision-hint">
                    <span>⚠️ Bitte überarbeite den Antrag bevor du ihn erneut einreichst.</span>
                  </div>
                  <a [routerLink]="['/expenses', expense()!.id, 'edit']" class="btn btn-revision-warning w-full" id="btn-edit">
                    ⚠ Jetzt überarbeiten
                  </a>
                } @else {
                  <a [routerLink]="['/expenses', expense()!.id, 'edit']" class="btn btn-secondary w-full" id="btn-edit">Bearbeiten</a>
                }
              }
              @if (expense()!._links['submit'] && isCreator() && expense()!.status !== 'NEEDS_REVISION') {
                <button class="btn btn-primary w-full" (click)="submitExpense()" [disabled]="actionLoading()" id="btn-submit">Einreichen</button>
              }
              @if (expense()!._links['cancel'] && isCreator()) {
                <button class="btn btn-secondary w-full" (click)="cancelExpense()" [disabled]="actionLoading()" id="btn-cancel">Zurückziehen</button>
              }
              @if (expense()!._links['delete']) {
                <button class="btn btn-danger w-full" (click)="deleteExpense()" [disabled]="actionLoading()" id="btn-delete">Löschen</button>
              }
              @if (expense()!._links['resubmit']) {
                <a [routerLink]="['/expenses', expense()!.id, 'edit']" class="btn btn-primary w-full">Überarbeiten und erneut einreichen</a>
              }
            </div>
          </div>
        </div>

        <!-- Status Timeline -->
        <div class="glass-card mt-3">
          <h3 class="mb-2">Status-Verlauf</h3>
          <div class="timeline">
            @for (step of getStatusSteps(); track step.key) {
              <div class="timeline-step" [class.active]="isStepActive(step.key)" [class.current]="isStepCurrent(step.key)" [class.failed]="isStepFailed(step.key)" [class.warning]="isStepWarning(step.key)">
                <div class="step-dot"></div>
                <div class="step-content">
                  <span class="step-label">{{ step.label }}</span>
                  <span class="step-desc text-sm text-muted">{{ step.desc }}</span>
                </div>
              </div>
            }
          </div>
        </div>

        @if (actionMsg()) {
          <div class="toast toast-info">{{ actionMsg() }}</div>
        }


      }
    </div>
  `,
  styles: [`
    .page-header { display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:2rem; }
    .back-link { display:block; margin-bottom:0.5rem; }
    .badge-lg { font-size:0.875rem; padding:0.375rem 1rem; }
    .detail-grid { display:grid; grid-template-columns:1.5fr 1fr; gap:1.5rem; }
    .info-grid { display:grid; grid-template-columns:1fr 1fr; gap:1rem; }
    .info-item { display:flex; flex-direction:column; gap:0.25rem; }
    .info-label { font-size:0.75rem; font-weight:600; text-transform:uppercase; letter-spacing:0.05em; color:var(--color-text-muted); }
    .info-value { font-size:1rem; color:var(--color-text-primary); }
    .amount { font-size:1.25rem; font-weight:700; color:var(--color-accent-secondary); }
    .actions-list { display:flex; flex-direction:column; gap:0.5rem; }
    .status-note { padding:0.75rem; border-radius:var(--border-radius-sm); margin-bottom:0.75rem; font-size:0.875rem; border:1px solid transparent; }
    .status-note-info { background:var(--color-info-bg); color:var(--color-info); border-color:rgba(59,130,246,0.35); }
    .status-note-success { background:var(--color-success-bg); color:var(--color-success); border-color:rgba(16,185,129,0.35); }
    .status-note-warning { background:var(--color-warning-bg); color:var(--color-warning); border-color:rgba(245,158,11,0.35); }
    .status-note-danger { background:var(--color-danger-bg); color:var(--color-danger); border-color:rgba(239,68,68,0.35); }
    .links-section { padding-top:1rem; border-top:1px solid var(--color-border-glass); }
    .links-grid { display:flex; flex-direction:column; gap:0.5rem; }
    .link-item { display:flex; align-items:center; gap:0.75rem; }
    .link-rel { font-size:0.75rem; background:rgba(99,102,241,0.1); color:var(--color-accent-secondary); padding:0.125rem 0.5rem; border-radius:4px; }
    .timeline { display:flex; gap:0; overflow-x:auto; padding:1rem 0; }
    .timeline-step { display:flex; flex-direction:column; align-items:center; flex:1; min-width:100px; position:relative; }
    .timeline-step::after { content:''; position:absolute; top:12px; left:50%; width:100%; height:2px; background:rgba(255,255,255,0.06); z-index:0; }
    .timeline-step:last-child::after { display:none; }
    .step-dot { width:24px; height:24px; border-radius:50%; background:rgba(255,255,255,0.06); border:2px solid rgba(255,255,255,0.1); z-index:1; margin-bottom:0.5rem; transition:var(--transition); }
    .timeline-step.active .step-dot { background:var(--color-accent-primary); border-color:var(--color-accent-primary); box-shadow:0 0 12px var(--color-accent-glow); }
    .timeline-step.current .step-dot { background:var(--color-success); border-color:var(--color-success); box-shadow:0 0 12px rgba(16,185,129,0.4); animation:pulse 2s infinite; }
    .timeline-step.failed .step-dot { background:var(--color-danger); border-color:var(--color-danger); box-shadow:0 0 12px rgba(239,68,68,0.4); animation:pulse-failed 2s infinite; }
    .timeline-step.warning .step-dot { background:#eab308; border-color:#eab308; box-shadow:0 0 12px rgba(234,179,8,0.4); animation:pulse-warning 2s infinite; }
    @keyframes pulse { 0%,100%{box-shadow:0 0 12px rgba(16,185,129,0.4)} 50%{box-shadow:0 0 24px rgba(16,185,129,0.6)} }
    @keyframes pulse-failed { 0%,100%{box-shadow:0 0 12px rgba(239,68,68,0.4)} 50%{box-shadow:0 0 24px rgba(239,68,68,0.6)} }
    @keyframes pulse-warning { 0%,100%{box-shadow:0 0 12px rgba(234,179,8,0.4)} 50%{box-shadow:0 0 24px rgba(234,179,8,0.6)} }
    .step-content { text-align:center; }
    .step-label { font-size:0.75rem; font-weight:600; display:block; }
    .step-desc { font-size:0.625rem; display:block; }
    /* Fix #3: Pulsing revision warning button */
    .btn-revision-warning {
      background: linear-gradient(135deg, #f97316, #ea580c);
      color: white;
      font-weight: 700;
      border: 2px solid #c2410c;
      animation: pulse-btn 1.5s ease-in-out infinite;
      box-shadow: 0 0 16px rgba(249, 115, 22, 0.4);
      text-align: center;
      text-decoration: none;
    }
    .btn-revision-warning:hover {
      background: linear-gradient(135deg, #ea580c, #c2410c);
      box-shadow: 0 0 24px rgba(249, 115, 22, 0.6);
      transform: translateY(-1px);
    }
    @keyframes pulse-btn {
      0%, 100% { box-shadow: 0 0 12px rgba(249, 115, 22, 0.3); }
      50% { box-shadow: 0 0 24px rgba(249, 115, 22, 0.6); }
    }
    .revision-hint {
      padding: 0.625rem 0.75rem;
      background: rgba(249, 115, 22, 0.1);
      border: 1px solid rgba(249, 115, 22, 0.3);
      border-radius: var(--border-radius-sm);
      color: #ea580c;
      font-size: 0.8125rem;
      font-weight: 500;
      margin-bottom: 0.5rem;
    }
    /* Fix #4: Manager message box */
    .manager-message-box {
      padding: 0.75rem;
      background: rgba(245, 158, 11, 0.05);
      border: 1px solid rgba(245, 158, 11, 0.2);
      border-radius: var(--border-radius-sm);
      margin-top: 0.5rem;
    }
  `],
})
export class ExpenseDetailComponent implements OnInit {
  expense = signal<Expense | null>(null);
  loading = signal(true);
  actionLoading = signal(false);
  actionMsg = signal('');
  approvalRecordId = signal('');
  approvalDecisionBy = signal('');
  approvalDecisionAt = signal('');
  approvalReason = signal('');
  decisionReason = signal('');
  managerMessage = signal('');

  baseStatusSteps = [
    { key: 'DRAFT', label: 'Entwurf', desc: 'Erstellt' },
    { key: 'SUBMITTED', label: 'Eingereicht', desc: 'Zur Prüfung' },
    { key: 'APPROVED', label: 'Genehmigt', desc: 'Akzeptiert' },
    { key: 'BUDGET_CONFIRMED', label: 'Budget OK', desc: 'Gedeckt' },
    { key: 'PAID', label: 'Ausgezahlt', desc: 'Erledigt' },
  ];

  private baseStatusOrder = ['DRAFT','SUBMITTED','APPROVED','BUDGET_CONFIRMED','PAID'];

  getStatusSteps() {
    const e = this.expense();
    if (!e) return this.baseStatusSteps;
    const steps = [...this.baseStatusSteps];
    if (e.status === 'REJECTED') {
      steps[2] = { key: 'REJECTED', label: 'Abgelehnt', desc: 'Abgelehnt' };
    } else if (e.status === 'BUDGET_DENIED') {
      steps[3] = { key: 'BUDGET_DENIED', label: 'Budget fehlt', desc: 'Kein Budget' };
    } else if (e.status === 'PAYOUT_FAILED') {
      steps[4] = { key: 'PAYOUT_FAILED', label: 'Fehler', desc: 'Zahlung fehlgeschlagen' };
    }
    return steps;
  }

  getStatusOrder() {
    const e = this.expense();
    if (!e) return this.baseStatusOrder;
    const order = [...this.baseStatusOrder];
    if (e.status === 'REJECTED') order[2] = 'REJECTED';
    else if (e.status === 'BUDGET_DENIED') order[3] = 'BUDGET_DENIED';
    else if (e.status === 'PAYOUT_FAILED') order[4] = 'PAYOUT_FAILED';
    return order;
  }

  constructor(
    private svc: ExpenseService,
    private route: ActivatedRoute,
    private router: Router,
    public auth: AuthService
  ) {}

  isCreator(): boolean {
    const e = this.expense();
    return !!e && e.created_by === this.auth.currentUser()?.username;
  }

  ngOnInit() {
    const id = this.route.snapshot.paramMap.get('id');
    if (id) {
      this.svc.getExpense(id).subscribe({
        next: (e) => {
          this.expense.set(e);
          this.loading.set(false);
          this.loadApprovalContext();
          this.prepareManagerMessage();
        },
        error: () => this.router.navigate(['/expenses']),
      });
    }
  }

  isStepActive(step: string): boolean {
    const e = this.expense();
    if (!e) return false;
    const order = this.getStatusOrder();
    const currentStatus = e.status === 'NEEDS_REVISION' ? 'SUBMITTED' : e.status;
    const ci = order.indexOf(currentStatus);
    const si = order.indexOf(step);
    if (ci === -1 || si === -1) return false;
    return si <= ci;
  }

  isStepCurrent(step: string): boolean {
    const e = this.expense();
    if (!e) return false;
    if (e.status === 'NEEDS_REVISION') return false; // Needs revision uses warning styling instead
    return e.status === step;
  }

  isStepWarning(step: string): boolean {
    const e = this.expense();
    if (!e) return false;
    return e.status === 'NEEDS_REVISION' && step === 'SUBMITTED';
  }

  isStepFailed(step: string): boolean {
    const e = this.expense();
    if (!e) return false;
    if (e.status !== step) return false;
    return ['REJECTED', 'BUDGET_DENIED', 'PAYOUT_FAILED'].includes(e.status);
  }

  submitExpense() {
    const e = this.expense();
    if (!e) return;
    this.actionLoading.set(true);
    this.svc.submitExpense(e.id).subscribe({
      next: (u) => { this.expense.set(u); this.actionLoading.set(false); this.showMsg('Antrag eingereicht!'); },
      error: () => { this.actionLoading.set(false); this.showMsg('Fehler beim Einreichen'); },
    });
  }

  cancelExpense() {
    const e = this.expense();
    if (!e) return;
    this.actionLoading.set(true);
    this.svc.cancelExpense(e.id).subscribe({
      next: (u) => { this.expense.set(u); this.actionLoading.set(false); this.showMsg('Antrag zurückgezogen'); },
      error: () => { this.actionLoading.set(false); },
    });
  }

  deleteExpense() {
    const e = this.expense();
    if (!e) return;
    if (!confirm('Antrag wirklich löschen?')) return;
    this.svc.deleteExpense(e.id).subscribe({
      next: () => this.router.navigate(['/expenses']),
      error: () => this.showMsg('Fehler beim Löschen'),
    });
  }

  getLabel(s: string) { return STATUS_LABELS[s] || s; }
  getCss(s: string) { return STATUS_CSS[s] || 'badge-draft'; }

  canManageApproval(): boolean {
    const currentUser = this.auth.currentUser();
    const role = (currentUser?.role || '').toLowerCase();
    
    // Cannot approve own expenses
    if (this.expense()?.created_by === currentUser?.username) {
      return false;
    }
    
    return role === 'manager';
  }

  approveByManager() {
    const recordId = this.approvalRecordId();
    if (!recordId) return;
    this.actionLoading.set(true);
    this.svc.approveExpense(recordId).subscribe({
      next: () => this.reloadExpenseWithMessage('Antrag genehmigt. Budgetprüfung wurde angestoßen.'),
      error: () => {
        this.actionLoading.set(false);
        this.showMsg('Genehmigung fehlgeschlagen');
      },
    });
  }

  rejectByManager() {
    const recordId = this.approvalRecordId();
    if (!recordId) return;
    this.actionLoading.set(true);
    this.svc.rejectExpense(recordId, this.decisionReason()).subscribe({
      next: () => this.reloadExpenseWithMessage('Antrag abgelehnt.'),
      error: () => {
        this.actionLoading.set(false);
        this.showMsg('Ablehnung fehlgeschlagen');
      },
    });
  }

  requestRevisionByManager() {
    const recordId = this.approvalRecordId();
    if (!recordId) return;
    this.actionLoading.set(true);
    this.svc.requestRevisionExpense(recordId, this.decisionReason()).subscribe({
      next: () => this.reloadExpenseWithMessage('Überarbeitung angefordert.'),
      error: () => {
        this.actionLoading.set(false);
        this.showMsg('Anforderung fehlgeschlagen');
      },
    });
  }

  private loadApprovalContext() {
    const e = this.expense();
    if (!e) return;
    this.svc.getApprovalForExpense(e.id).subscribe({
      next: (record) => {
        this.approvalRecordId.set(record?.id || '');
        this.approvalDecisionBy.set(record?.decided_by || '');
        this.approvalDecisionAt.set(record?.decided_at || '');
        this.approvalReason.set(record?.reason || '');
      },
      error: () => {
        this.approvalRecordId.set('');
        this.approvalDecisionBy.set('');
        this.approvalDecisionAt.set('');
        this.approvalReason.set('');
      },
    });
  }

  private reloadExpenseWithMessage(msg: string) {
    const e = this.expense();
    if (!e) {
      this.actionLoading.set(false);
      return;
    }
    this.svc.getExpense(e.id).subscribe({
      next: (updated) => {
        this.expense.set(updated);
        this.actionLoading.set(false);
        this.loadApprovalContext();
        this.showMsg(msg);
      },
      error: () => {
        this.actionLoading.set(false);
        this.showMsg('Aktualisierung fehlgeschlagen');
      },
    });
  }

  private showMsg(msg: string) {
    this.actionMsg.set(msg);
    setTimeout(() => this.actionMsg.set(''), 4000);
  }

  /** Pre-fill manager message template for BUDGET_DENIED expenses */
  private prepareManagerMessage() {
    const e = this.expense();
    if (!e || e.status !== 'BUDGET_DENIED') return;
    if (e.manager_message) {
      // Already sent — show existing message
      this.managerMessage.set(e.manager_message);
      return;
    }
    // Pre-fill template
    this.managerMessage.set(
      `Sehr geehrte/r ${e.created_by},\n\nleider wurde Ihr Antrag "${e.title}" über ${e.amount.toFixed(2)} ${e.currency} abgelehnt, da das verfügbare Budget nicht ausreicht.\n\nBitte wenden Sie sich bei Fragen an Ihren Vorgesetzten.\n\nMit freundlichen Grüßen`
    );
  }

  /** Send the manager message to the expense creator */
  sendMessage() {
    const e = this.expense();
    const msg = this.managerMessage();
    if (!e || !msg) return;
    this.actionLoading.set(true);
    this.svc.sendManagerMessage(e.id, msg).subscribe({
      next: (updated) => {
        this.expense.set(updated);
        this.actionLoading.set(false);
        this.showMsg('Nachricht wurde gesendet.');
      },
      error: () => {
        this.actionLoading.set(false);
        this.showMsg('Nachricht konnte nicht gesendet werden.');
      },
    });
  }
}
