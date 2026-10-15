# Material Label Generator

A Python-based material label generator with QR code support and Windows printer integration.

## Features

- **DTPWeb Native Printing**: Prints via 德佟 (DothanTech) `dtpweb` interface — text and QR code are sent to the printer as native objects instead of a bitmap
- **Print Channel Switch**: Choose between `dtpweb` native printing (DothanTech label printers) and Chrome bitmap printing (any Windows printer)
- **Text Size Control**: `Text Size (%)` scales all text globally (50%–200%); oversized lines shrink automatically to fit
- **Label Layout**: Left side displays TYPE, PKG (Package), and RNG (Value Range); Right side displays QR code
- **Cable Label Mode**: Tab-based GUI — the *Cable Label* tab prints a large cable name with a wrapping note line below (QR encodes `NAME:...|NOTE:...`)
- **QR Code Content**: Encodes TYPE, PKG, and RANGE information
- **Customizable Size**: Print size from 1mm to 70mm x 70mm
- **Print Date Option**: Optional timestamp on label
- **Printer Support**: Windows printer selection via dropdown
- **Input History**: Custom inputs are saved to `history.ini` and persist across sessions
- **Preview**: Real-time label preview before printing
- **Save Image**: Export label as PNG image

## Preview

![Label Preview](test_label.png)

![GUI Preview](preview.png)

## Requirements

```
Pillow
qrcode
pywin32
```

## Usage

```bash
python main.py
```

## Project Structure

```
label_generator/
├── generator/
│   ├── __init__.py
│   └── label.py                # Label layout (mm based) & bitmap rendering
├── gui/
│   ├── __init__.py
│   └── gui.py                  # GUI interface
├── printer/
│   ├── __init__.py
│   ├── dtpweb_bridge.py        # dtpweb native print channel
│   ├── chrome_bitmap.py        # Chrome/Edge bitmap print channel (fallback)
│   └── web/
│       ├── print.html          # Browser page that calls dtpweb
│       └── lib/dtpweb.js       # Official dtpweb UMD package (2.7.260720)
├── docs/
│   └── dtpweb-api.md           # dtpweb interface cheat sheet
├── config.py                   # History management
├── main.py                     # Entry point
└── history.ini                 # Auto-generated (user input history)
```

## Printing

Two print channels are available, switchable from the **Print via** dropdown:

| Channel | How it works | When to use |
| --- | --- | --- |
| `dtpweb` | Renders the label in a local HTML page through the official `dtpweb` JS interface; text and QR code are sent to the printer natively | 德佟 / DothanTech label printers (`dtpweb` print helper installed) |
| `bitmap` | Renders the label to a PNG with Pillow and prints it via Chrome/Edge at the exact paper size | Any other Windows printer, or when the print helper is unavailable |

Requirements for the `dtpweb` channel:

1. Install the 德佟 printer driver (the `dtpweb` print helper is bundled with it on Windows).
2. Chrome or Edge must be present on the machine.

The bridge starts a temporary local HTTP server, opens `printer/web/print.html`
in the browser, and waits for the page to report the print result back.

See [docs/dtpweb-api.md](docs/dtpweb-api.md) for the full interface reference.

## Print Size

- Minimum: 1mm x 1mm
- Maximum: 70mm x 70mm
- Default: 50mm x 25mm# label_generator
