from typing import Dict, Any
from langdetect import detect

SPANISH_HINTS = {
        "hola", "ayuda", "sesion", "sesión", "cuenta",
        "no puedo", "iniciar", "iniciar sesion", "iniciar sesión"
}


DOCKER_START_HINTS = {
    "docker",
    "container",
    "containers",
    "starting",
    "startup",
    "boot",
    "crash",
    "fails",
    "failing",
    "intermittent",
    "node factory",
}


def route_message(text: str) -> Dict[str, Any]:
        t = text.lower()

        # ---- Issue routing FIRST ----
        docker_hits = [h for h in DOCKER_START_HINTS if h in t]
        if docker_hits:
            # simple confidence: more matches => higher confidence (cap at 0.95)
            conf = min(0.95, 0.60 + 0.05 * len(docker_hits))
            return {
                "route": "container_startup_errors",
                "issue": "container_startup",
                "confidence": conf,
                "signals": {
                    "matched": docker_hits[:10],
                    "match_count": len(docker_hits),
                },
            }
               

        # ---- Language heuristics ----
        spanish_hits = [h for h in SPANISH_HINTS if h in t]
        if spanish_hits:
            conf = min(0.90, 0.65 + 0.05 * len(spanish_hits))
            return {
                "route": "language_es",
                "issue": "language",
                "confidence": conf,
                "signals": {
                    "matched": spanish_hits[:10],
                    "match_count": len(spanish_hits),
                },
            }


        try:
            lang = detect(text)
        except Exception:
            lang = "en"

        if lang.startswith("es"):
            return {
                "route": "language_es",
                "issue": "language",
                "confidence": 0.60,
                "signals": {"langdetect": lang},
        }

        return {
            "route": "language_en",
            "issue": "language",
            "confidence": 0.60,
            "signals": {"langdetect": lang},
        }
