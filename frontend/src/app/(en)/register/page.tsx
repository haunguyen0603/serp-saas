import type { Metadata } from "next";
import { AuthForm } from "@/features/auth/auth-form";
import { getAppUrl } from "@/lib/site";

export const metadata: Metadata = {
  title: "Create Account",
  description: "Create a free SERP SaaS account and start tracking keywords.",
  alternates: { canonical: new URL("/register", getAppUrl()).toString() },
  robots: { index: false, follow: false },
};

export default function RegisterPage() {
  return <AuthForm mode="signup" />;
}
