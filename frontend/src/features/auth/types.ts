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
}

export interface LoginInput {
  email: string;
  password: string;
}
export interface RegisterInput extends LoginInput {
  accept_terms: boolean;
}
