"use client";
import {
  Alert,
  Button,
  EmptyState,
  Input,
  PageHeader,
  Skeleton,
  StatusBadge,
  Table,
} from "@/design-system/ui";
import Link from "next/link";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useProtectedAuth } from "@/features/projects/protected";
import { button, control } from "@/features/billing/billing-page";
import type { BillingSummary } from "@/features/billing/types";

export function CustomerList() {
  const auth = useProtectedAuth();
  const [search, setSearch] = useState("");
  const [cursor, setCursor] = useState<string | null>(null);
  const customers = useQuery({
    queryKey: ["admin-customers", auth.user?.id, search, cursor],
    queryFn: () =>
      auth.request<{
        items: BillingSummary[];
        next_cursor: string | null;
        has_more: boolean;
      }>(
        `/api/v1/admin/customers?${new URLSearchParams({ search, ...(cursor ? { cursor } : {}) })}`,
      ),
    enabled: auth.isAuthenticated && !!auth.user?.is_platform_admin,
    retry: false,
  });
  if (auth.isAuthenticated && !auth.user?.is_platform_admin)
    return (
      <main>
        <h1>Administrator access required</h1>
      </main>
    );
  return (
    <main className="space-y-6">
      <Link href="/app">← Account</Link>
      <PageHeader title="Customers" />
      <label>
        Search email
        <Input
          className={control}
          value={search}
          onChange={(e) => {
            setSearch(e.target.value);
            setCursor(null);
          }}
        />
      </label>
      {customers.isError && <Alert>{customers.error.message}</Alert>}
      {customers.isPending && <Skeleton label="Loading customers…" />}
      <div className="overflow-x-auto">
        <Table className="w-full">
          <thead>
            <tr>
              <th>Email</th>
              <th>Desktop Plan / status / checks</th>
              <th>Mobile Plan / status / checks</th>
              <th>Account</th>
            </tr>
          </thead>
          <tbody>
            {customers.data?.items.map((customer) => (
              <tr key={customer.user_id} className="border-t border-border">
                <td className="py-4">
                  <Link
                    className="text-brand underline"
                    href={`/admin/customers/${customer.user_id}`}
                  >
                    {customer.email}
                  </Link>
                </td>
                {customer.devices.map((device) => (
                  <td key={device.device_scope}>
                    {device.plan.name} · {device.status} · {device.usage.used} /{" "}
                    {device.usage.limit} ({device.usage.reserved} reserved)
                  </td>
                ))}
                <td>
                  <StatusBadge status={customer.account_status} />
                </td>
              </tr>
            ))}
          </tbody>
        </Table>
      </div>
      {customers.data?.items.length === 0 && (
        <EmptyState title="No customers found">
          Try a different email search.
        </EmptyState>
      )}
      <div className="flex gap-3">
        <Button
          className={button}
          disabled={!cursor}
          onClick={() => setCursor(null)}
        >
          First page
        </Button>
        <Button
          className={button}
          disabled={!customers.data?.has_more}
          onClick={() => setCursor(customers.data?.next_cursor ?? null)}
        >
          Next page
        </Button>
      </div>
    </main>
  );
}
