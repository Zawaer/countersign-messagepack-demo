"""Ed25519 keys for named owners.

Public keys live in keys/<name>.pub (committed). Demo private keys live in .keys/<name>.key
(gitignored, mode 0600). In a real deployment the private key stays on the owner's device or in a KMS.
"""

from __future__ import annotations

import base64
import binascii
import os
import re

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

from .common import Workspace


_NAME = re.compile(r"[a-z0-9][a-z0-9_-]{0,63}")


def _slug(name: str) -> str:
    """Owner name -> key file stem. Only [a-z0-9_-], so a signer name read from a ledger entry or a signed comment can
    never point outside keys/ (no `../`, no absolute path)."""
    slug = str(name).strip().lower()
    if not _NAME.fullmatch(slug):
        raise ValueError(f"invalid owner name {name!r} (letters, digits, '-' and '_' only)")
    return slug


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
    """Never raises on untrusted input: a bad name, a non-string or non-base64 signature is a failed verification."""
    try:
        slug = _slug(name)
    except ValueError as e:
        return False, str(e)
    path = ws.public_keys / f"{slug}.pub"
    if not path.exists():
        return False, f"no public key for {name} ({path})"
    try:
        if not isinstance(signature_b64, str):
            raise ValueError("signature is not a string")
        sig = base64.b64decode(signature_b64, validate=True)
        Ed25519PublicKey.from_public_bytes(base64.b64decode(path.read_text())).verify(sig, data)
        return True, "signature valid"
    except (InvalidSignature, ValueError, binascii.Error):
        return False, f"signature does not verify against keys/{slug}.pub"
