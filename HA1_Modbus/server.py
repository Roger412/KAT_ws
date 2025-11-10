#!/usr/bin/env python3
import asyncio
import logging
import struct
from pymodbus.server import StartAsyncTcpServer
from pymodbus.datastore import ModbusServerContext, ModbusDeviceContext,ModbusSequentialDataBlock
from pymodbus import ModbusDeviceIdentification

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("simple_modbus_server")

# CRC4 (default polynomial: x^4 + x + 1)
def crc4_bits(bitstr: str, poly: str = "10011") -> int:
    data = list(map(int, bitstr + "0000"))
    p = list(map(int, poly))
    for i in range(len(data) - len(p) + 1):
        if data[i] == 1:
            for j in range(len(p)):
                data[i + j] ^= p[j]
    rem_bits = data[-4:]
    return (rem_bits[0] << 3) | (rem_bits[1] << 2) | (rem_bits[2] << 1) | rem_bits[3]

def reg16_to_bits(r):
    return f"{r:016b}"

# Custom block that logs & validates writes to HR[0..2]
class LoggingHRBlock(ModbusSequentialDataBlock):
    def setValues(self, address, values):
        super().setValues(address, values)
        try:
            if len(self.values) < 3:
                return

            reg0 = self.values[0]  # HIGH 16 bits (address 0)
            reg1 = self.values[1]  # LOW  16 bits (address 1)
            reg2 = self.values[3]  # CRC4

            # Debug section — show exactly what we received
            log.info("────────── WRITE RECEIVED ──────────")
            log.info("Register[0] (High word): %d → %s", reg0, f"{reg0:016b}")
            log.info("Register[1] (Low  word): %d → %s", reg1, f"{reg1:016b}")
            log.info("Register[2] (CRC4 reg):  %d → %s", reg2, f"{reg2:016b}")

            # Build bitstring in high→low order (same as client)
            bits32 = f"{reg1:016b}" + f"{reg0:016b}"    
            log.info("Concatenated 32-bit string: %s", bits32)
            
            for i in range(10):
                log.info("HR[%d] = %d", i, self.values[i])

            # Compute CRC on that bitstring
            crc_calc = crc4_bits(bits32)
            crc_recv = reg2 & 0xF
            crc_calc_bits = f"{crc_calc:04b}"
            crc_recv_bits = f"{crc_recv:04b}"
            log.info("CRC computed = %s (%d)", crc_calc_bits, crc_calc)
            log.info("CRC received = %s (%d)", crc_recv_bits, crc_recv)

            if crc_calc != crc_recv:
                log.error("❌ CRC mismatch!")
                log.error("Bits used for CRC: %s", bits32)
                return

            # Combine into full 32-bit integer
            u32 = (reg0 << 16) | reg1
            log.info("Combined 32-bit int: %08X", u32)

            # Convert to bytes and unpack as float
            b = u32.to_bytes(4, byteorder="big", signed=False)
            (val,) = struct.unpack("!f", b)
            log.info("✅ CRC OK — decoded float value: %s", val)
            log.info("────────────────────────────────────")
        except Exception as e:
            log.exception("Error while processing write: %s", e)


async def main(port=1502):
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

    log.info("### start ASYNC server, listening on %d - tcp", port)
    await StartAsyncTcpServer(
        context=context,
        identity=identity,
        address=("0.0.0.0", port),
        framer="socket",
    )

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=1502)
    args = ap.parse_args()
    asyncio.run(main(args.port))
