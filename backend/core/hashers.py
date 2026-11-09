"""Password hash support for accounts created by the original Desktop app."""

import hashlib

from django.contrib.auth.hashers import BasePasswordHasher, mask_hash
from django.utils.crypto import constant_time_compare


class LegacyDesktopPBKDF2PasswordHasher(BasePasswordHasher):
    """Verify the original PBKDF2-HMAC-SHA256 format, then upgrade on login.

    The Desktop app stored a 16-byte random salt as hex and a 32-byte digest as
    hex, using 200,000 PBKDF2 rounds. This format remains usable only so an
    imported account can authenticate once and Django can replace it with the
    configured Argon2 hasher through AbstractBaseUser.check_password().
    """

    algorithm = "aji_legacy_pbkdf2_sha256"
    iterations = 200_000

    def salt(self):
        # Hex is safe to store in Django's encoded hash and round-trips to the
        # exact bytes used by the old application.
        import secrets

        return secrets.token_hex(16)

    def encode(self, password, salt, iterations=None):
        rounds = int(iterations or self.iterations)
        digest = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), bytes.fromhex(salt), rounds
        ).hex()
        return f"{self.algorithm}${rounds}${salt}${digest}"

    def verify(self, password, encoded):
        try:
            algorithm, rounds, salt, expected = encoded.split("$", 3)
            if algorithm != self.algorithm:
                return False
            actual = self.encode(password, salt, int(rounds)).rsplit("$", 1)[1]
        except (TypeError, ValueError):
            return False
        return constant_time_compare(actual, expected)

    def decode(self, encoded):
        algorithm, rounds, salt, digest = encoded.split("$", 3)
        if algorithm != self.algorithm:
            raise ValueError("Not a legacy AJI password hash")
        return {
            "algorithm": algorithm,
            "iterations": int(rounds),
            "salt": salt,
            "digest": digest,
        }

    def safe_summary(self, encoded):
        decoded = self.decode(encoded)
        return {
            "algorithm": decoded["algorithm"],
            "iterations": decoded["iterations"],
            "salt": mask_hash(decoded["salt"]),
            "digest": mask_hash(decoded["digest"]),
        }

    def must_update(self, encoded):
        # A successful check invokes Django's setter and upgrades to Argon2.
        return True

    def harden_runtime(self, password, encoded):
        # The legacy iteration count is fixed and no longer used after login.
        return None
