def respond(message: str) -> str:
    return (
        "Thank you for contacting support.\n\n"
        f"I understand your issue: \"{message}\".\n"
        "I’m here to help. Let me look into this for you."
)

def reply_container_startup(message: str) -> str:
    return (
        "I understand you're seeing intermittent container startup errors.\n\n"
        "Here are the most common things to check:\n"
        "1) Host resources (CPU, RAM, disk space, inodes)\n"
        "2) Docker daemon health (restart Docker Desktop, check daemon logs)\n"
        "3) Port conflicts (verify required ports like 8000 are free)\n"
        "4) Image pulls (DNS, VPN, or registry access issues)\n"
        "5) Container logs ('docker logs <container>' - first error matters most)\n\n"
        "If you can share the exact error line and container logs, I can narrow this down quickly."
    )
