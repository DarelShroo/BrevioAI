import secrets
import time


class OTPUtils:
    @staticmethod
    def generate_otp(longitud: int = 6) -> int:
        """Cryptographically secure numeric OTP (fixed width)."""
        if longitud < 4 or longitud > 10:
            raise ValueError("OTP length must be between 4 and 10")
        upper = 10**longitud
        # secrets.randbelow avoids modulo bias from random.randint.
        return secrets.randbelow(upper - 1) + 1

    @staticmethod
    def constant_time_equals(left: int | str | None, right: int | str | None) -> bool:
        left_s = str(left or "")
        right_s = str(right or "")
        # Pad to equal length so compare_digest never raises; still leaks length.
        width = max(len(left_s), len(right_s), 1)
        return secrets.compare_digest(left_s.zfill(width), right_s.zfill(width))
