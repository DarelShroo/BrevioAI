import random
import time

class OTPUtils:
    @staticmethod
    def generate_otp(longitud=6):
        otp_random = int(''.join(str(random.randint(0, 9)) for _ in range(longitud)))
        
        now = int(time.strftime("%H%M"))
        
        result_otp = otp_random + now
        result_otp = result_otp % (10**longitud)
        
        return result_otp