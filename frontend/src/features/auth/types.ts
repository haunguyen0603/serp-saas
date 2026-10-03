export interface User {
  id: string;
  is_platform_admin?: boolean;
  email: string;
  status: "active" | "disabled";
  email_verified: boolean;
  terms_accepted_at: string;
  last_login_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: "bearer";
  expires_in: number;
  user: User;
  email_verification_required?: boolean;
}

export interface VerificationStatus {
  verified: boolean;
  delivery_status: "not_requested" | "pending" | "sent" | "failed" | "verified";
  retry_after_seconds: number;
  expires_at: string | null;
}

export interface LoginInput {
  email: string;
  password: string;
}
export interface RegisterInput extends LoginInput {
  accept_terms: boolean;
}
