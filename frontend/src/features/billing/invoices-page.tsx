"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState, type ReactNode } from "react";
import { useInfiniteQuery, useQuery } from "@tanstack/react-query";
import {
  Alert,
  Badge,
  Button,
  Card,
  CursorPagination,
  EmptyState,
  ErrorState,
  FormField,
  PageHeader,
  Select,
  Skeleton,
  Table,
} from "@/design-system/ui";
import {
  ProtectedStatus,
  useProtectedAuth,
} from "@/features/projects/protected";
import { formatPlanMoney } from "./money";
import {
  invoiceStatuses,
  type Invoice,
  type InvoiceDetail,
  type InvoiceList,
} from "./invoices";

const base = "/api/v1/billing/invoices";
const invoiceDate = (value: string | null) =>
  value ? new Date(value).toLocaleString() : "—";
const invoiceMoney = (invoice: Invoice) =>
  formatPlanMoney(
    {
      currency: invoice.currency,
      price_monthly_minor_units: invoice.amount_minor,
    },
    true,
  );

function useInvoiceAuth() {
  const auth = useProtectedAuth();
  const router = useRouter();
  const verified = auth.isAuthenticated && auth.user?.email_verified === true;
  useEffect(() => {
    if (auth.isAuthenticated && !verified) router.replace("/verify-email");
  }, [auth.isAuthenticated, verified, router]);
  return { auth, verified };
}

function InvoiceAccess({
  auth,
  verified,
  children,
}: ReturnType<typeof useInvoiceAuth> & { children: ReactNode }) {
  if (!auth.isAuthenticated)
    return (
      <ProtectedStatus
        status={auth.status === "authenticated" ? "loading" : auth.status}
        error={auth.error}
        retry={() => void auth.refresh().catch(() => {})}
      />
    );
  if (!verified)
    return (
      <main>
        <p role="status">Redirecting to email verification…</p>
      </main>
    );
  return children;
}

function InvoiceStatus({ invoice }: { invoice: Invoice }) {
  const tone =
    invoice.status === "paid"
      ? "success"
      : ["failed", "voided"].includes(invoice.status)
        ? "danger"
        : invoice.status === "review_required"
          ? "warning"
          : "neutral";
  return <Badge tone={tone}>{invoiceStatuses[invoice.status]}</Badge>;
}

function ExportInvoice({ invoice }: { invoice: Invoice }) {
  const { auth, verified } = useInvoiceAuth();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  async function download() {
    if (loading || !verified) return;
    setLoading(true);
    setError(null);
    try {
      const file = await auth.download(
        `${base}/${encodeURIComponent(invoice.id)}/pdf`,
      );
      const url = URL.createObjectURL(file.blob);
      try {
        const anchor = document.createElement("a");
        anchor.href = url;
        anchor.download =
          file.filename === "report"
            ? `invoice-${invoice.invoice_number}.pdf`
            : file.filename;
        document.body.append(anchor);
        try {
          anchor.click();
        } finally {
          anchor.remove();
        }
      } finally {
        URL.revokeObjectURL(url);
      }
    } catch (cause) {
      setError(
        cause instanceof Error
          ? cause.message
          : "Unable to export invoice. Please try again.",
      );
    } finally {
      setLoading(false);
    }
  }
  return (
    <div className="space-y-2">
      <Button
        size="sm"
        loading={loading}
        disabled={!verified}
        onClick={() => void download()}
        aria-label={`Download PDF for ${invoice.invoice_number}`}
      >
        Download PDF
      </Button>
      {error && <Alert>{error}</Alert>}
    </div>
  );
}

export function InvoicesPage() {
  const access = useInvoiceAuth();
  const { auth, verified } = access;
  const [status, setStatus] = useState("");
  const [product, setProduct] = useState("");
  const [environment, setEnvironment] = useState("");
  const invoices = useInfiniteQuery({
    queryKey: ["invoices", auth.user?.id, status, product, environment],
    initialPageParam: null as string | null,
    queryFn: ({ pageParam }) => {
      const params = new URLSearchParams({ limit: "20" });
      if (status) params.set("status", status);
      if (product) params.set("product_line", product);
      if (environment) params.set("environment", environment);
      if (pageParam) params.set("cursor", pageParam);
      return auth.request<InvoiceList>(`${base}?${params}`);
    },
    getNextPageParam: (page) => (page.has_more ? page.next_cursor : null),
    enabled: verified,
    retry: false,
  });
  const items = invoices.data?.pages.flatMap((page) => page.items) ?? [];
  return (
    <InvoiceAccess {...access}>
      <main className="space-y-6">
        <PageHeader
          title="Invoices"
          description="Track your transactions and download their details as PDF."
          actions={
            <Button
              onClick={() => void invoices.refetch()}
              loading={invoices.isRefetching}
            >
              Refresh
            </Button>
          }
        />
        <Card>
          <div className="grid gap-4 md:grid-cols-3">
            <FormField label="Payment status">
              <Select
                value={status}
                onChange={(e) => setStatus(e.target.value)}
              >
                <option value="">All statuses</option>
                {Object.entries(invoiceStatuses).map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </Select>
            </FormField>
            <FormField label="Product line">
              <Select
                value={product}
                onChange={(e) => setProduct(e.target.value)}
              >
                <option value="">All products</option>
                <option value="desktop">Desktop</option>
                <option value="mobile">Mobile</option>
              </Select>
            </FormField>
            <FormField label="Environment">
              <Select
                value={environment}
                onChange={(e) => setEnvironment(e.target.value)}
              >
                <option value="">All environments</option>
                <option value="production">Production</option>
                <option value="sandbox">Sandbox</option>
              </Select>
            </FormField>
          </div>
        </Card>
        {invoices.isPending ? (
          <Skeleton label="Loading invoices…" />
        ) : invoices.isError ? (
          <ErrorState
            title="Unable to load invoices."
            onRetry={() => void invoices.refetch()}
          >
            {invoices.error.message}
          </ErrorState>
        ) : items.length === 0 ? (
          <EmptyState title="No invoices found">
            {status || product || environment
              ? "Try another filter to find your transactions."
              : "Your transactions will appear here after you start a checkout."}
          </EmptyState>
        ) : (
          <Card>
            <Table>
              <thead>
                <tr>
                  <th>Invoice</th>
                  <th>Plan</th>
                  <th>Amount</th>
                  <th>Status</th>
                  <th>Created</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {items.map((invoice) => (
                  <tr key={invoice.id}>
                    <td>
                      <div>
                        <Link
                          className="ui-text-link invoice-reference"
                          href={`/app/invoices/${invoice.id}`}
                        >
                          {invoice.invoice_number}
                        </Link>
                        <Badge
                          tone={
                            invoice.provider_environment === "sandbox"
                              ? "warning"
                              : "neutral"
                          }
                        >
                          {invoice.provider_environment === "sandbox"
                            ? "Sandbox"
                            : "Production"}
                        </Badge>
                      </div>
                    </td>
                    <td>
                      <div>
                        {invoice.plan_name}
                        <p className="ui-caption">
                          {invoice.product_line === "desktop"
                            ? "Desktop"
                            : "Mobile"}
                        </p>
                      </div>
                    </td>
                    <td>{invoiceMoney(invoice)}</td>
                    <td>
                      <InvoiceStatus invoice={invoice} />
                    </td>
                    <td>{invoiceDate(invoice.created_at)}</td>
                    <td>
                      <ExportInvoice
                        key={`${auth.user?.id}-${invoice.id}`}
                        invoice={invoice}
                      />
                    </td>
                  </tr>
                ))}
              </tbody>
            </Table>
            <CursorPagination
              hasMore={invoices.hasNextPage}
              loading={invoices.isFetchingNextPage}
              onNext={() => void invoices.fetchNextPage()}
            />
          </Card>
        )}
      </main>
    </InvoiceAccess>
  );
}

function Details({ rows }: { rows: [string, ReactNode][] }) {
  return (
    <dl className="invoice-details">
      {rows.map(([label, value]) => (
        <div key={label}>
          <dt>{label}</dt>
          <dd>{value ?? "—"}</dd>
        </div>
      ))}
    </dl>
  );
}

export function InvoiceDetailPage({ invoiceId }: { invoiceId: string }) {
  const access = useInvoiceAuth();
  const invoice = useQuery({
    queryKey: ["invoice", access.auth.user?.id, invoiceId],
    queryFn: () =>
      access.auth.request<InvoiceDetail>(
        `${base}/${encodeURIComponent(invoiceId)}`,
      ),
    enabled: access.verified,
    retry: false,
  });
  const item = invoice.data;
  return (
    <InvoiceAccess {...access}>
      <main className="space-y-6">
        <Link className="ui-text-link" href="/app/invoices">
          ← Invoices
        </Link>
        <PageHeader
          title="Invoice details"
          description={item?.invoice_number}
          actions={
            item && (
              <ExportInvoice
                key={`${access.auth.user?.id}-${invoiceId}`}
                invoice={item}
              />
            )
          }
        />
        {invoice.isPending ? (
          <Skeleton label="Loading invoice…" />
        ) : invoice.isError ? (
          <ErrorState
            title="Unable to load invoice."
            onRetry={() => void invoice.refetch()}
          >
            {invoice.error.message}
          </ErrorState>
        ) : (
          item && (
            <>
              <Card className="space-y-4">
                <div className="flex flex-wrap gap-3">
                  <InvoiceStatus invoice={item} />
                  <Badge
                    tone={
                      item.provider_environment === "sandbox"
                        ? "warning"
                        : "neutral"
                    }
                  >
                    {item.provider_environment === "sandbox"
                      ? "Sandbox"
                      : "Production"}
                  </Badge>
                </div>
                <h2>{invoiceMoney(item)}</h2>
                <p className="text-secondary">
                  {item.provider_environment === "sandbox" &&
                    "This is a Sandbox test transaction. "}
                  {item.status === "paid"
                    ? "Payment confirmed by SePay."
                    : "Payment is not currently confirmed as completed."}
                </p>
                <Details
                  rows={[
                    ["Account", item.account_email],
                    ["Plan", item.plan_name],
                    [
                      "Product line",
                      item.product_line === "desktop" ? "Desktop" : "Mobile",
                    ],
                    [
                      "Billing duration",
                      item.terms.billing_months
                        ? `${item.terms.billing_months} month(s)`
                        : null,
                    ],
                    ["Created", invoiceDate(item.created_at)],
                    ["Paid", invoiceDate(item.paid_at)],
                    ["Checkout expires", invoiceDate(item.expires_at)],
                    ["Cancelled", invoiceDate(item.cancelled_at)],
                    ["Failed", invoiceDate(item.failed_at)],
                    ["Last updated", invoiceDate(item.updated_at)],
                  ]}
                />
                <Button
                  size="sm"
                  onClick={() => void invoice.refetch()}
                  loading={invoice.isRefetching}
                >
                  Refresh status
                </Button>
              </Card>
              <Card className="space-y-4">
                <h2>Transaction details</h2>
                <Details
                  rows={[
                    ["Provider", item.provider],
                    ["Payment method", item.payment_method],
                    ["Provider order", item.provider_order_id],
                    ["Transaction reference", item.provider_transaction_id],
                    ["Transaction UUID", item.provider_transaction_uuid],
                  ]}
                />
              </Card>
              <Card className="space-y-4">
                <h2>Plan terms at checkout</h2>
                <Details
                  rows={[
                    ["Projects", item.terms.max_projects],
                    ["Keywords", item.terms.max_keywords],
                    ["Checks per month", item.terms.monthly_keyword_checks],
                    [
                      "Scheduled checks",
                      item.terms.scheduled_checks_enabled
                        ? item.terms.max_scheduled_frequency
                        : item.terms.scheduled_checks_enabled === false
                          ? "Not included"
                          : null,
                    ],
                  ]}
                />
              </Card>
            </>
          )
        )}
      </main>
    </InvoiceAccess>
  );
}
