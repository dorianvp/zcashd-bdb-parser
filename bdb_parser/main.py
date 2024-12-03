import binascii
import re
from asn1crypto.keys import PublicKeyInfo
import argparse
from secp256k1 import PrivateKey

PUBLIC_KEY_LEN = 33  # Compressed secp256k1 public key length
PRIVATE_KEY_LEN = 32  # secp256k1 private key length


def hex_to_ascii(hex_string) -> str | None:
    """Convert a hexadecimal string to ASCII if possible."""
    try:
        ascii_text = binascii.unhexlify(hex_string).decode("utf-8", errors="ignore")
        if all(
            32 <= ord(c) <= 126 or c in "\n\t\r" for c in ascii_text
        ):  # Printable characters
            return ascii_text.strip()
    except (binascii.Error, UnicodeDecodeError):
        pass
    return None


def parse_asn1_data(hex_string) -> dict | None:
    """Parse ASN.1 DER data, such as cryptographic keys."""
    try:
        data = bytearray.fromhex(hex_string)

        # Parse PrivateKey
        # Split data
        vch_privkey = bytes(data)[:PRIVATE_KEY_LEN]
        _hashed_data = data[PRIVATE_KEY_LEN:]

        # Try parsing as ECPrivateKey
        try:
            private_key = PrivateKey(vch_privkey, raw=True)

            return {
                "type": "ECPrivateKey",
                "private_key": private_key.serialize(),
                "public_key": None,
            }
        except Exception:
            pass

        # Try parsing as PublicKeyInfo
        try:
            public_key = PublicKeyInfo.load(data)
            return {
                "type": "ECPublicKey",
                "public_key": public_key["public_key"].native.hex(),
            }
        except Exception:
            pass

        return None
    except binascii.Error:
        return None


def analyze_dump(dump) -> list:
    """Analyze the Berkeley DB wallet dump."""
    results = []
    lines = dump.splitlines()

    for i in range(0, len(lines) - 1, 2):
        line = lines[i].strip()
        value_line = lines[i + 1].strip()
        # First byte is always the length of the key
        length = int(line[0:2], 16)
        key_match = re.match(r"([0-9a-fA-F]+)(.*)$", line[2 : length * 2 + 2])
        value_match = re.match(r"([0-9a-fA-F]+)(.*)$", line[length * 2 + 2 :])

        key = None
        value = None
        if key_match is not None:
            key = key_match.group(1)
        if value_match is not None:
            value = re.match(r"([0-9a-fA-F]+)(.*)$", line[length * 2 + 2 :]).group(1)

        key_ascii = hex_to_ascii(key)

        parsed_value = None
        if key_ascii == "key":
            parsed_value = parse_asn1_data(value_line)

        results.append(
            {
                # "key": key,
                "key_ascii": key_ascii,
                "value": value,
                "parsed_value": parsed_value,
            }
        )

    return results


def get_chunks(input_text) -> dict:
    """
    Processes the input text in multiple steps to parse key-value pairs.

    :param input_text: str - The input text to parse.
    :return: dict - A dictionary of parsed key-value pairs.
    """
    lines = input_text.splitlines()

    result = {}

    data = []
    cleaned_lines = [line.strip() for line in lines if line.strip()]

    regex = r"^([\w_]+)\s*=\s*([\w\d]+)$"
    key_value_pairs = []
    for line in cleaned_lines:
        match = re.match(regex, line)
        if match:
            key_value_pairs.append((match.group(1), match.group(2)))
        else:
            data.append(line)

    result = {key: value for key, value in key_value_pairs}

    result["data"] = "\n".join(data)

    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--file",
        # type=argparse.FileType("r"),
        required=False,
        help="The input file to parse (e.g., wallet.dat)",
        default=None,
    )
    args = parser.parse_args()

    if hasattr(args, "file") and args.file:
        with open(args.file, "r") as f:
            wallet_dump = f.read()
    else:
        print("INFO: Using example wallet dump.\n")

        wallet_dump = """
        VERSION=3
        format=bytevalue
        database=main
        type=btree
        db_pagesize=4096
        HEADER=END
        036b6579210210933eeae2f5cc26a7938ff2e1a9502b41addba6c7f41cfedca0f8a77dcd0a3e
        d63081d302010104207d13492d7b76c967c03d86faa5e982676c6705593a806fb832504aa4e45b87e9a08185308182020101302c06072a8648ce3d0101022100fffffffffffffffffffffffffffffffffffffffffffffffffffffffefffffc2f300604010004010704210279be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f81798022100fffffffffffffffffffffffffffffffebaaedce6af48a03bbfd25e8cd0364141020101a1240322000210933eeae2f5cc26a7938ff2e1a9502b41addba6c7f41cfedca0f8a77dcd0a3e686d1462708b375128ab31d82191db6923ea9fca1c278ae9bae955fdc4375edc
        036b657921022094799b330f1f0da42d71b03348fd17a6ea703dc09c2f4833944fd70c9aba1d
        d63081d30201010420f05b74def5f5e1026b48171ff92b0372e939499bc960f4711273938d0198cc33a08185308182020101302c06072a8648ce3d0101022100fffffffffffffffffffffffffffffffffffffffffffffffffffffffefffffc2f300604010004010704210279be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f81798022100fffffffffffffffffffffffffffffffebaaedce6af48a03bbfd25e8cd0364141020101a124032200022094799b330f1f0da42d71b03348fd17a6ea703dc09c2f4833944fd70c9aba1d2a52e915863a0ec416bca04db628235a4e580f81502238e4c3ba9399131153ed
        046e616d6523746d455667704735744333516a786b4d34774d47585a704c70714d4677654258316233
        00
        04706f6f6c0100000000000000
        b28d5b00bee4466700000000210210933eeae2f5cc26a7938ff2e1a9502b41addba6c7f41cfedca0f8a77dcd0a3e
        076b65796d657461210210933eeae2f5cc26a7938ff2e1a9502b41addba6c7f41cfedca0f8a77dcd0a3e
        0a000000bee4466700000000186d2f3434272f31272f32313437343833363437272f312f30f40d2214997564f1a47289f39678f353524d456cd35ce71574aabefa2fa9c012
        076b65796d65746121022094799b330f1f0da42d71b03348fd17a6ea703dc09c2f4833944fd70c9aba1d
        0a000000bee4466700000000186d2f3434272f31272f32313437343833363437272f302f30f40d2214997564f1a47289f39678f353524d456cd35ce71574aabefa2fa9c012
        07707572706f736523746d455667704735744333516a786b4d34774d47585a704c70714d4677654258316233
        0772656365697665
        0776657273696f6e
        b28d5b00
        0962657374626c6f636b
        b28d5b0000
        0a64656661756c746b6579
        21022094799b330f1f0da42d71b03348fd17a6ea703dc09c2f4833944fd70c9aba1d
        0a6d696e76657273696f6e
        60ea0000
        0b6e6574776f726b696e666f
        055a636173680772656774657374
        0e6d6e656d6f6e6963706872617365f40d2214997564f1a47289f39678f353524d456cd35ce71574aabefa2fa9c012
        00000000a17072696f726974792061726d65642067756974617220636f6e76696e636520756e7665696c206569746865722061696d2073686564206c6f75642073656c656374206561676c65206a6f75726e657920616e696d616c20627269636b20666573746976616c2073617665206c75676761676520626174746c6520686f757220706872617365206e6574776f726b2068796272696420636c617269667920636c6179
        0f6d6e656d6f6e69636864636861696e
        01000000f40d2214997564f1a47289f39678f353524d456cd35ce71574aabefa2fa9c012bee44667000000000000000001000000010000000000000000
        107769746e657373636163686573697a65
        6400000000000000
        1262657374626c6f636b5f6e6f6d65726b6c65
        b28d5b00138c2d0261f1350242b0d4f9894f6102bf87da18d7c6a25c18ef07ab7ab45fd00709537de7da7a6fee7284dfcc84e0bff407e9dab6a48163f9ab9ae01a15c4e30a388fe7a3207fb83fc1fd841c59b7650ac46e3833f9d49ecd7c9ef1dd74620908199548402f3f9587b5861966f2fb5f0db4f453fe1369a9217b953c2dbb165e05cc8c708a51325db4f4336142f656d5436276c5541ad8985c5b8153ea6e764e0366d7f0ea52de56198f29276d3a65041756c4c3eec0e7d2a285ec695e1d128805ad493ed3dbefce4e11c09c4ad0b1dc480bdc4c90306bb67ad0882a4427dbb802dd8eba6dc26b0bb0d5ae925f87f26116d35b6723ea84383f17907671d2f1ec012bfeb4acddc2fdc7264862b7599ea0515361ee15af19ac11beb73ee839d5a1050a08e8352f5a59bdbcab7d8a78c1cc103df6d5aee7c40db4eeab67c0fcaa4507dd989f5ff84e7a45f1a146f4a1cc1cfeb390f9d15a4583fb1b5257e3e4b0d10d0f3017bccd3eeead2e2ca4907394ab4ead088b66ee68657ce85881ffc691f500f31c4a5e07a5f1153e319c78ab1f3fddb914d1336b1597d230261af655ef9a053d33034bc6c1d0fbc0b89cba088bdec36b8ecdc3948b7a71f4fdae4d4e2ad40a301c05049624b5911da3a836071d0b41f42cc29afd308fb8e040ab97215a280d7549b51f07a5341c7a4ad1f3dc9e69a18a8d8a9012276e81d5e4fe613ae149065c828d303bd29ca42b0cd53ea51ebe4d5fa8f83372506cb8dcfce239a2bc010a9bf41bf9e248c95dd151d72840d7845baf0898560e0ce18211e1d6fa9402100b27e30134d620e9fe61f719938320bab63e7e72c91b5e23025676f90ed8119f02
        1c6f7263686172645f6e6f74655f636f6d6d69746d656e745f74726565
        b28d5b0001000300000000640000000000000000
        DATA=END
        """

    results = get_chunks(wallet_dump)

    analysis_result = analyze_dump(results["data"])

    for entry in analysis_result:
        if entry["key_ascii"] is not None:
            print("Key:", entry["key_ascii"])
            print("Value: ", entry["value"])
            if entry["parsed_value"] is not None:
                print("Parsed Value: ", entry["parsed_value"])


if __name__ == "__main__":
    main()
