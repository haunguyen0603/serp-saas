export interface HealthResponse {
  status: "ok";
}

export interface ApiErrorResponse {
  error: { code: string; message: string };
}
