import {
  ApiError,
  requestFile,
  requestJson,
  type DownloadedFile,
} from "@/lib/api/client";
import * as api from "./api";
import type { AuthResponse, LoginInput, RegisterInput, User } from "./types";

export interface AuthState {
  user: User | null;
  accessToken: string | null;
  status: "loading" | "authenticated" | "anonymous" | "error";
  error: string | null;
  emailVerificationRequired: boolean;
}

export type AuthenticatedRequest = <T>(
  path: string,
  options?: RequestInit,
) => Promise<T>;

const initial: AuthState = {
  user: null,
  accessToken: null,
  status: "loading",
  error: null,
  emailVerificationRequired: false,
};

// One instance per mounted provider, never a server-wide mutable singleton.
export class AuthSession {
  private state = initial;
  private listeners = new Set<() => void>();
  private refreshFlight: Promise<AuthResponse> | null = null;
  private started = false;
  private generation = 0;

  constructor(private readonly clearUserCache: () => void = () => {}) {}

  getSnapshot = () => this.state;
  getServerSnapshot = () => initial;
  subscribe = (listener: () => void) => {
    this.listeners.add(listener);
    return () => {
      this.listeners.delete(listener);
    };
  };

  private update(state: AuthState) {
    if (this.state.user?.id !== state.user?.id) this.clearUserCache();
    this.state = state;
    this.listeners.forEach((listener) => listener());
  }

  private accept(response: AuthResponse) {
    this.update({
      user: response.user,
      accessToken: response.access_token,
      status: "authenticated",
      error: null,
      emailVerificationRequired: response.email_verification_required ?? false,
    });
  }

  start = () => {
    if (this.started) return;
    this.started = true;
    void this.refresh().catch(() => {});
  };

  refresh = (): Promise<AuthResponse> => {
    if (this.refreshFlight) return this.refreshFlight;
    const generation = this.generation;
    this.refreshFlight = api
      .refreshSession()
      .then((result) => {
        if (generation === this.generation) this.accept(result);
        return result;
      })
      .catch((error: unknown) => {
        if (generation === this.generation) {
          const unauthorized =
            error instanceof ApiError &&
            (error.status === 401 || error.status === 403);
          this.update({
            user: null,
            accessToken: null,
            status: unauthorized ? "anonymous" : "error",
            error: unauthorized
              ? null
              : "The service is unavailable. Please try again.",
            emailVerificationRequired: false,
          });
        }
        throw error;
      })
      .finally(() => {
        this.refreshFlight = null;
      });
    return this.refreshFlight;
  };

  register = async (input: RegisterInput) => {
    await this.refreshFlight?.catch(() => {});
    const result = await api.register(input);
    this.generation++;
    this.accept(result);
    return result;
  };

  login = async (input: LoginInput) => {
    await this.refreshFlight?.catch(() => {});
    const result = await api.login(input);
    this.generation++;
    this.accept(result);
    return result;
  };

  logout = async () => {
    // Finish an in-flight rotation before revoking the cookie it returned.
    this.generation++;
    await this.refreshFlight?.catch(() => {});
    await api.logout();
    this.update({
      user: null,
      accessToken: null,
      status: "anonymous",
      error: null,
      emailVerificationRequired: false,
    });
  };

  authenticatedRequest: AuthenticatedRequest = async <T>(
    path: string,
    options: RequestInit = {},
  ): Promise<T> => {
    if (this.state.status === "loading") await this.refresh();
    const generation = this.generation;
    const token = this.state.accessToken;
    if (!token) throw new ApiError(401, "AUTHENTICATION_REQUIRED");
    const send = (accessToken: string) =>
      requestJson<T>(path, {
        ...options,
        headers: {
          ...options.headers,
          Authorization: `Bearer ${accessToken}`,
        },
      });
    try {
      return await send(token);
    } catch (error) {
      if (
        !(error instanceof ApiError) ||
        error.status !== 401 ||
        generation !== this.generation
      )
        throw error;
      const refreshed =
        this.state.accessToken !== token && this.state.accessToken
          ? this.state.accessToken
          : (await this.refresh()).access_token;
      if (generation !== this.generation)
        throw new ApiError(401, "AUTHENTICATION_REQUIRED");
      // Deliberately no recursive retry: at most one refresh and one retry.
      return await send(refreshed);
    }
  };

  authenticatedDownload = async (path: string): Promise<DownloadedFile> => {
    if (this.state.status === "loading") await this.refresh();
    const generation = this.generation;
    const token = this.state.accessToken;
    if (!token) throw new ApiError(401, "AUTHENTICATION_REQUIRED");
    try {
      return await requestFile(path, token);
    } catch (error) {
      if (
        !(error instanceof ApiError) ||
        error.status !== 401 ||
        generation !== this.generation
      )
        throw error;
      const refreshed =
        this.state.accessToken !== token && this.state.accessToken
          ? this.state.accessToken
          : (await this.refresh()).access_token;
      if (generation !== this.generation)
        throw new ApiError(401, "AUTHENTICATION_REQUIRED");
      return requestFile(path, refreshed);
    }
  };

  getCurrentUser = () => this.authenticatedRequest<User>("/api/v1/users/me");
}
