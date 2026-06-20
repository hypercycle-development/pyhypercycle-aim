"""Tests for the node Offer Document (pyhypercycle_aim.offers)."""
import json

from eth_account import Account

from pyhypercycle_aim.offers import (
    build_offer_document,
    canonical,
    sign_offer_document,
    verify_offer_document,
    OfferDocumentMixin,
)

MANIFEST = {
    "name": "Example",
    "short_name": "example",
    "version": "0.1",
    "endpoints": [{
        "uri": "/model",
        "currency": "USD",
        "price_per_call": {"estimated_cost": 0.001, "min": 0, "max": 0.1},
        "price_per_mb": {"estimated_cost": 0, "min": 0, "max": 0},
    }],
}


def test_build_from_manifest():
    doc = build_offer_document(MANIFEST, node_id="0xabc", endpoint="http://n:4000",
                               capabilities={"gpus": 1})
    assert doc["node"]["id"] == "0xabc"
    assert doc["capabilities"] == {"gpus": 1}
    assert len(doc["aims"]) == 1
    o = doc["aims"][0]
    assert o["short_name"] == "example"
    assert o["version"] == "0.1"
    assert o["uri"] == "/model"
    assert o["price_per_call"]["estimated_cost"] == 0.001
    assert "issued_at" in doc


def test_canonical_excludes_signature_and_is_stable():
    doc = {"b": 2, "a": 1, "signature": "0xdead"}
    assert canonical(doc) == '{"a":1,"b":2}'


def test_sign_and_verify_roundtrip():
    acct = Account.create()
    doc = build_offer_document(MANIFEST, endpoint="http://n:4000")
    signed = sign_offer_document(doc, acct.key.hex())
    # node.id is filled in from the key when omitted
    assert signed["node"]["id"] == acct.address.lower()
    assert verify_offer_document(signed) is True


def test_tampered_price_fails_verification():
    acct = Account.create()
    signed = sign_offer_document(build_offer_document(MANIFEST), acct.key.hex())
    assert verify_offer_document(signed) is True
    # an index that alters the price can't keep the signature valid
    signed["aims"][0]["price_per_call"]["estimated_cost"] = 999
    assert verify_offer_document(signed) is False


def test_tampered_node_id_fails_verification():
    acct = Account.create()
    signed = sign_offer_document(build_offer_document(MANIFEST), acct.key.hex())
    signed["node"]["id"] = "0x0000000000000000000000000000000000000000"
    assert verify_offer_document(signed) is False


def test_unsigned_document_does_not_verify():
    doc = build_offer_document(MANIFEST, node_id="0xabc")
    assert "signature" not in doc
    assert verify_offer_document(doc) is False


def test_mixin_opt_out():
    class S(OfferDocumentMixin):
        serve_offer_document = False
        manifest_json = MANIFEST
    routes = []
    S()._register_offer_route(routes)
    assert routes == []


def test_mixin_registers_route_and_signs_from_attr():
    acct = Account.create()

    class S(OfferDocumentMixin):
        manifest_json = MANIFEST
        capabilities = {"gpus": 2, "gpu_model": "RTX 3090"}
        node_private_key = acct.key.hex()
        node_endpoint = "http://n:4000"

    s = S()
    routes = []
    s._register_offer_route(routes)
    assert len(routes) == 1
    assert routes[0].path == "/.well-known/hypercycle/offers.json"
    assert verify_offer_document(s.offer_document_json) is True
    assert s.offer_document_json["capabilities"]["gpu_model"] == "RTX 3090"
