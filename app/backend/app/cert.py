"""Create a self-signed certificate for HTTPS on the workshop network:

    python -m app.cert --host 192.168.1.20 --host workshop-pc --out storage/certs

Browsers will show a one-time warning for self-signed certificates; install the .crt on the devices to avoid it.
"""
import argparse
import ipaddress
from datetime import datetime, timedelta, timezone
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID


def make_cert(hosts: list[str], out: Path, days: int = 825) -> tuple[Path, Path]:
    out.mkdir(parents=True, exist_ok=True)
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, hosts[0] if hosts else "autocare")])
    san: list[x509.GeneralName] = []
    for h in hosts or ["localhost"]:
        try:
            san.append(x509.IPAddress(ipaddress.ip_address(h)))
        except ValueError:
            san.append(x509.DNSName(h))
    san += [x509.DNSName("localhost"), x509.IPAddress(ipaddress.ip_address("127.0.0.1"))]
    now = datetime.now(timezone.utc)
    cert = (x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(key.public_key())
            .serial_number(x509.random_serial_number()).not_valid_before(now - timedelta(minutes=5))
            .not_valid_after(now + timedelta(days=days)).add_extension(x509.SubjectAlternativeName(san), critical=False)
            .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
            .sign(key, hashes.SHA256()))
    crt, pem = out / "autocare.crt", out / "autocare.key"
    crt.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    pem.write_bytes(key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.TraditionalOpenSSL,
                                      serialization.NoEncryption()))
    return crt, pem


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", action="append", default=[], help="IP address or name clients will use (repeatable)")
    ap.add_argument("--out", default="storage/certs")
    a = ap.parse_args()
    crt, key = make_cert(a.host, Path(a.out))
    print(f"created {crt} and {key}\nset AUTOCARE_SSL_CERTFILE={crt}\nset AUTOCARE_SSL_KEYFILE={key}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
