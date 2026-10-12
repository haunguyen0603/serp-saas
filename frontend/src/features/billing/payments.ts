export interface Checkout {
  payment_order_id: string;
  invoice_number: string;
  checkout_url: string;
  form: Record<string, string>;
}
export interface PaymentOptions {
  enabled: boolean;
  eligible_plan_ids: string[];
}
export interface PaymentStatus {
  id: string;
  invoice_number: string;
  status: string;
  product_line: string;
  plan_code: string;
  plan_name_snapshot: string;
  amount_minor: number;
  currency: string;
  paid_at: string | null;
  subscription_id: string | null;
}
export function submitCheckout(checkout: Checkout) {
  const form = document.createElement("form");
  form.method = "POST";
  form.action = checkout.checkout_url;
  form.hidden = true;
  for (const [name, value] of Object.entries(checkout.form)) {
    const input = document.createElement("input");
    input.type = "hidden";
    input.name = name;
    input.value = value;
    form.appendChild(input);
  }
  document.body.appendChild(form);
  try {
    form.submit();
  } finally {
    form.remove();
  }
}
