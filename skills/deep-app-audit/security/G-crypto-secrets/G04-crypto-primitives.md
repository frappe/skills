# G04 — Roll-your-own crypto and weak primitives

**Scope:** every cryptographic operation the app performs itself.

**Why:** never roll your own crypto.

## Find
- `rg -n "hashlib|hmac|Fernet|cryptography|Crypto\.|base64|AES|DES|md5|sha1" --type py`
- MD5 or SHA-1 used for anything security-relevant (tokens, signatures, integrity) as opposed
  to cache keys.
- Password hashing: algorithm, work factor, salt, and whether it is a current standard.
- Symmetric encryption: mode (ECB is a finding), IV/nonce reuse, key derivation from a
  low-entropy input, missing authentication (encrypt-without-MAC).
- `==` comparing secrets instead of `hmac.compare_digest`.
- Base64 or obfuscation presented as encryption.

## Confirm
- Point at the standard alternative in the fix line.

## Report
Primitive, misuse, concrete consequence.
