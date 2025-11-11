#!/usr/bin/env python3

# This code was made by analyzing the code (with the help of AI) of the pymodbus repository's server_async example:
# https://github.com/pymodbus-dev/pymodbus/blob/dev/examples/simple_async_client.py

import asyncio
from pymodbus.server import StartAsyncTcpServer
from pymodbus.datastore import ModbusServerContext, ModbusDeviceContext,ModbusSequentialDataBlock
from pymodbus import ModbusDeviceIdentification

print("simple_modbus_server")

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

def ieee754_to_float_manual(bits: str) -> float:
    ####################### iee754 format ######################
    #  0             10000001          01110000000000000000000 
    # sign (1b)   exponent(8 bits)          mantissa (23 bits)
    ############################################################ 
    
    sign_bit = bits[0]
    exp_bits = bits[1:9]
    mantissa_bits = bits[9:]

    # Convert sign
    sign = -1 if sign_bit == '1' else 1

    # Exponent (remove bias 127)
    exponent = int(exp_bits, 2) - 127

    # Mantissa reconstruction
    mantissa = 1.0
    for i, bit in enumerate(mantissa_bits, start=1):
        if bit == '1':
            mantissa += 2 ** (-i)

    # result
    val = sign * mantissa * (2 ** exponent)
    return val

# Custom block that logs & validates writes to HR[0..2]
class LoggingHRBlock(ModbusSequentialDataBlock):
    def setValues(self, address, values):
        super().setValues(address, values)
        try:
            if len(self.values) < 3:
                return

            reg0 = self.values[1]  # HIGH 16 bits (address 0)
            reg1 = self.values[2]  # LOW  16 bits (address 1)
            reg2 = self.values[3]  # CRC4

            # Print received registers
            print("────────── WRITE RECEIVED ──────────")
            print(f"Register[0] (High word): {reg0:d} → {reg0:016b}")
            print(f"Register[1] (Low  word): {reg1:d} → {reg1:016b}")
            print(f"Register[2] (CRC4 reg):  {reg2:d} → {reg2:016b}")

            # Recontstruct binary number 
            bits32 = f"{reg0:016b}" + f"{reg1:016b}"    
            print("Concatenated 32-bit string: %s", bits32)
            
            for i in range(10):
                print("HR[%d] = %d", i, self.values[i])

            # Compute CRC on that bitstring
            crc_calc = int(compute_crc4(bits32), 2)
            crc_recv = reg2 & 0xF
            crc_calc_bits = f"{crc_calc:04b}"
            crc_recv_bits = f"{crc_recv:04b}"
            print(f"CRC computed = {crc_calc_bits} ({crc_calc})")
            print(f"CRC received = {crc_recv_bits} ({crc_recv})")

            if crc_calc != crc_recv:
                print("❌ CRC mismatch!")
                print(f"Bits used for CRC: {bits32}")
                return

            # Combine 16-bit words back into binary string
            bits32 = f"{reg0:016b}{reg1:016b}"
            print(f"Combined 32-bit binary: {bits32}")

            # Decode manually using your function
            val = ieee754_to_float_manual(bits32)

            print(f"✅ CRC OK — decoded float value (manual): {val}")
            print("────────────────────────────────────")

        except Exception as e:
            print(f"Error while processing write: {e}")


async def main():
    port=502
    hr_block = LoggingHRBlock(0, [0]*10)
    di = ModbusSequentialDataBlock(0, [0]*1)
    co = ModbusSequentialDataBlock(0, [0]*1)
    ir = ModbusSequentialDataBlock(0, [0]*1)

    context = ModbusServerContext(
        devices=ModbusDeviceContext(di=di, co=co, hr=hr_block, ir=ir),
        single=True,
    )

    identity = ModbusDeviceIdentification(info_name={
        "VendorName": "KAT",
        "ProductCode": "PM",
        "VendorUrl": "https://example.local/",
        "ProductName": "Simple Modbus Server",
        "ModelName": "Simple Modbus Server",
        "MajorMinorRevision": "1.0",
    })

    print(f"### start ASYNC server, listening on {port} - tcp")
    await StartAsyncTcpServer(
        context=context,
        identity=identity,
        address=("0.0.0.0", port),
        framer="socket",
    )

if __name__ == "__main__":
    asyncio.run(main())