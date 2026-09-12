"""Exercise real HTTP authentication against the running development backend."""

import json
import secrets
from uuid import uuid4

import httpx

from app.core.config import get_settings


def main() -> None:
    settings = get_settings()
    email = f"smoke-{uuid4().hex}@example.com"
    password = secrets.token_urlsafe(24)
    base_url = f"http://127.0.0.1:{settings.backend_port}"
    with httpx.Client(base_url=base_url, timeout=10) as client:
        signup = client.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "password": password,
                "accept_terms": True,
            },
        )
        assert signup.status_code == 201, "Registration failed"
        assert signup.headers["cache-control"] == "no-store"
        assert "HttpOnly" in signup.headers["set-cookie"]
        token = signup.json()["access_token"]
        me = client.get(
            "/api/v1/users/me", headers={"Authorization": f"Bearer {token}"}
        )
        assert me.status_code == 200 and me.json()["email"] == email
        old_refresh = client.cookies.get(settings.auth_cookie_name)
        refreshed = client.post("/api/v1/auth/refresh", json={})
        assert refreshed.status_code == 200, "Refresh failed"
        assert old_refresh != client.cookies.get(settings.auth_cookie_name)
        rejected = client.post(
            "/api/v1/auth/refresh",
            json={},
            headers={
                "Cookie": f"{settings.auth_cookie_name}={old_refresh}",
            },
        )
        assert rejected.status_code == 401, "Rotated token replay succeeded"
        me = client.get(
            "/api/v1/users/me",
            headers={"Authorization": f"Bearer {refreshed.json()['access_token']}"},
        )
        assert me.status_code == 200
        assert client.post("/api/v1/auth/logout", json={}).status_code == 200
        assert client.post("/api/v1/auth/refresh", json={}).status_code == 401
        assert client.post("/api/v1/auth/logout", json={}).status_code == 200
        logged_in = client.post(
            "/api/v1/auth/login", json={"email": email, "password": password}
        )
        assert logged_in.status_code == 200
        assert client.post("/api/v1/auth/logout", json={}).status_code == 200
    # Only the verification result is printed; never credentials or token values.
    print(
        json.dumps(
            {
                "authentication_smoke": "passed",
                "checks": [
                    "registration",
                    "current_user",
                    "rotation",
                    "replay_rejection",
                    "logout",
                    "repeat_logout",
                    "login",
                ],
            }
        )
    )


if __name__ == "__main__":
    main()
