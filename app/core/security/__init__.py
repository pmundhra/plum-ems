"""Security and authentication"""

from app.core.security.jwt import (
    create_access_token,
    decode_access_token,
    get_current_user,
    get_optional_user,
    oauth2_scheme,
)
from app.core.security.hmac import (
    generate_hmac_signature,
    verify_hmac_signature,
    verify_webhook_signature,
    get_hmac_dependency,
)
from app.core.security.dependencies import (
    get_employer_id_from_user,
    require_role,
    require_any_role,
)

__all__ = [
    "create_access_token",
    "decode_access_token",
    "get_current_user",
    "get_optional_user",
    "oauth2_scheme",
    "generate_hmac_signature",
    "verify_hmac_signature",
    "verify_webhook_signature",
    "get_hmac_dependency",
    "get_employer_id_from_user",
    "require_role",
    "require_any_role",
]
