#!/usr/bin/env python3
"""Generic decryptor for the common Android-app backup scheme:
Base64( AES-256/CBC/PKCS7( plaintext, key=SHA-256(password), IV=zeros ) )

Usage:
  .venv/bin/python aes_b64_decrypt.py FILE [PASSWORD]
  .venv/bin/python aes_b64_decrypt.py DIR          # decrypts all *.b64/*.enc via PASSWORDS dict
Edit PASSWORDS below per target app (grep jadx sources for the call sites).
Prints first bytes of plaintext as the correctness oracle — JSON should start with [ or {.
"""
import base64, hashlib, os, sys
from Crypto.Cipher import AES

# Per-app password table — fill from decompiled call sites.
PASSWORDS = {
    # 'source.json': 'wxaj19sd',   # 一本日记 example
}

ZERO_IV = bytes(16)

def derive_key(password: str) -> bytes:
    return hashlib.sha256(password.encode('utf-8')).digest()

def decrypt_bytes(cipher_bytes: bytes, password: str) -> bytes:
    pt = AES.new(derive_key(password), AES.MODE_CBC, ZERO_IV).decrypt(cipher_bytes)
    pad = pt[-1]
    if 1 <= pad <= 16 and pt[-pad:] == bytes([pad]) * pad:
        pt = pt[:-pad]
    return pt

def decrypt_file(path: str, password: str) -> bytes:
    raw = open(path, 'r', encoding='utf-8').read().strip()
    return decrypt_bytes(base64.b64decode(raw), password)

def main():
    target = sys.argv[1]
    pw_arg = sys.argv[2] if len(sys.argv) > 2 else None
    files = []
    if os.path.isdir(target):
        files = [os.path.join(target, f) for f in sorted(os.listdir(target))
                 if os.path.splitext(f)[1] in ('.b64', '.enc') or f in PASSWORDS]
    else:
        files = [target]
    for path in files:
        name = os.path.basename(path)
        pw = pw_arg or PASSWORDS.get(name)
        if not pw:
            print(f'skip {name}: no password (add to PASSWORDS or pass as argv[2])')
            continue
        pt = decrypt_file(path, pw)
        out = path + '.plain'
        open(out, 'wb').write(pt)
        head = pt[:100].decode('utf-8', errors='replace')
        print(f'{name}: {len(pt)}B -> {out}  head={head!r}')

if __name__ == '__main__':
    main()
