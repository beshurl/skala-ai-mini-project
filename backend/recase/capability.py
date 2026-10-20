"""Short-lived tool scopes, minted only by the trusted service."""
import base64
import binascii
import hashlib
import hmac
import json
import time


def mint(secret, owner, case_id, version):
    data = base64.urlsafe_b64encode(json.dumps({"owner": owner, "case_id": case_id, "version": version, "exp": time.time() + 300}, separators=(",", ":")).encode()).decode()
    return data + "." + hmac.new(secret.encode(), data.encode(), hashlib.sha256).hexdigest()


def verify(secret, token, case_id, version):
    try:
        data, sig = token.rsplit(".", 1)
        expected = hmac.new(secret.encode(), data.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, sig):
            raise ValueError()
        scope = json.loads(base64.urlsafe_b64decode(data))
        if scope["case_id"] != case_id or scope["version"] != version or scope["exp"] < time.time():
            raise ValueError()
        return scope["owner"]
    except (ValueError, KeyError, TypeError, binascii.Error, UnicodeDecodeError):
        raise PermissionError("TOOL_SCOPE_DENIED") from None
