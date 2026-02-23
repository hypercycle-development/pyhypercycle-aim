from aims.router.router import route_message
from aims.language_en.aim import respond as respond_en
from aims.language_es.aim import respond as respond_es
from aims.issue_classifier.aim import classify_issue



def handle_message(message: str) -> dict:
    route_result = route_message(message)
    route = route_result.get("route", "unknown")

    decision_trace = {
        "route_source": "router",
        "route_confidence": route_result.get("confidence"),
        "issue_source": "classifier",
        "escalation_rule": "billing_only",
        "language": "es" if route == "language_es" else "en",
    }

    issue = classify_issue(message)

    # Route-aware reply selection (no schema change)
    if route == "language_es":
        reply = respond_es(message)

    elif route == "container_startup_errors":
        reply = (
            "Thanks for contacting support.\n\n"
            "It sounds like you're seeing intermittent errors when starting containers. "
            "Let's narrowthis dow.\n\n"
            "1) What environment are running this on (Docker Desktop on Mac/Windows, Linux server, etc.)?\n"
            "2) What is the exact error message (copy/paste) and when does it happen (pull, build, or run)?\n"
            "3) Please run these and share the output:\n"
            "   - docker ps -a\n"
            "   - docker logs <container_name_or_id>\n"
            "   - docker info\n\n"
            "Common causes include port conflicts, low disk space, Docker daemon not running, "
            "and image pull/auth issues. Once I see the error test, I can tell you the quickest fix."
        )

    else:
        reply = respond_en(message)

    # Escalation rule (Fast path)
    escalate = (issue == "billing")

    if escalate:
        if route == "language_es":
            reply += "\n\nVoy a escalar esto a un agente humano de facturacion."
        else:
            reply += "\n\nI'm escalating this to a human billing agent."

    # Hard invariant: escalation is billing-only
    if escalate and issue != "billing":
        escalate = False

    return {
        "route": route,
        "issue": issue,
        "reply": reply,
        "escalate": escalate,
        "decision_trace": {
            "route_result": route_result,
            "issue": issue,
            "escalate_rule": "billing_only",
        },
    }
