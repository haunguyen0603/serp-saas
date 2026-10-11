import { CustomerBilling } from "@/features/admin/billing/customer-billing";
export default async function Page({
  params,
}: {
  params: Promise<{ userId: string }>;
}) {
  const { userId } = await params;
  return <CustomerBilling userId={userId} />;
}
