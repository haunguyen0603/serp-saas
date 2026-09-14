import type { Metadata } from "next";
import { AuthForm } from "@/features/auth/auth-form";

export const metadata: Metadata = {
  title: "Create Account",
  description: "Create a free SERP SaaS account and start tracking keywords.",
  alternates: { canonical: "/register" },
};

export default function RegisterPage() {
  return <AuthForm mode="signup" />;
}
