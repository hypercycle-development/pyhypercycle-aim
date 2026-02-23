from aims.router.router import route_message
from aims.language_en.aim import respond as respond_en
from aims.language_es.aim import respond as respond_es
from aims.issue_classifier.aim import classify_issue
from aims.telemetry.logger import log_event


def handle_message(message: str) -> dict:
    route = route_message(message)
    issue = classify_issue(message)

    if route == "language_es":
        reply = respond_es(message)
    else:
        reply = respond_en(message)

    log_event({
        "aim": "support_core",
        "route": route,
        "issue": issue,
        "chars": len(message),
})

    return {
        "route": route,
        "issue": issue,
        "reply": reply,
}
