"""Purpose-specific gates. Automatic cleaning never grants human approval."""
USES = {"training", "rag", "display", "redistribution"}


def approved_for(document, use):
    if use not in USES:
        return False
    return (document.get("state") == "APPROVED_FOR_SPECIFIC_USE"
            and document.get("permissions", {}).get(use) is True
            and document.get("privacy_review", {}).get("human_reviewed") is True
            and bool(document.get("privacy_review", {}).get("reviewer"))
            and (use != "training" or document.get("label_review", {}).get("human_reviewed") is True))
