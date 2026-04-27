/**
 * Expense model interfaces including HATEOAS links.
 */

export interface HATEOASLink {
  href: string;
  method: string;
  rel?: string;
}

export interface Expense {
  id: string;
  title: string;
  description?: string;
  amount: number;
  currency: string;
  status: string;
  category?: string;
  manager_message?: string;
  created_by: string;
  created_at?: string;
  updated_at?: string;
  _links: { [key: string]: HATEOASLink };
}

export interface ExpenseList {
  items: Expense[];
  total: number;
  _links: { [key: string]: HATEOASLink };
}

export interface ExpenseCreate {
  title: string;
  description?: string;
  amount: number;
  currency: string;
  category?: string;
}

export interface AuthToken {
  access_token: string;
  token_type: string;
}

export interface UserInfo {
  username: string;
  role: string;
  full_name?: string;
}

export type ExpenseStatus =
  | 'DRAFT'
  | 'SUBMITTED'
  | 'APPROVED'
  | 'REJECTED'
  | 'BUDGET_CONFIRMED'
  | 'BUDGET_DENIED'
  | 'PAID'
  | 'PAYOUT_FAILED'
  | 'NEEDS_REVISION';

export const STATUS_LABELS: Record<string, string> = {
  DRAFT: 'Entwurf',
  SUBMITTED: 'Eingereicht',
  APPROVED: 'Genehmigt',
  REJECTED: 'Abgelehnt',
  BUDGET_CONFIRMED: 'Budget bestätigt',
  BUDGET_DENIED: 'Budget abgelehnt',
  PAID: 'Ausgezahlt',
  PAYOUT_FAILED: 'Auszahlung fehlgeschlagen',
  NEEDS_REVISION: 'Überarbeitung erforderlich',
};

export const STATUS_CSS: Record<string, string> = {
  DRAFT: 'badge-draft',
  SUBMITTED: 'badge-submitted',
  APPROVED: 'badge-approved',
  REJECTED: 'badge-rejected',
  BUDGET_CONFIRMED: 'badge-budget-confirmed',
  BUDGET_DENIED: 'badge-budget-denied',
  PAID: 'badge-paid',
  PAYOUT_FAILED: 'badge-payout-failed',
  NEEDS_REVISION: 'badge-needs-revision',
};
