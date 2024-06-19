import threading
from alice import Alice
from bob import Bob


def alice_thread(circuits: str, oblivious_transfer: bool, bit_size: int, inputs_file: str, logs_file: str, results):
    a = Alice(circuits=circuits, oblivious_transfer=oblivious_transfer, bit_size=bit_size, inputs_file=inputs_file, logs_file=logs_file)
    a.start()
    a.socket.create_logs_file()
    print(f'Alice global max: {a.global_max}')
    results.append(a.global_max)


def bob_thread(oblivious_transfer: bool, bit_size: int, inputs_file: str, logs_file: str, results):
    b = Bob(oblivious_transfer=oblivious_transfer, bit_size=bit_size, inputs_file=inputs_file, logs_file=logs_file)
    b.start()
    b.socket.create_logs_file()
    print(f'Bob global max: {b.global_max}')
    results.append(b.global_max)


def verify(file_path, results, alice_input_file: str, bob_input_file: str):

    party_inputs = []
    with open(alice_input_file, "r") as file:
        party_inputs += [int(s) for s in file.readline().strip().split(" ")]

    with open(bob_input_file, "r") as file:
        party_inputs += [int(s) for s in file.readline().strip().split(" ")]

    with open(file_path, 'w') as file:

        # Alice and bob max matches
        if len(results) != 2 or results[0] != results[1]:
            print('Verification: 0')
            file.write('0')
            return

        # Alice and bob max matches with the max from file
        if max(party_inputs) != results[0]:
            print('Verification: 0')
            file.write('0')
            return

        print('Verification: 1')
        file.write('1')


if __name__ == '__main__':
    import argparse
    import os

    parser = argparse.ArgumentParser(prog="Yao Protocol with verification", description="Run in yao protocol for two parties")
    parser.add_argument("-c", "--circuit", help="Path to circuit file", default="4bit_max.json")
    parser.add_argument("-b", "--bit-size", help="Number of input wires for a party in the circuit", default=4)
    parser.add_argument('-ia', '--input_alice', help="Path to alice's input file", default="inputs_alice.txt")
    parser.add_argument('-ib', '--input_bob', help="Path to bob's input file", default="inputs_bob.txt")
    parser.add_argument('-la', '--log_alice', help="Path to alice's log file", default="logs_alice.json")
    parser.add_argument('-lb', '--log_bob', help="Path to bob's log file", default="logs_bob.json")
    parser.add_argument('-v', '--verify', help="Path to verification output file", default="verification.txt")
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
    if not os.path.exists(args.input_alice):
        raise FileNotFoundError(f"Input file file not found: {args.input_alice}")

    if ".txt" not in args.input_alice:
        raise Exception(f"Input file must be a .txt file: {args.input_alice}")

    if not os.path.exists(args.input_bob):
        raise FileNotFoundError(f"Input file file not found: {args.input_bob}")

    if ".txt" not in args.input_bob:
        raise Exception(f"Input file must be a .txt file: {args.input_bob}")

    # Log file
    if ".json" not in args.log_alice:
        raise Exception(f"Log file must be a .json file: {args.log_alice}")

    if ".json" not in args.log_bob:
        raise Exception(f"Log file must be a .json file: {args.log_bob}")

    # Verify
    if '.txt' not in args.verify:
        raise Exception(f"Verification file must be a .txt file: {args.verify}")

    # OT
    if not isinstance(args.disable_ot, bool):
        raise ValueError("Disable oblivious transfer must be of the type bool")

    outputs = []

    # Alice
    # circuits, oblivious_transfer, bit_size, inputs_file, logs_file, results
    t1 = threading.Thread(target=alice_thread, args=(args.circuit, not args.disable_ot, int(args.bit_size), args.input_alice, args.log_alice, outputs))

    # Bob
    # oblivious_transfer, bit_size, inputs_file, logs_file, results
    t2 = threading.Thread(target=bob_thread, args=(not args.disable_ot, int(args.bit_size), args.input_bob, args.log_bob, outputs))

    t1.start()
    t2.start()
    t1.join()
    t2.join()

    verify(args.verify, outputs, args.input_alice, args.input_bob)
