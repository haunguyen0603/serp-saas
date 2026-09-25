import base64
import json
import re
import unicodedata
from datetime import datetime
from urllib.parse import urlsplit
from uuid import UUID

from app.core.errors import AppError

_whitespace = re.compile(r"\s+")
_country = re.compile(r"^[A-Z]{2}$", re.ASCII)
_language = re.compile(r"^[A-Za-z]{2,3}(?:-[A-Za-z0-9]{2,8})*$", re.ASCII)


def normalize_name(value: str) -> str:
    result = value.strip()
    if not 1 <= len(result) <= 200:
        raise AppError(422, "INVALID_PROJECT_NAME", "Project name is invalid.")
    return result


def normalize_tracked_site_name(value: str) -> str:
    result = value.strip()
    if not 1 <= len(result) <= 200:
        raise AppError(
            422, "INVALID_TRACKED_SITE_NAME", "Tracked Site name is invalid."
        )
    return result


def normalize_domain(value: str) -> str:
    raw = value.strip()
    if not raw or len(raw) > 2048:
        raise AppError(422, "INVALID_DOMAIN", "Domain is invalid.")
    candidate = raw if "://" in raw else f"//{raw}"
    try:
        parsed = urlsplit(candidate)
        if parsed.scheme and parsed.scheme.lower() not in {"http", "https"}:
            raise ValueError
        if parsed.username is not None or parsed.password is not None:
            raise ValueError
        # Validate a supplied port, then intentionally discard it with the path,
        # query, and fragment. Tracked Domains store only canonical hostnames.
        _ = parsed.port
        hostname = parsed.hostname
        if hostname is None:
            raise ValueError
        hostname = hostname.rstrip(".").encode("idna").decode("ascii").lower()
        labels = hostname.split(".")
        if (
            len(hostname) > 253
            or len(labels) < 2
            or any(not label or len(label) > 63 for label in labels)
            or any(
                label.startswith("-")
                or label.endswith("-")
                or not re.fullmatch(r"[a-z0-9-]+", label, re.ASCII)
                for label in labels
            )
        ):
            raise ValueError
        return hostname
    except (UnicodeError, ValueError):
        raise AppError(422, "INVALID_DOMAIN", "Domain is invalid.") from None


def normalize_search_engine(value: str) -> str:
    result = value.strip().lower()
    if result != "google":
        raise AppError(422, "INVALID_SEARCH_ENGINE", "Search engine is invalid.")
    return result


def normalize_country_code(value: str) -> str:
    result = value.strip().upper()
    if not _country.fullmatch(result):
        raise AppError(422, "INVALID_COUNTRY_CODE", "Country code is invalid.")
    return result


def normalize_language_code(value: str) -> str:
    raw = value.strip().replace("_", "-")
    if len(raw) > 16 or not _language.fullmatch(raw):
        raise AppError(422, "INVALID_LANGUAGE_CODE", "Language code is invalid.")
    parts = raw.split("-")
    normalized = [parts[0].lower()]
    for part in parts[1:]:
        if len(part) == 2 and part.isalpha():
            normalized.append(part.upper())
        elif len(part) == 4 and part.isalpha():
            normalized.append(part.title())
        else:
            normalized.append(part.lower())
    return "-".join(normalized)


def normalize_device(value: str) -> str:
    result = value.strip().lower()
    if result not in {"desktop", "mobile"}:
        raise AppError(422, "INVALID_DEVICE", "Device is invalid.")
    return result


def normalize_location(value: str | None) -> str | None:
    if value is None:
        return None
    result = _whitespace.sub(" ", unicodedata.normalize("NFC", value)).strip()
    if not result:
        return None
    if len(result) > 500:
        raise AppError(422, "INVALID_LOCATION", "Location is invalid.")
    return result


def normalized_location(value: str | None) -> str:
    return (normalize_location(value) or "").casefold()


def normalize_keyword(value: str) -> tuple[str, str]:
    display = _whitespace.sub(" ", unicodedata.normalize("NFC", value)).strip()
    if not display or len(display) > 512:
        raise AppError(422, "INVALID_KEYWORD", "Keyword is invalid.")
    return display, display.casefold()


def normalize_organization_name(
    value: str, *, maximum: int, code: str
) -> tuple[str, str]:
    display = _whitespace.sub(" ", unicodedata.normalize("NFC", value)).strip()
    normalized = display.casefold()
    if not display or len(display) > maximum or len(normalized) > maximum:
        raise AppError(422, code, "Organization name is invalid.")
    return display, normalized


def encode_cursor(created_at: datetime, item_id: UUID) -> str:
    payload = json.dumps(
        {"created_at": created_at.isoformat(), "id": str(item_id)},
        separators=(",", ":"),
    ).encode()
    return base64.urlsafe_b64encode(payload).rstrip(b"=").decode()


def decode_cursor(value: str | None) -> tuple[datetime, UUID] | None:
    if value is None:
        return None
    try:
        padding = "=" * (-len(value) % 4)
        payload = json.loads(base64.urlsafe_b64decode(value + padding))
        created_at = datetime.fromisoformat(payload["created_at"])
        if created_at.tzinfo is None:
            raise ValueError
        return created_at, UUID(payload["id"])
    except (ValueError, TypeError, KeyError, json.JSONDecodeError):
        raise AppError(422, "INVALID_CURSOR", "Pagination cursor is invalid.") from None
