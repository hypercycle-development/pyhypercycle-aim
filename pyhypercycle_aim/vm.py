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

