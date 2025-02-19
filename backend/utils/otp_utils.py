import random

class OTPUtils:
    @staticmethod
    def generate_otp(longitud=6):
        return int(''.join(str(random.randint(0, 9)) for _ in range(longitud)))
