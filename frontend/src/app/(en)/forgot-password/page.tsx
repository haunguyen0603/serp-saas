import type { Metadata } from "next";
import { ForgotPassword } from "@/features/auth/password-recovery";

export const metadata: Metadata = {
  title: "Forgot password",
  robots: { index: false, follow: false },
  referrer: "no-referrer",
};

export default function ForgotPasswordPage() {
  return <ForgotPassword />;
}
