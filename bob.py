from src.util import EvaluatorSocket
from src.ot import ObliviousTransfer
import utils


class Bob:
    def __init__(self,
                 oblivious_transfer=True,
                 bit_size=4,
                 inputs_file='inputs_bob.txt',
                 logs_file="logs_bob.json"
                 ):
        self.socket = EvaluatorSocket(logs_file)
        self.ot = ObliviousTransfer(self.socket, enabled=oblivious_transfer)

        self.inputs = utils.parse_input_file(inputs_file, bit_size)
        self.global_max = -1

    def start(self):
        for message in self.socket.poll_socket():
            if message['type'] == 'circuit':
                self.socket.send(True)
                self._evaluate(message)  # start with evaluation
            elif message['type'] == 'exit':  # evaluation complete
                self.socket.send(True)
                break

    def _evaluate(self, message):
        circuit = message["circuit"]
        pbits_out = message["pbits_out"]
        garbled_tables = message["garbled_tables"]

        b_wires = circuit.get("bob", [])  # list of Bob's wires

        has_alice_exhausted = False
        has_bob_exhausted = False

        ctr = 0
        # loop until both parties have used their input at least once
        while not has_bob_exhausted or not has_alice_exhausted:
            # reset
            if ctr == len(self.inputs):
                ctr = 0
                has_bob_exhausted = True

            # get alice's input status
            data = self.socket.receive()

            # send self's status to alice
            if data['type'] == 'exhausted':
                self.socket.send(has_bob_exhausted)
                has_alice_exhausted = data['value']
            else:
                raise Exception("Invalid message type")

            # get current input, extract individual bits as int
            bits_b = [int(x) for x in self.inputs[ctr]]
            ctr += 1

            # map input to wires in circuit
            b_inputs_clear = {
                b_wires[i]: bits_b[i]
                for i in range(len(b_wires))
            }

            # evaluate circuit
            result = self.ot.send_result(circuit, garbled_tables, pbits_out, b_inputs_clear)

            self.socket.messages.append({
                'type': 'intermediate result',
                'data': result
            })

            result_int = utils.parse_circuit_output(result)

            # update locally stored global max
            if result_int > self.global_max:
                self.global_max = result_int


if __name__ == '__main__':
    import argparse
    import os

    parser = argparse.ArgumentParser(prog="Yao Protocol - Bob", description="Run Bob(Evaluator) in yao protocol")
    parser.add_argument("-b", "--bit-size", help="Number of input wires for a party in the circuit", default=4)
    parser.add_argument("-i", "--input-file", help="Path to input file (.txt)", default="inputs_bob.txt")
    parser.add_argument("-l", "--log-file", help="Path for log file (.json)", default="logs_bob.json")
    parser.add_argument("--disable-ot", action="store_true", help="Disables oblivious transfer")

    args = parser.parse_args()

    # Check args
    # Bits size for circuit
    if not isinstance(int(args.bit_size), int):
        raise ValueError("Bit size must be of the type int")

    # Input file
    if not os.path.exists(args.input_file):
        raise FileNotFoundError(f"Input file file not found: {args.input_file}")

    if ".txt" not in args.input_file:
        raise Exception(f"Input file must be a .txt file: {args.input_file}")

    # Log file
    if ".json" not in args.log_file:
        raise Exception(f"Log file must be a .json file: {args.log_file}")

    # OT
    if not isinstance(args.disable_ot, bool):
        raise ValueError("Disable oblivious transfer must be of the type bool")

    b = Bob(
        oblivious_transfer=not args.disable_ot,
        bit_size=int(args.bit_size),
        inputs_file=args.input_file,
        logs_file=args.log_file
    )
    b.start()
    b.socket.create_logs_file()
    print(f'Computed global max: {b.global_max}')

