# pyhypercycle-aim

Python library for building **AIMs** (AI Modules) for the [HyperCycle](https://www.hypercycle.ai)
network. An AIM is a small ASGI service that exposes one or more priced endpoints plus a
self-describing `GET /manifest.json`. A HyperCycle node runs AIMs in numbered slots and a Node
Manager handles payment and routing.

## Quickstart

Subclass one of the server helpers (`SimpleServer`, `SimpleQueue`, `AsyncQueue`), set a `manifest`,
and decorate endpoints with `@aim_uri`:

```python
from pyhypercycle_aim import SimpleQueue, aim_uri, JSONResponseCORS

class Example(SimpleQueue):
    manifest = {"name": "Example", "short_name": "example", "version": "0.1",
                "license": "Open", "author": "you"}

    @aim_uri(uri="/model", methods=["POST"], endpoint_manifest={
        "input_body": {"text": "<Text>"}, "output": "<JSON>", "currency": "USD",
        "price_per_call": {"estimated_cost": 0.001, "min": 0, "max": 0.1},
        "price_per_mb":  {"estimated_cost": 0, "min": 0, "max": 0},
        "documentation": "Run the model.",
        "example_calls": [{"body": {"text": "hi"}, "method": "POST", "query": "",
                           "headers": "", "output": {"output": "hello"}}],
    })
    async def model(self, request):
        data = await request.json()
        return JSONResponseCORS({"output": data["text"].upper()})

Example().run(uvicorn_kwargs={"host": "0.0.0.0", "port": 4000})
```

This automatically serves `GET /manifest.json` describing the AIM and its per-endpoint pricing.
Send a `cost_only` header to any endpoint to get a `{min, max, estimated_cost, currency}` quote
without doing the work.

## Node Offer Document (discovery)

Every server also serves a **signed Node Offer Document** at:

```
GET /.well-known/hypercycle/offers.json
```

`/manifest.json` describes *one AIM*. The offer document describes *this node* — which AIMs it runs,
on what hardware, at what price — in one place that a discovery service or another agent can fetch to
answer **"where can I run AIM X, and for how much?"**. It is **signed with the node's Ethereum key**,
so any consumer can re-fetch it from the node and verify it independently; an index that caches it can
never forge or alter a price. The node stays the source of truth.

```jsonc
{
  "node": { "id": "0x…", "endpoint": "https://node.example:4000", "region": "eu-west",
            "license_level": 4 },
  "capabilities": { "gpus": 2, "gpu_model": "RTX 3090", "vram_gb": 48, "ram_gb": 128,
                    "cpu": "Ryzen 9 5950X", "bandwidth_mbps": 1000 },
  "aims": [ { "short_name": "example", "version": "0.1", "uri": "/model",
              "price_per_call": { "estimated_cost": 0.001, "min": 0, "max": 0.1 },
              "price_per_mb":   { "estimated_cost": 0, "min": 0, "max": 0 },
              "currency": "USD", "settles_in": [] } ],
  "issued_at": "2026-06-20T20:00:00Z",
  "signature": "0x…"        // EIP-191 personal_sign over the doc minus this field
}
```

### Configuration

The `aims` block is built automatically from each endpoint's manifest pricing — you don't repeat it.
Provide node identity, specs, and a signing key via **environment variables**:

| Variable | Meaning |
|---|---|
| `HYPC_NODE_ID` | node's wallet/identity address (auto-filled from the key if a private key is set) |
| `HYPC_NODE_ENDPOINT` | publicly reachable base URL of the node |
| `HYPC_NODE_REGION` | free-text region, e.g. `eu-west` |
| `HYPC_NODE_LICENSE_LEVEL` | integer license level |
| `HYPC_NODE_PRIVATE_KEY` | Ethereum private key used to **sign** the document |
| `HYPC_NODE_CAPABILITIES` | JSON object of self-declared hardware specs |

…or by setting attributes on your server class: `capabilities`, `node_id`, `node_endpoint`,
`node_region`, `license_level`, `node_private_key`.

If no private key is configured the document is still served, just **unsigned** (`signature` omitted).
Set `serve_offer_document = False` on your server to disable the endpoint entirely.

### Verifying (consumer / indexer side)

```python
from pyhypercycle_aim.offers import verify_offer_document
import httpx

doc = httpx.get("https://node.example:4000/.well-known/hypercycle/offers.json").json()
assert verify_offer_document(doc)   # True iff signed by node.id and untampered
```

Signing/verification use `eth_account` (already pulled in by the `web3` dependency).
