import { AuthForm } from "@/features/auth/auth-form";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Create Account",
  robots: { index: false, follow: false },
};

export default function SignupPage() {
  return <AuthForm mode="signup" />;
}
