

def parse_input_file(file_path: str, bit_size: int):
    """
    Reads the set of integers from the input file and returns them in their binary representation

    :param file_path: Path to input file for the party
    :param bit_size: The number of inputs to the circuit for a party
    :return: List[str] of number in binary (of size bit_size)
    """
    max_int = 2 ** bit_size

    with open(file_path, 'r') as file:
        contents = file.read().strip().split(' ')
        nums = [int(c) for c in contents]

        # If any number is out of range
        if any([n < 0 or max_int < n for n in nums]):
            raise ValueError("Input contains a number which is out of range")

        return [bin(n)[2:].zfill(bit_size) for n in nums]


def parse_circuit_output(result: dict):
    """
    Converts the output of the circuit (in binary) to a number in base 10

    :param result: Output of the circuit as a dict
    :return: A number in base 10 representing the output of the circuit
    """
    output_str = ''.join([str(result[k]) for k in result.keys()])
    output_str = output_str[::-1]
    return int(output_str, 2)
