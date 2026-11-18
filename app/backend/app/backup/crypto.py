"""Streaming authenticated encryption for backup archives (AES-256-GCM, scrypt key derivation).

File layout:  header | chunk*   where header = MAGIC(8) ver(1) log2n(1) r(1) p(1) salt(16) nonce_prefix(8)
Each chunk = len(4, big endian) + AES-GCM ciphertext+tag. The nonce is nonce_prefix + chunk counter; the
associated data binds the header, the chunk index and a "final chunk" flag, so tampering, reordering and
truncation are all detected. The passphrase is never stored: without it the archive cannot be recovered.
"""
import os
import struct
from pathlib import Path

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt

from app.backup.pgtools import BackupError

MAGIC = b"ACPBKENC"
VERSION = 1
CHUNK = 1024 * 1024
LOG2N, R, P = 15, 8, 1
HEADER_LEN = 8 + 4 + 16 + 8


def is_encrypted(path: Path) -> bool:
    with open(path, "rb") as f:
        return f.read(8) == MAGIC


def _key(passphrase: str, salt: bytes, log2n: int, r: int, p: int) -> bytes:
    return Scrypt(salt=salt, length=32, n=2 ** log2n, r=r, p=p).derive(passphrase.encode("utf-8"))


def _aad(header: bytes, index: int, final: bool) -> bytes:
    return header + struct.pack(">QB", index, 1 if final else 0)


def _nonce(prefix: bytes, index: int) -> bytes:
    return prefix + struct.pack(">I", index & 0xFFFFFFFF)


def encrypt_file(src: Path, dst: Path, passphrase: str) -> None:
    if len(passphrase) < 8:
        raise BackupError("كلمة سر التشفير يجب ألا تقل عن 8 أحرف")
    salt, prefix = os.urandom(16), os.urandom(8)
    header = MAGIC + bytes([VERSION, LOG2N, R, P]) + salt + prefix
    aes = AESGCM(_key(passphrase, salt, LOG2N, R, P))
    with open(src, "rb") as fin, open(dst, "wb") as fout:
        fout.write(header)
        index = 0
        cur = fin.read(CHUNK)
        while True:
            nxt = fin.read(CHUNK)
            final = not nxt
            ct = aes.encrypt(_nonce(prefix, index), cur, _aad(header, index, final))
            fout.write(struct.pack(">I", len(ct)) + ct)
            if final:
                break
            cur, index = nxt, index + 1
        fout.flush()
        os.fsync(fout.fileno())


def decrypt_file(src: Path, dst: Path, passphrase: str) -> None:
    with open(src, "rb") as fin:
        header = fin.read(HEADER_LEN)
        if len(header) < HEADER_LEN or header[:8] != MAGIC or header[8] != VERSION:
            raise BackupError("ملف نسخة احتياطية مشفر غير صالح")
        _, log2n, r, p = header[8], header[9], header[10], header[11]
        if log2n > 20 or r > 16 or p > 4:  # refuse absurd parameters from a tampered header
            raise BackupError("معاملات التشفير غير مقبولة")
        salt, prefix = header[12:28], header[28:36]
        aes = AESGCM(_key(passphrase, salt, log2n, r, p))
        try:
            with open(dst, "wb") as fout:
                index = 0
                while True:
                    raw = fin.read(4)
                    if len(raw) < 4:
                        raise BackupError("الملف المشفر ناقص أو تالف")
                    (n,) = struct.unpack(">I", raw)
                    if n < 16 or n > CHUNK + 16:
                        raise BackupError("الملف المشفر تالف")
                    ct = fin.read(n)
                    if len(ct) != n:
                        raise BackupError("الملف المشفر ناقص أو تالف")
                    final = fin.read(1) == b""
                    if not final:
                        fin.seek(-1, os.SEEK_CUR)
                    fout.write(aes.decrypt(_nonce(prefix, index), ct, _aad(header, index, final)))
                    if final:
                        break
                    index += 1
        except InvalidTag as e:
            dst.unlink(missing_ok=True)
            raise BackupError("كلمة السر غير صحيحة أو الملف تالف/معدّل") from e
        except BackupError:
            dst.unlink(missing_ok=True)
            raise
