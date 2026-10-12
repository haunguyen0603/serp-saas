export const invoiceStatuses = {
  pending: "Pending payment",
  checkout_created: "Awaiting payment",
  paid: "Paid",
  failed: "Failed",
  cancelled: "Cancelled",
  voided: "Voided",
  expired: "Expired",
  review_required: "Needs review",
} as const;

export type Invoice = {
  id: string;
  invoice_number: string;
  status: keyof typeof invoiceStatuses;
  product_line: "desktop" | "mobile";
  plan_code: string;
  plan_name: string;
  amount_minor: number;
  currency: string;
  provider: string;
  provider_environment: "sandbox" | "production";
  created_at: string;
  paid_at: string | null;
};
export type InvoiceList = {
  items: Invoice[];
  next_cursor: string | null;
  has_more: boolean;
};
export type InvoiceDetail = Invoice & {
  account_email: string;
  payment_method: string | null;
  provider_order_id: string | null;
  provider_transaction_id: string | null;
  provider_transaction_uuid: string | null;
  updated_at: string;
  expires_at: string;
  cancelled_at: string | null;
  failed_at: string | null;
  terms: {
    billing_months: number | null;
    max_projects: number | null;
    max_keywords: number | null;
    monthly_keyword_checks: number | null;
    scheduled_checks_enabled: boolean | null;
    max_scheduled_frequency: string | null;
  };
};
