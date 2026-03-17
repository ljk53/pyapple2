# pyapple2

A Python Apple II emulator with a reverse-engineering toolkit.

## Architecture

- **Emulator**: Pure Python Apple II simulation (6502 CPU with BCD support, memory, Disk II controller, display, keyboard, speaker)
- **Tools**: Generic reverse-engineering tools (instruction tracing, routine detection, call stack analysis, symbol tables, heatmap visualization)

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Usage

### Pygame (graphical)

```bash
cd src
python main_pygame.py
```

### With disk image

```bash
cd src
python main_pygame.py -d ../bin/APPLER.DSK
```

### Headless (terminal)

```bash
cd src
python main_headless.py
```

## ROM Files

The `bin/` directory contains ROM and disk files from the [Appler](https://github.com/zajo/appler) project (an Apple ][ emulator for MS-DOS), plus the Apple II+ system ROM (`A2SOFT2.BIN`).

## Tests

```bash
cd src
python -m pytest tests/
```

## Credits

- CPU implementation based on [py65](https://github.com/mnaberez/py65) by Mike Naberez (MPU6502 with BCD support)
- Appler ROM/disk files from [zajo/appler](https://github.com/zajo/appler) by Emil Dotchevski

## License

MIT
