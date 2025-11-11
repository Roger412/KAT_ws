import struct

import math

import pymodbus
from pymodbus.client import ModbusTcpClient


def float_2_ieee754_manual(val: float) -> str:
    
    ####################### iee754 format ######################
    #  0             10000001          01110000000000000000000 
    # sign (1b)   exponent(8 bits)          mantissa (23 bits)
    ############################################################ 

    # Check sign
    sign_bit = '0'
    if val < 0:
        sign_bit = '1'
        val = -val

    # Put value in binary scientific notation:
    exponent = 0
    mantissa = val

    while mantissa >= 2.0:
        mantissa /= 2.0
        exponent += 1
    while mantissa < 1.0:
        mantissa *= 2.0
        exponent -= 1

    #   exponent bias
    exp_bits = exponent + 127
    exp_bits_bin = f"{exp_bits:08b}"
    # print(exp_bits_bin)

    
    mantissa_bits = "" 
    mantissa -= 1.0 # subtract implicit 1
    # use multiply by 2 method to convert fraction (mantissa) to binary 
    for i in range(23): 
        mantissa *= 2
        if mantissa >= 1.0:
            mantissa_bits += "1"
            mantissa -= 1.0
        else:
            mantissa_bits += "0"

    # append sections
    result = sign_bit + exp_bits_bin + mantissa_bits 
    # print(result)

    return result

def compute_crc4(data_bits: str, polynom: str = "10011") -> str:

    ####
    # Compute CRC4 , default polynomial x^4 + x + 1 (0b10011)
    ####

    # append 4 zeros
    data_bits = data_bits + "0000"
    
    bits = []
    polynom_bits = []

    for i in range(len(data_bits)):
        bits.append(int(data_bits[i]))

    for i in range(len(polynom)):
        polynom_bits.append(int(polynom[i]))

    for i in range(len(bits) - len(polynom_bits) + 1):
        if bits[i] == 1:  # XOR the polynomial starting at every bit that is 1
            for j in range(len(polynom_bits)):
                bits[i + j] ^= polynom_bits[j]

    # last 4 bits will be the remainder
    remainder = ""
    for b in bits[-4:]:
        remainder = remainder + str(b)
    # print(remainder)

    return remainder


def main():
    num = float(input("Enter a floating-point number: "))

    # Convert to IEEE754 binary
    ieee_bits = float_2_ieee754_manual(num)
    print("IEEE754 (32 bits):", ieee_bits)

    # Compute CRC4
    crc_bits = compute_crc4(ieee_bits)
    print("CRC4 checksum:", crc_bits)

    # Split into two 16-bit registers
    reg1_bits = ieee_bits[:16]
    reg2_bits = ieee_bits[16:]

    # Convert to decimal (Modbus registers are 16-bit unsigned ints)
    reg1 = int(reg1_bits, 2)
    reg2 = int(reg2_bits, 2)
    crc_reg = int(crc_bits, 2)

    print("\n────────── REGISTER VALUES ──────────")
    print("Register 1 (bits 0–15):", reg1, "→", reg1_bits)
    print("Register 2 (bits 16–31):", reg2, "→", reg2_bits)
    print("CRC Register (4 bits):", crc_reg, "→", crc_bits)

    print(ieee_bits + crc_bits)

    print("\nSend these 3 registers via Modbus:")
    print(f"[{reg1}, {reg2}, {crc_reg}]")


    # ─────────────────────────────────────────────
    # SEND TO MODBUS SERVER
    # ─────────────────────────────────────────────

    # Create a TCP client to local server (default port 501)
    client = ModbusTcpClient("127.0.0.1", port=502)

    # Try connecting
    connection = client.connect()
    if not connection:
        print("❌ Could not connect to Modbus server.")
    else:
        print("✅ Connected to Modbus server at 127.0.0.1:501")

        # Prepare the 3 registers you computed earlier
        registers_to_send = [reg1, reg2, crc_reg]

        # Write them starting at holding-register address 0
        result = client.write_registers(0, registers_to_send)

        if result.isError():
            print("❌ Error sending registers:", result)
        else:
            print("✅ Registers successfully written!")
            print("Data sent:", registers_to_send)

        client.close()


if __name__ == "__main__":
    main()