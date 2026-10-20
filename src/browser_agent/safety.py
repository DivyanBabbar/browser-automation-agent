import ipaddress
import re
import socket
from urllib.parse import urlsplit


class BrowserPolicyError(ValueError):
    """Raised when a URL, navigation, or requested browser action violates policy."""


SENSITIVE_FIELD_PATTERN = re.compile(
    r"password|passwd|credit.?card|card.?number|cvv|cvc|ssn|social.?security|one.?time.?code|otp|secret|token",
    re.IGNORECASE,
)


def normalize_host(value: str) -> str:
    host = value.strip().lower().rstrip(".")
    if not host or "/" in host or ":" in host or "@" in host:
        raise BrowserPolicyError("Allowed domains must be hostnames without ports or paths.")
    try:
        host = host.encode("idna").decode("ascii")
    except UnicodeError as exc:
        raise BrowserPolicyError("The domain name is invalid.") from exc
    if host in {"localhost", "localhost.localdomain"} or host.endswith((".localhost", ".local", ".internal")):
        raise BrowserPolicyError("Local and internal hostnames are blocked.")
    return host


def _is_public_ip(value: str) -> bool:
    try:
        address = ipaddress.ip_address(value)
    except ValueError:
        return True
    return address.is_global


def validate_url(url: str, allowed_domains: list[str], *, resolve_dns: bool = False) -> str:
    parsed = urlsplit(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise BrowserPolicyError("Only absolute HTTP and HTTPS URLs are allowed.")
    if parsed.username or parsed.password:
        raise BrowserPolicyError("URLs with embedded credentials are blocked.")
    host = normalize_host(parsed.hostname)
    domains = {normalize_host(domain) for domain in allowed_domains}
    if host not in domains:
        raise BrowserPolicyError(f"Navigation to {host} is outside the approved domain list.")
    if not _is_public_ip(host):
        raise BrowserPolicyError("Private, loopback, and reserved IP addresses are blocked.")
    if resolve_dns and not _is_public_destination(host):
        raise BrowserPolicyError("The destination resolves to a private or unreachable address.")
    return host


def _is_public_destination(host: str) -> bool:
    try:
        addresses = {result[4][0] for result in socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)}
    except OSError:
        return False
    return bool(addresses) and all(_is_public_ip(address) for address in addresses)


def validate_fill_target(attributes: dict[str, str | None]) -> None:
    field_type = (attributes.get("type") or "").lower()
    autocomplete = (attributes.get("autocomplete") or "").lower()
    hints = " ".join(
        value or ""
        for key, value in attributes.items()
        if key in {"name", "id", "placeholder", "aria-label"}
    )
    if field_type in {"password", "hidden", "file"}:
        raise BrowserPolicyError(f"Filling {field_type} fields is not allowed.")
    if autocomplete.startswith("cc-") or autocomplete in {"current-password", "new-password", "one-time-code"}:
        raise BrowserPolicyError("Credential and payment fields are not allowed.")
    if SENSITIVE_FIELD_PATTERN.search(hints):
        raise BrowserPolicyError("This field appears to contain sensitive information.")
