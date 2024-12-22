import random
import string

def generate_random_name():
    return ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(10))