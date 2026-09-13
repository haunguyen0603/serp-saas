export interface Plan {
  id?: string;
  code: string;
  name: string;
  device_scope: "desktop" | "mobile";
  price_monthly_minor_units: number;
  currency: string;
  max_projects: number;
  max_keywords: number;
  monthly_keyword_checks: number;
  scheduled_checks_enabled: boolean;
  max_scheduled_frequency: string;
}
export interface DeviceBilling {
  device_scope: "desktop" | "mobile";
  subscription_id: string;
  plan: Plan;
  status: string;
  period_start: string;
  period_end: string | null;
  projects_used: number;
  keywords_used: number;
  over_limit: boolean;
  usage: {
    id: string;
    period_start: string;
    period_end: string;
    limit: number;
    used: number;
    reserved: number;
    remaining: number;
    adjustment: number;
  };
}
export interface BillingSummary {
  user_id: string;
  email: string;
  account_status: string;
  devices: DeviceBilling[];
}
export interface Subscription {
  id: string;
  device_scope: string;
  status: string;
  source: string;
  period_start: string;
  period_end: string;
  snapshot: Plan;
  payment_method: string | null;
  payment_reference: string | null;
  payment_note: string | null;
  activated_by_user_id: string | null;
}
export interface UsageHistory {
  events: {
    id: string;
    device_scope: string;
    event_type: string;
    amount: number;
    created_at: string;
  }[];
  audit: {
    id: string;
    device_scope: string;
    event_type: string;
    actor_user_id: string | null;
    created_at: string;
    safe_metadata: Record<string, unknown>;
  }[];
}
