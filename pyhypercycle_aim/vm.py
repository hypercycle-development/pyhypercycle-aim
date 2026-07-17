import json


class VMProgram:
    """
        Stub for VMPrograms in python. Additional functionality to be added later.
    """

def AIMCall(name, request, headers=None):
    if not headers:
        headers = {}
    return {"status": "aim_call", "aim": {"name": name}, "request": request, "headers": headers}
    return {"status": "aim_call", "aim": {"name": name, "address": "localhost:8000"}, "request": request}
    return {"status": "aim_call", "aim": {"name": name, "address": "localhost:8000", "version": ">0.2.1", "slot": 1}, "request": req}


def TMCall(action, request=None, headers=None, tm_type="nullpay"):
    """
        Yield-helper for the TM (Transaction Machine) side of the VM protocol. Mirrors
        AIMCall's shape exactly (a status-tagged dict, not a class) so a VM program's
        driving loop only needs one more `elif` branch to support it, not a rewrite.

        `action` is one of the TM contract's verbs: "info", "balance", "commit", "verify",
        "settle" (plus any host-specific extension verbs, e.g. "verify_with_retry" -- see
        verify_with_retry() below). `request` is the JSON body for that verb, e.g. for
        "commit": {"to_tm_address": ..., "to_tm_url": ..., "amount": ..., "task": ...}.

        A VM program calls this as:
            commit = yield TMCall("commit", {"to_tm_address": ..., "to_tm_url": ...,
                                              "amount": 10, "task": "..."})
        and the host resolves it against the node's own local TM container and sends the
        TM's JSON response back in as the yield's return value, exactly like AIMCall.

        `tm_type` selects WHICH of the node's TMs handles the call, for hosts that run more
        than one TM type side by side: "nullpay" (default; hold/settle contract) or "toda"
        (real twin payments, pay-then-trust contract -- verbs "info", "balance", "verify",
        "transfer"; no commit/settle, transfers are atomic). The default keeps every
        pre-existing nullpay VM program byte-identical in behavior.
    """
    if not headers:
        headers = {}
    return {"status": "tm_call", "tm": {"action": action, "type": tm_type},
            "request": request or {}, "headers": headers}


def verify_with_retry(twin_nonce, amount, root=None, tm_type="toda"):
    """
        Yield-FROM helper for a VM/brain program's pay-then-trust flow: verifies a
        twin-to-twin transfer, retrying with backoff if the payee's binder hasn't caught up
        yet. A transfer's funds move immediately, but the binder (what "verify" scans to
        confirm the transfer happened) can take a short moment to reflect a just-landed
        transfer -- calling verify immediately after a payment can see a binder that
        doesn't yet include the entry and fail closed even though the payment is completely
        valid.

        The retry/backoff loop itself runs host-side (dispatched via the
        "verify_with_retry" TM action), not in this generator. A generator-local
        `time.sleep` here would block the calling VM container's own async event loop for
        the whole retry window, stalling every other request that container is trying to
        serve -- this function is a thin pass-through to an async-safe host implementation
        rather than looping client-side.

        Any VM/brain program doing "pay, then immediately verify" should use this instead
        of a bare `yield TMCall("verify", ...)`. Usage inside a program's generator:

            verify = yield from verify_with_retry(nonce, amount, root)
            if not verify["ok"]:
                ...refuse, using verify["raw"] for the failure detail...

        Returns {"ok": bool, "raw": <the TM's own response dict, or None>}.
    """
    request = {"twin_nonce": twin_nonce, "amount": amount}
    if root is not None:
        request["root"] = root

    envelope = yield TMCall("verify_with_retry", request, tm_type=tm_type)
    result = envelope.get("result") if isinstance(envelope, dict) else None
    if isinstance(result, str):
        try:
            result = json.loads(result)
        except (ValueError, TypeError):
            result = None

    if isinstance(result, dict) and "ok" in result:
        return result
    return {"ok": False, "raw": result}
