ISSUE_LOGIN = "login"
ISSUE_BILLING = "billing"
ISSUE_SHIPPING = "shipping"
ISSUE_REFUND = "refund"
ISSUE_OTHER = "other"

ISSUE_VALUES = {
    ISSUE_LOGIN,
    ISSUE_BILLING,
    ISSUE_SHIPPING,
    ISSUE_REFUND,
    ISSUE_OTHER,
}

# aims/issue_classifier/aim.py

LOGIN_HINTS = {
    "login", "log in", "sign in", "signin", "password", "reset", "2fa",
    "iniciar", "iniciar sesion", "iniciar sesión", "contraseña", "cuenta"
}

BILLING_HINTS = {
    "bill", "billing", "charge", "charged", "payment", "invoice", "refund",
    "card", "credit card", "subscription", "cancel", "canceled",
    "cobro", "cobrado", "pago", "factura", "tarjeta", "suscripción", "suscripcion", "cancelar"
}

SHIPPING_HINTS = {
    "shipping", "ship", "delivery", "delivered", "tracking", "order", "package",
    "late", "where is my", "eta",
    "envio", "envío", "entrega", "entregado", "rastreo", "seguimiento", "pedido", "paquete"
}

REFUND_HINTS = {
    "refund", "return", "exchange", "money back",
    "reembolso", "devolucion", "devolución", "cambio", "devolver"
}

def classify_issue(message: str) -> str:
    t = message.lower()

    if any(h in t for h in LOGIN_HINTS):
        return "login"

    if any(h in t for h in BILLING_HINTS):
        return "billing"

    if any(h in t for h in SHIPPING_HINTS):
        return "shipping"

    if any(h in t for h in REFUND_HINTS):
        return "refund"

    return "other"

