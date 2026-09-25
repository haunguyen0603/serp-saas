import { config } from "@/lib/config";
import type { HealthResponse } from "@/types/health";

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly code = "SERVICE_UNAVAILABLE",
    message = "The service is unavailable.",
  ) {
    super(message);
    this.name = "ApiError";
  }
}

const errorMessages: Record<string, string> = {
  PLAN_CHANGED: "This Plan has changed. Reload the catalog before saving.",
  INVALID_PLAN_PRICE:
    "Free Plans must stay at $0; paid Plans need a positive price.",
  PLAN_NOT_FOUND: "Plan is unavailable.",
  NO_ACTIVE_SUBSCRIPTION: "Subscription not found.",
  SUBSCRIPTION_EXPIRED: "Subscription expired. Activate a new Plan.",
  SUBSCRIPTION_CONFLICT:
    "A subscription already exists or overlaps. Use Change Plan or adjust the dates.",
  INVALID_SUBSCRIPTION_PERIOD: "Check the subscription start and end dates.",
  PROJECT_LIMIT_EXCEEDED:
    "Project limit reached for this device. Review Billing & Usage.",
  KEYWORD_LIMIT_EXCEEDED:
    "Keyword limit reached for this device. Review Billing & Usage.",
  USAGE_LIMIT_EXCEEDED:
    "Monthly check quota is insufficient. Review Billing & Usage.",
  SCHEDULE_NOT_INCLUDED: "Scheduled checks are not included in this Plan.",
  SCHEDULE_FREQUENCY_NOT_ALLOWED: "This Plan allows weekly schedules only.",
  PLAN_DEVICE_MISMATCH:
    "Device change is unavailable while checks are pending.",
  ADMIN_REQUIRED: "Platform administrator access is required.",
  USER_NOT_FOUND: "Customer not found.",

  INVALID_CREDENTIALS: "Invalid email or password.",
  EMAIL_ALREADY_REGISTERED: "This email is already registered.",
  PASSWORD_POLICY_VIOLATION: "Password must contain 10 to 128 characters.",
  TERMS_NOT_ACCEPTED: "You must accept the Terms of Service.",
  AUTHENTICATION_REQUIRED: "Please log in to continue.",
  INVALID_ACCESS_TOKEN: "Please log in again.",
  EXPIRED_ACCESS_TOKEN: "Your session needs to be refreshed.",
  INVALID_REFRESH_TOKEN: "Please log in again.",
  DISABLED_USER: "This account is disabled.",
  VALIDATION_ERROR: "Please check your email and form details.",
  PROJECT_NOT_FOUND: "Project not found.",
  INVALID_PROJECT_NAME: "Project name is invalid.",
  INVALID_PROJECT_STATUS: "Project status is invalid.",
  PROJECT_REQUIRES_KEYWORDS: "Add at least one valid keyword.",
  PROJECT_KEYWORD_LIMIT_EXCEEDED:
    "A Project may contain at most 1000 keyword inputs.",
  KEYWORD_NOT_FOUND: "Keyword not found.",
  KEYWORD_ALREADY_EXISTS: "This keyword already exists in this Project.",
  INVALID_KEYWORD: "Keyword is invalid.",
  INVALID_SEARCH_ENGINE: "Search engine is invalid.",
  INVALID_COUNTRY_CODE: "Country code is invalid.",
  INVALID_LANGUAGE_CODE: "Language code is invalid.",
  INVALID_DEVICE: "Device is invalid.",
  INVALID_LOCATION: "Location is invalid.",
  INVALID_CURSOR: "Pagination cursor is invalid.",
  INVALID_ANALYTICS_RANGE: "Select a supported analytics range.",
  INVALID_MOVEMENT_FILTER: "The movement filter is invalid.",
  INVALID_STATUS_FILTER: "The ranking status filter is invalid.",
  INVALID_POSITION_BUCKET:
    "The position filter is unavailable for this checked depth.",
  INVALID_SORT_FIELD: "The ranking sort field is invalid.",
  INVALID_SORT_ORDER: "The ranking sort order is invalid.",
  INVALID_DATE_RANGE:
    "Choose valid UTC dates. From date must not be after To date.",
  INVALID_DEVICE_SCOPE: "Analytics must use the Project device.",
  BULK_KEYWORD_LIMIT_EXCEEDED:
    "A bulk request may contain at most 1000 keywords.",
  TRACKED_SITE_NOT_FOUND: "Tracked Site not found.",
  TRACKED_DOMAIN_NOT_FOUND: "Tracked Domain not found.",
  INVALID_TRACKED_SITE_NAME: "Tracked Site name is invalid.",
  INVALID_TRACKED_SITE_STATUS: "Tracked Site status is invalid.",
  INVALID_DOMAIN: "Domain is invalid.",
  DOMAIN_ALREADY_TRACKED: "This domain is already tracked in your account.",
  PRIMARY_DOMAIN_REQUIRED: "An active Tracked Site requires a primary domain.",
  PRIMARY_DOMAIN_MUST_BE_ACTIVE: "The primary domain must remain active.",
  PRIMARY_DOMAIN_REPLACEMENT_REQUIRED:
    "Promote another domain before replacing the primary domain.",
  SERP_PROVIDER_NOT_CONFIGURED: "Provider is not configured.",
  SERP_PROVIDER_TIMEOUT: "The SERP provider timed out.",
  SERP_PROVIDER_UNAVAILABLE: "The SERP provider is unavailable.",
  SERP_PROVIDER_RATE_LIMITED: "Provider quota or rate limit reached.",
  SERP_PROVIDER_AUTH_ERROR: "The SERP provider credentials were rejected.",
  SERP_PROVIDER_INVALID_RESPONSE:
    "The SERP provider returned an invalid response.",
  SERP_PROVIDER_ERROR: "The SERP provider could not complete the search.",
  RANK_CHECK_ALREADY_RUNNING:
    "A rank check is already running for this Keyword.",
  RANK_CHECK_NOT_FOUND: "Rank Check not found.",
  PROJECT_NOT_ACTIVE: "This Project is archived.",
  KEYWORD_NOT_ACTIVE: "This Keyword is paused.",
  RANK_CHECK_LIMIT_EXCEEDED:
    "This Project exceeds the manual check limit. Check individual Keywords.",
  HISTORY_EXISTS:
    "Ranking history exists. Archive or pause this item instead of deleting it.",
  REPORT_NOT_FOUND: "Report not found.",
  REPORT_NOT_READY: "Report is still being generated.",
  INVALID_REPORT_RANGE: "Choose a valid report period.",
  REPORT_TOO_LARGE: "Narrow the report filters or reporting period.",
  REPORT_EXPIRED: "This report expired. Generate it again to download.",
  REPORT_ARTIFACT_MISSING: "The report file is unavailable. Generate it again.",
  REPORT_GENERATION_FAILED: "The report could not be generated.",
  REPORT_DELIVERY_UNAVAILABLE: "Scheduled email delivery is not configured.",
  REPORT_EMAIL_NOT_VERIFIED:
    "Verify your account email before scheduling reports.",
  REPORT_CONCURRENCY_LIMIT:
    "Wait for an active report to finish before generating another.",
  REPORT_SCHEDULE_LIMIT:
    "This Project has reached its active report schedule limit.",
  REPORT_SCHEDULE_NOT_FOUND: "Report schedule not found.",
  REPORT_RETRY_NOT_ALLOWED:
    "This report cannot be retried in its current state.",
  REPORT_RETRY_EXHAUSTED: "This report has reached its retry limit.",
  IDEMPOTENCY_CONFLICT:
    "This report request was already used with different settings.",
};

async function responseError(response: Response): Promise<ApiError> {
  let body: unknown;
  try {
    body = await response.json();
  } catch {
    body = null;
  }
  if (
    typeof body === "object" &&
    body !== null &&
    "error" in body &&
    typeof body.error === "object" &&
    body.error !== null &&
    "code" in body.error &&
    typeof body.error.code === "string"
  ) {
    const code = body.error.code;
    return new ApiError(
      response.status,
      code,
      errorMessages[code] ?? "The request could not be completed.",
    );
  }
  return new ApiError(response.status);
}

export async function requestJson<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${config.apiBaseUrl}${path}`, {
      ...options,
      credentials: "include",
      cache: "no-store",
      signal: options.signal ?? AbortSignal.timeout(8000),
      headers: { Accept: "application/json", ...options.headers },
    });
  } catch {
    throw new ApiError(0);
  }
  if (!response.ok) {
    throw await responseError(response);
  }
  if (response.status === 204) return undefined as T;
  try {
    return (await response.json()) as T;
  } catch {
    throw new ApiError(502);
  }
}

export interface DownloadedFile {
  blob: Blob;
  filename: string;
}

export async function requestFile(
  path: string,
  accessToken: string,
): Promise<DownloadedFile> {
  let response: Response;
  try {
    response = await fetch(`${config.apiBaseUrl}${path}`, {
      credentials: "include",
      cache: "no-store",
      signal: AbortSignal.timeout(30000),
      headers: { Authorization: `Bearer ${accessToken}` },
    });
  } catch {
    throw new ApiError(0);
  }
  if (!response.ok) throw await responseError(response);
  const disposition = response.headers.get("Content-Disposition") ?? "";
  const filename = disposition.match(/filename="([^"]+)"/)?.[1] ?? "report";
  return { blob: await response.blob(), filename };
}

async function getStatus(path: string): Promise<HealthResponse> {
  const response = await fetch(`${config.apiBaseUrl}${path}`, {
    method: "GET",
    headers: { Accept: "application/json" },
    cache: "no-store",
    signal: AbortSignal.timeout(8000),
  });
  if (!response.ok) throw new ApiError(response.status);
  const body: unknown = await response.json();
  if (
    typeof body !== "object" ||
    body === null ||
    !("status" in body) ||
    body.status !== "ok"
  ) {
    throw new ApiError(502);
  }
  return { status: "ok" };
}

export const getHealth = () => getStatus("/health");
export const getDatabaseHealth = () => getStatus("/health/db");
export const getRedisHealth = () => getStatus("/health/redis");
