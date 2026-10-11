import { AuthForm } from "@/features/auth/auth-form";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Log in",
  robots: { index: false, follow: false },
};

export default function LoginPage() {
  return <AuthForm mode="login" />;
}
