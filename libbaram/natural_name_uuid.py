#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Natural Name string: custom base32 based UUID representation.
#
# Format: [variant_char][120bit_base32][version_char]
# - variant_char: base32 character representing UUID variant
# - 120bit_base32: base32 encoded 120-bit value (bits 0-47, 52-63, 68-127)
# - version_char: base32 character representing UUID version

import re
import uuid
import base64


BASE32_CHARS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567"

MATCH = re.compile(
    r'^[A-P]'
    r'[2-7A-Z]{24}'
    r'[A-P]', re.VERBOSE
)


def uuidToNnstr(value: uuid.UUID) -> str:
    """
    UUID to Natural Name String
    """
    uuid_int = value.int

    variant_bits = (uuid_int >> (127 - 67)) & 0xF  # Get bits 64-67
    version_bits = (uuid_int >> (127 - 51)) & 0xF  # Get bits 48-51

    # make compact 128bit integer

    upper_part  = (uuid_int >> 80) & ((1 << 48) - 1)
    middle_part = (uuid_int >> 64) & ((1 << 12) - 1)
    lower_part  =  uuid_int & ((1 << 60) - 1)

    compact_120bit = (upper_part << 72) | (middle_part << 60) | lower_part

    compact_bytes = compact_120bit.to_bytes(15, byteorder='big')

    base32_encoded = base64.b32encode(compact_bytes).decode('ascii')

    variant_char = BASE32_CHARS[variant_bits]
    version_char = BASE32_CHARS[version_bits]

    return variant_char + base32_encoded + version_char


def nnstrToUuid(nnstr: str) -> uuid.UUID:
    """
    Natural Name String to UUID
    """
    match = MATCH.match(nnstr)
    if not match:
        raise ValueError("Invalid base32 string: format mismatch")

    variant = BASE32_CHARS.index(nnstr[0])
    version = BASE32_CHARS.index(nnstr[-1])

    compact_bytes = base64.b32decode(nnstr[1:-1])
    compact_120bit = int.from_bytes(compact_bytes, byteorder='big')

    upper_part = (compact_120bit >> 72) & ((1 << 48) - 1)
    middle_part = (compact_120bit >> 60) & ((1 << 12) - 1)
    lower_part = compact_120bit & ((1 << 60) - 1)

    uuid_int = 0
    uuid_int |= upper_part << 80
    uuid_int |= version << 76
    uuid_int |= middle_part << 64
    uuid_int |= variant << 60
    uuid_int |= lower_part

    return uuid.UUID(int=uuid_int)


if __name__ == "__main__":
    # Test with different UUID versions
    test_uuids = [
        uuid.uuid4(),  # Random UUID (version 4)
        uuid.uuid1(),  # Time-based UUID (version 1)
        uuid.UUID('550e8400-e29b-41d4-a716-446655440000'),  # Known UUID
    ]

    print("UUID to Base32 String Conversion Tests:")
    print("=" * 50)

    for i, test_uuid in enumerate(test_uuids, 1):
        print(f"\nTest {i}:")
        print(f"Original UUID: {test_uuid}")
        print(f"UUID version:  {test_uuid.version}")
        print(f"UUID variant:  {test_uuid.variant}")

        # Convert to base32 string
        base32_str = uuidToNnstr(test_uuid)
        print(f"Base32 string: {base32_str}")
        print(f"String length: {len(base32_str)}")

        # Convert back to UUID
        reconstructed_uuid = nnstrToUuid(base32_str)
        print(f"Reconstructed: {reconstructed_uuid}")
        print(f"Match:         {test_uuid == reconstructed_uuid}")

        # Show the parts
        variant_char = base32_str[0]
        version_char = base32_str[-1]
        data_part = base32_str[1:-1]
        print(f"Parts: variant='{variant_char}', data='{data_part}', version='{version_char}'")

        if test_uuid != reconstructed_uuid:
            print("❌ MISMATCH!")
            print(f"Original int:  {test_uuid.int:032x}")
            print(f"Reconstructed: {reconstructed_uuid.int:032x}")
        else:
            print("✅ SUCCESS!")
