def calculate_crc8( data: bytes) -> int:
    """
    SAE J1850 CRC-8 calculation.
    Polynomial: 0x1D
    Initial value: 0xFF
    """
    crc = 0xFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 0x80:
                crc = (crc << 1) ^ 0x1D
            else:
                crc <<= 1
            crc &= 0xFF
    return crc ^ 0xFF