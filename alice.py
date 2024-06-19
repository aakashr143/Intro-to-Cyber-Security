from src.garbler import YaoGarbler
from src.util import GarblerSocket
from src.ot import ObliviousTransfer
import utils


class Alice(YaoGarbler):
    def __init__(self,
                 circuits: str,
                 oblivious_transfer=True,
                 bit_size=4,
                 inputs_file='inputs_alice.txt',
                 logs_file="logs_alice.json"
                 ):
        super().__init__(circuits)
        self.socket = GarblerSocket(logs_file)
        self.ot = ObliviousTransfer(self.socket, enabled=oblivious_transfer)

        self.inputs = utils.parse_input_file(inputs_file, bit_size)
        self.global_max = -1

    def start(self):
        for circuit in self.circuits:
            # send circuit info to bob
            self.socket.send_wait({
                "circuit": circuit["circuit"],
                "garbled_tables": circuit["garbled_tables"],
                "pbits_out": circuit["pbits_out"],
                "type": "circuit"
            })

            # start with evaluation
            self._evaluate(circuit)

        # evaluation complete
        self.socket.send_wait({
            'type': 'exit'
        })

    def _evaluate(self, message):
        circuit = message["circuit"]
        pbits = message["pbits"]
        keys = message["keys"]

        a_wires = circuit.get("alice", [])  # Alice's wires
        a_inputs = {}  # map from Alice's wires to (key, encr_bit) inputs
        b_wires = circuit.get("bob", [])  # Bob's wires
        b_keys = {  # map from Bob's wires to a pair (key, encr_bit)
            w: self._get_encr_bits(pbits[w], key0, key1)
            for w, (key0, key1) in keys.items() if w in b_wires
        }

        has_alice_exhausted = False
        has_bob_exhausted = False

        ctr = 0
        # loop until both parties have used their input at least once
        while not has_bob_exhausted or not has_alice_exhausted:
            # reset
            if ctr == len(self.inputs):
                ctr = 0
                has_alice_exhausted = True

            # get bob's input status and send self's status
            has_bob_exhausted = self.socket.send_wait({
                'type': 'exhausted',
                'value': has_alice_exhausted
            })

            # get current input, extract individual bits as int
            bits_a = [int(x) for x in self.inputs[ctr]]
            ctr += 1

            # map input to wires in circuit
            for i in range(len(a_wires)):
                a_inputs[a_wires[i]] = (keys[a_wires[i]][bits_a[i]], pbits[a_wires[i]] ^ bits_a[i])

            # evaluate circuit
            result = self.ot.get_result(a_inputs, b_keys)

            self.socket.messages.append({
                'type': 'intermediate result',
                'data': result
            })

            result_int = utils.parse_circuit_output(result)

            # update locally stored global max
            if result_int > self.global_max:
                self.global_max = result_int

    @staticmethod
    def _get_encr_bits(pbit, key0, key1):
        return (key0, 0 ^ pbit), (key1, 1 ^ pbit)


if __name__ == '__main__':
    import argparse
    import os

    parser = argparse.ArgumentParser(prog="Yao Protocol - Alice", description="Run Alice(Garbler) in yao protocol")
    parser.add_argument("-c", "--circuit", help="Path to circuit file", default="4bit_max.json")
    parser.add_argument("-b", "--bit-size", help="Number of input wires for a party in the circuit", default=4)
    parser.add_argument("-i", "--input-file", help="Path to input file (.txt)", default="inputs_alice.txt")
    parser.add_argument("-l", "--log-file", help="Path for log file (.json)", default="logs_alice.json")
    parser.add_argument("--disable-ot", action="store_true", help="Disables oblivious transfer")

    args = parser.parse_args()

    # Check args
    # Circuit
    if not os.path.exists(args.circuit):
        raise FileNotFoundError(f"Circuit file not found: {args.circuit}")

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

    a = Alice(
        circuits=args.circuit,
        oblivious_transfer=not args.disable_ot,
        bit_size=int(args.bit_size),
        inputs_file=args.input_file,
        logs_file=args.log_file
    )
    a.start()
    a.socket.create_logs_file()
    print(f'Computed global max: {a.global_max}')
