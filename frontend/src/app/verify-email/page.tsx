import type { Metadata } from "next";
import { EmailVerification } from "@/features/auth/email-verification";

export const metadata: Metadata = {
  title: "Verify your email",
  robots: { index: false, follow: false },
  referrer: "no-referrer",
};

export default function VerifyEmailPage() {
  return <EmailVerification />;
}
