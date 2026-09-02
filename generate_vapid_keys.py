"""Generate a VAPID key pair for the Render environment, once per deployment."""

import base64

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec


def base64url(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def main() -> None:
    private_key = ec.generate_private_key(ec.SECP256R1())
    private_number = private_key.private_numbers().private_value.to_bytes(32, "big")
    public_key = private_key.public_key().public_bytes(
        serialization.Encoding.X962,
        serialization.PublicFormat.UncompressedPoint,
    )
    print(f"VAPID_PUBLIC_KEY={base64url(public_key)}")
    print(f"VAPID_PRIVATE_KEY={base64url(private_number)}")
    print("VAPID_SUBJECT=mailto:operacao@seu-dominio.com")


if __name__ == "__main__":
    main()
