# ieee754_modbus_client.py
# ───────────────────────────────
# Part 1: Send IEEE754 float + CRC4 via Modbus
# Requirements:
#   pip install pymodbus

import struct
from pymodbus.client import ModbusTcpClient

# CRC-4 polynomial (x⁴ + x + 1) = 0b10011
def crc4(data_bits: str, poly='10011'):
    bits = list(map(int, data_bits + '0000'))  # append 4 zeros
    poly = list(map(int, poly))
    for i in range(len(data_bits)):
        if bits[i] == 1:
            for j in range(len(poly)):
                bits[i + j] ^= poly[j]
    return ''.join(str(x) for x in bits[-4:])

def float_to_ieee754_bin(value: float) -> str:
    packed = struct.pack('!f', value)      # network (= big endian) order
    return ''.join(f'{b:08b}' for b in packed)

def main():
    # 1️⃣ Ask user for number
    num = float(input("Pls input a floating point number: "))

    # 2️⃣ Convert to IEEE754
    ieee_bits = float_to_ieee754_bin(num)
    print(f"IEEE 754 representation of {num} is: {ieee_bits}")

    # 3️⃣ Compute CRC4
    crc_bits = crc4(ieee_bits)
    print(f"Output bits: {ieee_bits}{crc_bits} (with CRC4 appended)")
    print(f"CRC4: 0b{crc_bits}")

    # 4️⃣ Split into 2×16-bit registers
    reg1_bits = ieee_bits[:16]
    reg2_bits = ieee_bits[16:]
    print(f"two registers: ['{reg1_bits}', '{reg2_bits}']")

    reg1 = int(reg1_bits, 2)
    reg2 = int(reg2_bits, 2)
    crc_val = int(crc_bits, 2)
    registers = [reg1, reg2, crc_val]
    print(f"Final three Register: {registers}")

    # 5️⃣ Send via Modbus
    client = ModbusTcpClient("127.0.0.1", port=501)
    connection = client.connect()
    if not connection:
        print("❌ Could not connect to Modbus server.")
        return

    result = client.write_registers(0, registers)
    if result.isError():
        print("❌ Write failed:", result)
    else:
        print(f"✅ Registers {registers} written successfully starting at address 0.")

    client.close()

if __name__ == "__main__":
    main()
