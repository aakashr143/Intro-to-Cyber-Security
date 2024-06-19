import json
import operator
import random
import secrets
import sympy
import zmq

# SOCKET
LOCAL_PORT = 4080
SERVER_HOST = "localhost"
SERVER_PORT = 4080


# ADDED
def transform_data(obj):
    """
    transforms the input object so that it can be written into a JSON file
    :param obj:
    :return: transformed obj
    """
    if isinstance(obj, bytes):
        return obj.hex()  # Convert bytes to a hex string
    elif isinstance(obj, dict):
        return {transform_data(key): transform_data(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [transform_data(element) for element in obj]
    elif isinstance(obj, tuple):
        return ", ".join([str(transform_data(element)) for element in obj])
    elif isinstance(obj, PrimeGroup):
        return obj.to_json()
    else:
        return obj


# UPDATED
class Socket:
    def __init__(self, socket_type, logs_file):
        self.socket = zmq.Context().socket(socket_type)
        self.poller = zmq.Poller()
        self.poller.register(self.socket, zmq.POLLIN)

        self.logs_file = logs_file
        self.messages = []

    # UPDATED
    def send(self, msg):
        self.messages.append({
            'type': 'communication',
            'direction': 'send',
            'data': transform_data(msg)
        })
        self.socket.send_pyobj(msg)

    # UPDATED
    def receive(self):
        rcv = self.socket.recv_pyobj()

        self.messages.append({
            'type': 'communication',
            'direction': 'receive',
            'data': transform_data(rcv)
        })
        return rcv

    def send_wait(self, msg):
        self.send(msg)
        return self.receive()

    # ADDED
    def create_logs_file(self):
        with open(self.logs_file, 'w') as file:
            data = json.dumps(transform_data(self.messages), indent=4)
            file.write(data)

    """
    From https://stackoverflow.com/questions/17174001/stop-pyzmq-receiver-by-keyboardinterrupt
    """

    # UPDATED
    def poll_socket(self, timetick=100):
        try:
            while True:
                obj = dict(self.poller.poll(timetick))
                if self.socket in obj and obj[self.socket] == zmq.POLLIN:
                    rcv = self.socket.recv_pyobj()
                    self.messages.append({
                        'type': 'communication',
                        'direction': 'receive',
                        'data': transform_data(rcv)
                    })
                    yield rcv
        except KeyboardInterrupt:
            pass


class EvaluatorSocket(Socket):
    def __init__(self, logs_file, endpoint=f"tcp://*:{LOCAL_PORT}"):
        super().__init__(zmq.REP, logs_file)
        self.socket.bind(endpoint)


class GarblerSocket(Socket):
    def __init__(self, logs_file, endpoint=f"tcp://{SERVER_HOST}:{SERVER_PORT}"):
        super().__init__(zmq.REQ, logs_file)
        self.socket.connect(endpoint)


# PRIME GROUP
PRIME_BITS = 64  # order of magnitude of prime in base 2


def next_prime(num):
    """Return next prime after 'num' (skip 2)."""
    return 3 if num < 3 else sympy.nextprime(num)


def gen_prime(num_bits):
    """Return random prime of bit size 'num_bits'"""
    r = secrets.randbits(num_bits)
    return next_prime(r)


def xor_bytes(seq1, seq2):
    """XOR two byte sequence."""
    return bytes(map(operator.xor, seq1, seq2))


def bits(num, width):
    """Convert number into a list of bits."""
    return [int(k) for k in f'{num:0{width}b}']


class PrimeGroup:
    """Cyclic abelian group of prime order 'prime'."""

    def __init__(self, prime=None):
        self.prime = prime or gen_prime(num_bits=PRIME_BITS)
        self.prime_m1 = self.prime - 1
        self.prime_m2 = self.prime - 2
        self.generator = self.find_generator()

    def mul(self, num1, num2):
        "Multiply two elements." ""
        return (num1 * num2) % self.prime

    def pow(self, base, exponent):
        "Compute nth power of an element." ""
        return pow(base, exponent, self.prime)

    def gen_pow(self, exponent):  # generator exponentiation
        "Compute nth power of a generator." ""
        return pow(self.generator, exponent, self.prime)

    def inv(self, num):
        "Multiplicative inverse of an element." ""
        return pow(num, self.prime_m2, self.prime)

    def rand_int(self):  # random int in [1, prime-1]
        "Return an random int in [1, prime - 1]." ""
        return random.randint(1, self.prime_m1)

    def find_generator(self):  # find random generator for group
        """Find a random generator for the group."""
        factors = sympy.primefactors(self.prime_m1)

        while True:
            candidate = self.rand_int()
            for factor in factors:
                if 1 == self.pow(candidate, self.prime_m1 // factor):
                    break
            else:
                return candidate

    # ADDED
    def to_json(self):
        return {
            'object': 'PrimeGroup',
            'prime': self.prime,
            'prime_m1': self.prime_m1,
            'prime_m2': self.prime_m2,
            'generator': self.generator
        }


# HELPER FUNCTIONS
def parse_json(json_path):
    with open(json_path) as json_file:
        return json.load(json_file)
