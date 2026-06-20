"""Node Offer Document — a node's signed, self-describing advertisement.

A HyperCycle node already serves a ``/manifest.json`` per AIM describing *what it
does* and *what it costs*. What the network has never had is a single, **signed**
document at the node saying *"this node runs these AIMs, on this hardware, at these
prices"* — the thing a discovery service (or another agent) needs to answer
"where can I run AIM X, and for how much?".

This module adds that as an OPTIONAL, standard endpoint:

    GET /.well-known/hypercycle/offers.json

The document is assembled from the AIM's own manifest (so prices stay in one
place) plus an optional operator-declared ``capabilities`` block, and is **signed
with the node's Ethereum key** (the same key the node already uses for payments /
``AIM ProtocolV2``). Because it's signed, any consumer can re-fetch it straight
from the node and verify it independently — so an index that caches it can never
forge or alter a price. The node stays the source of truth; indexes are just
caches. Serving it is opt-out (``serve_offer_document = False``); signing is
automatic when a key is configured and a no-op otherwise.

Signing uses ``eth_account`` (already available via the ``web3`` dependency); if
it cannot be imported the document is still served, just unsigned.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone

from starlette.routing import Route

from pyhypercycle_aim.util import JSONResponseCORS

try:  # eth_account ships with web3 (a declared dependency); degrade if absent
    from eth_account import Account
    from eth_account.messages import encode_defunct
    _ETH_OK = True
except Exception:  # pragma: no cover - only when web3/eth_account missing
    _ETH_OK = False

WELL_KNOWN_PATH = "/.well-known/hypercycle/offers.json"


# --------------------------------------------------------------------------- #
# Pure helpers (no server state) — also usable by indexers/consumers.
# --------------------------------------------------------------------------- #
def canonical(doc: dict) -> str:
    """Canonical serialization that gets signed/verified.

    The ``signature`` field is excluded; keys are sorted and separators are
    compact so the sender and any verifier produce byte-identical input.
    """
    body = {k: v for k, v in doc.items() if k != "signature"}
    return json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def build_offer_document(manifest_json: dict, *, node_id: str = "", endpoint: str = "",
                         region: str = "", license_level=None, capabilities: dict | None = None,
                         issued_at: str | None = None) -> dict:
    """Build an (unsigned) offer document from an AIM ``manifest.json`` dict.

    Each manifest endpoint becomes one priced offer for this AIM's ``short_name``.
    """
    short_name = manifest_json.get("short_name") or manifest_json.get("name") or ""
    version = manifest_json.get("version") or ""
    aims = []
    for ep in (manifest_json.get("endpoints") or []):
        aims.append({
            "short_name": short_name,
            "version": version,
            "uri": ep.get("uri") or "/",
            "price_per_call": ep.get("price_per_call") or {},
            "price_per_mb": ep.get("price_per_mb") or {},
            "currency": ep.get("currency") or "",
            "settles_in": ep.get("settles_in") or [],
        })
    node = {"id": node_id or "", "endpoint": endpoint or ""}
    if region:
        node["region"] = region
    if license_level is not None:
        node["license_level"] = license_level
    doc = {
        "node": node,
        "capabilities": capabilities or {},
        "aims": aims,
        "issued_at": issued_at or datetime.now(timezone.utc).isoformat(),
    }
    return doc


def sign_offer_document(doc: dict, private_key: str) -> dict:
    """Return a copy of ``doc`` with a ``signature`` (EIP-191 personal_sign).

    If ``node.id`` is empty it is filled in from the key's address. Raises if
    ``eth_account`` is unavailable so the caller can decide how to handle it.
    """
    if not _ETH_OK:
        raise RuntimeError("eth_account not available (install web3) — cannot sign offer document")
    acct = Account.from_key(private_key)
    doc = dict(doc)
    node = dict(doc.get("node") or {})
    if not node.get("id"):
        node["id"] = acct.address.lower()
    doc["node"] = node
    signed = acct.sign_message(encode_defunct(text=canonical(doc)))
    doc["signature"] = signed.signature.hex()
    return doc


def verify_offer_document(doc: dict) -> bool:
    """True iff ``doc.signature`` is a valid signature by ``doc.node.id``."""
    node_id = ((doc.get("node") or {}).get("id") or "").lower()
    sig = doc.get("signature")
    if not (_ETH_OK and node_id and sig):
        return False
    try:
        recovered = Account.recover_message(encode_defunct(text=canonical(doc)), signature=sig)
        return recovered.lower() == node_id
    except Exception:
        return False


def _capabilities_from_env() -> dict:
    raw = os.environ.get("HYPC_NODE_CAPABILITIES", "")
    if not raw:
        return {}
    try:
        v = json.loads(raw)
        return v if isinstance(v, dict) else {}
    except (ValueError, TypeError):
        return {}


def node_config_from_env() -> dict:
    """Operator-supplied node identity/specs, read from environment variables.

    HYPC_NODE_ID, HYPC_NODE_ENDPOINT, HYPC_NODE_REGION, HYPC_NODE_LICENSE_LEVEL,
    HYPC_NODE_PRIVATE_KEY, HYPC_NODE_CAPABILITIES (JSON object).
    """
    lvl = os.environ.get("HYPC_NODE_LICENSE_LEVEL")
    return {
        "node_id": os.environ.get("HYPC_NODE_ID", ""),
        "endpoint": os.environ.get("HYPC_NODE_ENDPOINT", ""),
        "region": os.environ.get("HYPC_NODE_REGION", ""),
        "license_level": int(lvl) if (lvl or "").isdigit() else None,
        "private_key": os.environ.get("HYPC_NODE_PRIVATE_KEY", ""),
        "capabilities": _capabilities_from_env(),
    }


# --------------------------------------------------------------------------- #
# Mixin wired into the server base class.
# --------------------------------------------------------------------------- #
class OfferDocumentMixin:
    """Adds a signed ``/.well-known/hypercycle/offers.json`` endpoint.

    Configure via env vars (see :func:`node_config_from_env`) or by setting any of
    these attributes on your server: ``capabilities`` (dict), ``node_id``,
    ``node_endpoint``, ``node_region``, ``license_level``, ``node_private_key``.
    Set ``serve_offer_document = False`` to opt out entirely.
    """
    serve_offer_document = True

    def build_offer_document(self) -> dict:
        cfg = node_config_from_env()
        license_level = getattr(self, "license_level", None)
        if license_level is None:
            license_level = cfg["license_level"]
        doc = build_offer_document(
            getattr(self, "manifest_json", {}) or {},
            node_id=getattr(self, "node_id", "") or cfg["node_id"],
            endpoint=getattr(self, "node_endpoint", "") or cfg["endpoint"],
            region=getattr(self, "node_region", "") or cfg["region"],
            license_level=license_level,
            capabilities=getattr(self, "capabilities", None) or cfg["capabilities"],
        )
        private_key = getattr(self, "node_private_key", "") or cfg["private_key"]
        if private_key:
            try:
                doc = sign_offer_document(doc, private_key)
            except Exception as exc:  # never block startup over signing
                print(f"[offers] offer document left unsigned: {exc}")
        return doc

    def _register_offer_route(self, routes) -> None:
        """Append the offers route unless opted out or already overridden."""
        if not getattr(self, "serve_offer_document", True):
            return
        if any(getattr(r, "path", None) == WELL_KNOWN_PATH for r in routes):
            return
        self.offer_document_json = self.build_offer_document()
        routes.append(Route(
            WELL_KNOWN_PATH,
            lambda *args, **kwargs: JSONResponseCORS(self.offer_document_json),
            methods=["GET"],
        ))
