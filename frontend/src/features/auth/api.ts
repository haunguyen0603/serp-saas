import { ApiError, requestJson } from "@/lib/api/client";
import type { AuthResponse, LoginInput, RegisterInput } from "./types";

function post(body: object): RequestInit {
  return {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  };
}

async function session(path: string, body: object): Promise<AuthResponse> {
  const result = await requestJson<AuthResponse>(path, post(body));
  if (
    !result ||
    typeof result.access_token !== "string" ||
    result.token_type !== "bearer" ||
    !result.user ||
    typeof result.user.id !== "string" ||
    typeof result.user.email !== "string"
  )
    throw new ApiError(502);
  return result;
}

export const register = (input: RegisterInput) =>
  session("/api/v1/auth/register", input);
export const login = (input: LoginInput) =>
  session("/api/v1/auth/login", input);
export const refreshSession = () => session("/api/v1/auth/refresh", {});
export const logout = async () => {
  await requestJson<{ status: "ok" }>("/api/v1/auth/logout", post({}));
};
