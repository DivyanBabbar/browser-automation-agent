from browser_agent.models import AutomationPlan, AutomationStep
from browser_agent.planner import ApprovalRequired, validate_approvals
from browser_agent.safety import BrowserPolicyError, validate_fill_target, validate_url


def test_local_and_private_destinations_are_rejected():
    for url, domains in [
        ("http://127.0.0.1/admin", ["127.0.0.1"]),
        ("http://10.0.0.5/", ["10.0.0.5"]),
        ("https://app.example.com", ["example.com"]),
        ("file:///etc/passwd", ["example.com"]),
    ]:
        try:
            validate_url(url, domains)
        except BrowserPolicyError:
            continue
        raise AssertionError(f"Expected unsafe destination to be rejected: {url}")


def test_domain_policy_defaults_to_exact_host():
    assert validate_url("https://docs.example.com/guide", ["docs.example.com"]) == "docs.example.com"
    try:
        validate_url("https://other.example.com", ["docs.example.com"])
    except BrowserPolicyError:
        pass
    else:
        raise AssertionError("Sibling subdomains must require explicit allowlisting")


def test_credentials_and_payment_fields_are_blocked():
    blocked = [
        {"type": "password", "name": "account"},
        {"type": "text", "name": "card_number"},
        {"type": "text", "autocomplete": "one-time-code"},
    ]
    for attributes in blocked:
        try:
            validate_fill_target(attributes)
        except BrowserPolicyError:
            continue
        raise AssertionError(f"Expected sensitive field to be rejected: {attributes}")


def test_click_and_fill_steps_require_explicit_approval():
    plan = AutomationPlan(
        summary="Find and open the contact form.",
        steps=[
            AutomationStep(id="read", action="extract_text", selector="main", rationale="Read page"),
            AutomationStep(id="open", action="click", selector="#contact", rationale="Open form"),
            AutomationStep(id="name", action="fill", selector="[name=name]", value="Ari", rationale="Enter name"),
        ],
    )

    assert plan.steps[0].requires_approval is False
    assert plan.steps[1].requires_approval is True
    try:
        validate_approvals(plan, ["open"])
    except ApprovalRequired as exc:
        assert exc.step_ids == ["name"]
    else:
        raise AssertionError("Missing approvals must be rejected")
    validate_approvals(plan, ["open", "name"])


def test_plan_rejects_non_css_selectors_and_duplicate_ids():
    try:
        AutomationStep(id="unsafe", action="click", selector="javascript:alert(1)", rationale="Bad")
    except ValueError:
        pass
    else:
        raise AssertionError("Script-like selectors must be rejected")
    try:
        AutomationPlan(
            summary="Duplicate IDs",
            steps=[
                AutomationStep(id="same", action="wait", wait_ms=1, rationale="First"),
                AutomationStep(id="same", action="wait", wait_ms=1, rationale="Second"),
            ],
        )
    except ValueError:
        pass
    else:
        raise AssertionError("Duplicate step IDs must be rejected")
