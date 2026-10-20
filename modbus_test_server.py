#!/usr/bin/env python3
"""A small Modbus TCP server for testing iModbus. No extra packages needed.

    python3 tools/modbus_test_server.py              # one device on port 5020
    python3 tools/modbus_test_server.py 5020 5021    # one simulated device per port

Each port has 1000 of each table. Live demo values (holding registers):
    0      seconds since start (counts up)
    1      sine wave, -1000..1000 (view as Signed)
    2-3    temperature as 32-bit float, ABCD order
    4-5    same temperature, CDAB order
    6-7    milliseconds since start, 32-bit unsigned, ABCD order
    10+    free for writing (10 starts at 1234)
Input registers 0-1 change too, and discrete inputs 0-1 toggle.
Unit ID 99 never answers, to test timeouts. Addresses past 999, and
holding/input registers 300-349 (an unmapped gap), return exception 02
(Illegal Data Address).
"""
import asyncio
import math
import struct
import sys
import time

SIZE = 1000
SILENT_UNIT = 99
REGISTER_GAP = range(300, 350)


class SimulatedDevice:
    def __init__(self, name):
        self.name = name
        self.start = time.monotonic()
        self.coils = [False] * SIZE
        self.discrete = [False] * SIZE
        self.holding = [0] * SIZE
        self.inputs = [0] * SIZE
        self.coils[0] = True
        self.holding[10] = 1234

    def update(self):
        t = time.monotonic() - self.start
        self.holding[0] = int(t) & 0xFFFF
        self.holding[1] = int(1000 * math.sin(t / 5)) & 0xFFFF
        high, low = struct.unpack(">HH", struct.pack(">f", 20 + 5 * math.sin(t / 10)))
        self.holding[2], self.holding[3] = high, low
        self.holding[4], self.holding[5] = low, high
        ms = int(t * 1000) & 0xFFFFFFFF
        self.holding[6], self.holding[7] = ms >> 16, ms & 0xFFFF
        self.inputs[0] = int(250 + 10 * math.sin(t))
        self.inputs[1] = int(t * 10) % 1000
        self.discrete[0] = int(t) % 2 == 0
        self.discrete[1] = int(t) % 4 < 2


def handle(device, pdu):
    """Returns the response PDU for a request PDU."""
    function = pdu[0]

    def exception(code):
        return bytes([function | 0x80, code])

    try:
        if function in (1, 2, 3, 4):
            address, quantity = struct.unpack(">HH", pdu[1:5])
            limit = 2000 if function in (1, 2) else 125
            if not 1 <= quantity <= limit:
                return exception(3)
            if address + quantity > SIZE:
                return exception(2)
            if function in (3, 4) and any(a in REGISTER_GAP for a in range(address, address + quantity)):
                return exception(2)
            device.update()
            table = {1: device.coils, 2: device.discrete, 3: device.holding, 4: device.inputs}[function]
            values = table[address:address + quantity]
            if function in (1, 2):
                packed = bytearray((quantity + 7) // 8)
                for i, on in enumerate(values):
                    if on:
                        packed[i // 8] |= 1 << (i % 8)
                return bytes([function, len(packed)]) + bytes(packed)
            return bytes([function, quantity * 2]) + struct.pack(">%dH" % quantity, *values)

        if function == 5:
            address, value = struct.unpack(">HH", pdu[1:5])
            if value not in (0xFF00, 0x0000):
                return exception(3)
            if address >= SIZE:
                return exception(2)
            device.coils[address] = value == 0xFF00
            return pdu[:5]

        if function == 6:
            address, value = struct.unpack(">HH", pdu[1:5])
            if address >= SIZE:
                return exception(2)
            device.holding[address] = value
            return pdu[:5]

        if function == 15:
            address, quantity, _ = struct.unpack(">HHB", pdu[1:6])
            if address + quantity > SIZE:
                return exception(2)
            data = pdu[6:]
            for i in range(quantity):
                device.coils[address + i] = bool(data[i // 8] >> (i % 8) & 1)
            return pdu[:5]

        if function == 16:
            address, quantity, _ = struct.unpack(">HHB", pdu[1:6])
            if address + quantity > SIZE:
                return exception(2)
            device.holding[address:address + quantity] = struct.unpack(">%dH" % quantity, pdu[6:6 + 2 * quantity])
            return pdu[:5]

        return exception(1)
    except (struct.error, IndexError):
        return exception(3)


async def serve_client(reader, writer, device):
    peer = writer.get_extra_info("peername")
    print(f"[{device.name}] client connected from {peer[0]}")
    try:
        while True:
            header = await reader.readexactly(7)
            transaction, _, length, unit = struct.unpack(">HHHB", header)
            pdu = await reader.readexactly(length - 1)
            if unit == SILENT_UNIT:
                continue
            response = handle(device, pdu)
            if pdu[0] in (5, 6, 15, 16):
                print(f"[{device.name}] write fc={pdu[0]} unit={unit} -> {response.hex(' ')}")
            writer.write(struct.pack(">HHHB", transaction, 0, len(response) + 1, unit) + response)
            await writer.drain()
    except (asyncio.IncompleteReadError, ConnectionResetError):
        pass
    finally:
        print(f"[{device.name}] client disconnected")
        writer.close()


async def main(ports):
    servers = []
    for port in ports:
        device = SimulatedDevice(f"port {port}")
        server = await asyncio.start_server(
            lambda r, w, d=device: serve_client(r, w, d), "0.0.0.0", port)
        servers.append(server)
        print(f"Modbus TCP test server listening on port {port}")
    print("Press Ctrl+C to stop.")
    await asyncio.gather(*(s.serve_forever() for s in servers))


if __name__ == "__main__":
    ports = [int(p) for p in sys.argv[1:]] or [5020]
    try:
        asyncio.run(main(ports))
    except KeyboardInterrupt:
        pass
