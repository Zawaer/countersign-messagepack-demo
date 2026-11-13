"""Ed25519 keys for named owners.

Public keys live in keys/<name>.pub (committed). Demo private keys live in .keys/<name>.key
(gitignored, mode 0600). In a real deployment the private key stays on the owner's device or in a KMS.
"""

from __future__ import annotations

import base64
import os

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

from .common import Workspace


def _slug(name: str) -> str:
    return name.strip().lower()


def keygen(ws: Workspace, name: str, force: bool = False) -> tuple[str, str]:
    priv_path = ws.private_keys / f"{_slug(name)}.key"
    pub_path = ws.public_keys / f"{_slug(name)}.pub"
    if priv_path.exists() and not force:
        raise FileExistsError(f"{priv_path} exists (use --force to replace it)")
    key = Ed25519PrivateKey.generate()
    raw_priv = key.private_bytes(serialization.Encoding.Raw, serialization.PrivateFormat.Raw, serialization.NoEncryption())
    raw_pub = key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    ws.private_keys.mkdir(parents=True, exist_ok=True)
    ws.public_keys.mkdir(parents=True, exist_ok=True)
    priv_path.write_text(base64.b64encode(raw_priv).decode() + "\n")
    os.chmod(priv_path, 0o600)
    pub_path.write_text(base64.b64encode(raw_pub).decode() + "\n")
    return str(priv_path), str(pub_path)


def sign(ws: Workspace, name: str, data: bytes) -> str:
    path = ws.private_keys / f"{_slug(name)}.key"
    if not path.exists():
        raise FileNotFoundError(f"no private key for {name} ({path}); run: countersign keygen --name {name}")
    key = Ed25519PrivateKey.from_private_bytes(base64.b64decode(path.read_text()))
    return base64.b64encode(key.sign(data)).decode()


def verify(ws: Workspace, name: str, data: bytes, signature_b64: str) -> tuple[bool, str]:
    path = ws.public_keys / f"{_slug(name)}.pub"
    if not path.exists():
        return False, f"no public key for {name} ({path})"
    try:
        Ed25519PublicKey.from_public_bytes(base64.b64decode(path.read_text())).verify(base64.b64decode(signature_b64), data)
        return True, "signature valid"
    except (InvalidSignature, ValueError):
        return False, f"signature does not verify against keys/{_slug(name)}.pub"
