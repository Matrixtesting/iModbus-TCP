# iModbus TCP

iModbus TCP is a Modbus TCP client for iPhone. Use it to read and write PLCs, drives, meters and other Modbus TCP devices on your local network.

This repository hosts the app's public web pages:

- [Privacy Policy](https://matrixtesting.github.io/iModbus-TCP/): iModbus TCP collects no data.

- [Modbus TCP test server](modbus_test_server.py): simulates Modbus TCP devices on a Mac, for trying the app without real equipment.

The app's source code is not published here.

## Features

- Poll several devices at once, each with its own windows, unit IDs, address ranges and scan rates
- Read coils, discrete inputs, holding registers and input registers (functions 01–04)
- Write coils and registers (functions 05, 06 and 16), always with a confirmation step
- Show values as signed, unsigned, hex, binary, or 32/64-bit integers, floats and doubles in any byte order
- Name registers and set a format for each row

## Test server

`modbus_test_server.py` simulates Modbus TCP devices. It needs only Python 3, which comes with macOS.

```bash
python3 modbus_test_server.py 5020
```

Connect iModbus TCP to your Mac's IP address on port 5020. Holding register 0 counts seconds, register 1 is a sine wave, registers 2–3 are a 32-bit float temperature, and register 10 (starting at 1234) is free for writing. The comment at the top of the script lists everything it simulates. Press Ctrl+C to stop it.

## Support

Questions or problems: [matrixtesting2@gmail.com](mailto:matrixtesting2@gmail.com)
