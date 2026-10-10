"use client";

import { useState } from "react";
import Link from "next/link";
import { Card } from "@/design-system/ui";
import { useAuth } from "./auth-provider";
import { PasswordForm } from "./password-form";

export function ChangePassword() {
  const auth = useAuth();
  const [changed, setChanged] = useState(false);
  return (
    <Card className="mt-8">
      <div className="max-w-md space-y-6">
        <h2 className="text-xl font-semibold">Change password</h2>
        <p className="text-secondary">
          Enter your current password and choose a new one.
        </p>
        <PasswordForm
          currentPassword
          submitLabel="Change password"
          onSubmit={async (password, current) => {
            setChanged(false);
            await auth.changePassword(current, password);
            setChanged(true);
          }}
        />
        {changed && (
          <p role="status">
            Your password has been changed. Other sessions have been signed out.
          </p>
        )}
        <Link href="/forgot-password" className="ui-text-link">
          Forgot your current password?
        </Link>
      </div>
    </Card>
  );
}
