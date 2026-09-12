function getFrontendConfig() {
  const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL;
  const environment = process.env.NEXT_PUBLIC_APP_ENV;
  if (!apiBaseUrl) {
    throw new Error("Missing required configuration: NEXT_PUBLIC_API_BASE_URL");
  }
  if (
    !environment ||
    !["development", "test", "production"].includes(environment)
  ) {
    throw new Error(
      "NEXT_PUBLIC_APP_ENV must be development, test, or production",
    );
  }
  let url: URL;
  try {
    url = new URL(apiBaseUrl);
  } catch {
    throw new Error("NEXT_PUBLIC_API_BASE_URL must be an HTTP(S) URL");
  }
  if (
    !["http:", "https:"].includes(url.protocol) ||
    url.username ||
    url.password ||
    url.search ||
    url.hash
  ) {
    throw new Error(
      "NEXT_PUBLIC_API_BASE_URL must be an HTTP(S) URL without credentials, query, or fragment",
    );
  }
  return { apiBaseUrl: apiBaseUrl.replace(/\/$/, ""), environment };
}

export const config = getFrontendConfig();
