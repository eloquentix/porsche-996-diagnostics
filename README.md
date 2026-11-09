# pdiag: Porsche 996 and Boxster diagnostics for Mac

Open diagnostics for K-line era water-cooled Porsches: 986 Boxster, 996, 997.1, 987.1
and Cayenne 955 (roughly 1997–2008). A $20 cable, a Mac, and this.

**Try the demo first** (simulated car, no hardware): https://apps.eloquentix.com/porsche/996/

## Why this exists

To see what these cars' engine computers know on a Mac.

The tools that read a 996's Porsche data, Durametric and the dealer's PIWIS, run on
Windows only. A Mac owner needs a Windows laptop or a virtual machine just to read a fault
code or watch live engine data. Generic OBD apps work anywhere, but they only see emissions
data, not the engine computer's own Porsche data.

pdiag runs natively on macOS with a $20 cable. It's open source, read-only by design, and
logs every byte, so anything it finds can be checked.

## What works today, and what doesn't yet

Tested on a 2002 911 (996) Targa, US spec, Bosch ME7.8 engine computer.

| | Status |
|---|---|
| Live engine data: rpm, temperatures, air flow, timing, fuel trims, O2 sensors, speed, readiness | Works (21 readings, about 7 a second) |
| Fault codes: generic OBD and the engine computer's own | Works |
| Clearing fault codes (asks first, saves every code before clearing) | Works |
| Engine computer identification (VIN, part and software numbers) | Works |
| The engine computer's 14 Porsche-specific data blocks, raw | Works (shown and logged; not all decoded) |
| Over-rev counters (ignitions in each of the six over-rev ranges) | Not decoded yet; see "How you can help". The demo shows simulated counts. |
| Other models (986, 987.1, 997.1, 955) | Profiles exist, untested on a car |

## When it's useful now

- **Your own car, on a Mac:** live data on a 996-style cluster, check-engine codes with
  their status, clearing them after a repair, and a log of every reading.
- **Before buying:** fault codes, readiness monitors (all "not ready" right after a
  clear is a red flag), and the engine computer's identity. The over-rev check comes
  once the counters are decoded.
- **Research:** every byte on the wire is logged, and `pdiag sniff` captures what other
  tools do.

## What you need

- A **K-line era water-cooled Porsche** (above). Only the 2002 996 has been tested.
- An **FTDI-based KKL USB cable** ("VAG-COM 409.1", FT232RL chip), about $20. Not an
  ELM327 Bluetooth dongle: those hide the raw K-line. Avoid CH340 cables: their timing is
  too loose for the wake-up the car needs. Details: [docs/HARDWARE.md](docs/HARDWARE.md).
- A **Mac** (macOS has the FTDI driver built in). Linux likely works with small changes;
  Windows isn't supported yet.
- **Python 3.11+** and **uv**.

## Setup

```sh
brew install uv                          # or: curl -LsSf https://astral.sh/uv/install.sh | sh
git clone https://github.com/eloquentix/porsche-996-diagnostics.git
cd porsche-996-diagnostics
uv sync
uv run pdiag --mock ui                   # try it with the simulated car first
uv run pytest                            # optional: the test suite
```

## First run on the car

1. Plug the cable into the car first (996: driver's footwell, left of the steering
   column), then into the Mac. The other way round can leave the cable refusing
   settings until it's replugged.
2. Ignition **fully on**: dash lights and the check-engine lamp lit. In the accessory
   position the car doesn't answer. Engine running for live data.
3. `uv run pdiag ports` should list a `/dev/cu.usbserial-…` device.
4. `uv run pdiag ui` opens the web UI at http://127.0.0.1:8996. Or, on the command line:
   `uv run pdiag obd` (generic OBD summary), `uv run pdiag id` (identification),
   `uv run pdiag dtc` (the engine computer's fault codes).

Every run writes a byte-level trace to `logs/`. Those files contain your VIN; they stay
on your machine (gitignored).

## Commands

| Command | What |
|---|---|
| `pdiag ports` | List serial ports, flag the KKL cable |
| `pdiag ui` | Web UI: live cluster, over-rev report, fault codes (with clear), Porsche data, car info |
| `pdiag obd` | Generic OBD: protocol, supported readings, values, stored codes |
| `pdiag live [--pids 0C,05,0E]` | Stream readings as CSV |
| `pdiag id` | Engine computer identification (KWP 0x1A) |
| `pdiag dtc` | Engine computer fault codes (KWP 0x18) |
| `pdiag lid-scan [--session 0x81]` | Read every Porsche data block (KWP 0x21) to `logs/` |
| `pdiag probe [--addrs 33,10,11] [--init both]` | Wake addresses, print keybytes |
| `pdiag sniff` | Listen only: capture another tool's session |

Options: `--port /dev/cu.usbserial-…` (or `PDIAG_PORT`), `--model 986|996|987|997`
(default: from the VIN), `--mock` for the simulated car, `--no-trace`.

## Safety

pdiag only reads, with one exception you have to ask for. It never sends anything that
writes, codes, adapts or flashes the engine computer, and never asks for security access.
**Clearing fault codes** uses the same standard command any OBD reader sends (mode 04),
only after a confirmation dialog, and only after every code, the readiness status and
the engine computer's own code list are saved to `logs/`. Clearing resets the readiness
monitors, so the car may need some driving before an emissions test.

You use it on your own car at your own risk.

## How you can help

pdiag decodes only from its own captures, never from leaked dealer software or
proprietary tool internals. That makes data from real cars the most valuable
contribution.

1. **You have a Durametric:** this is the fastest way to the over-rev counters. Put
   pdiag's cable on the same OBD port with a Y-splitter, run `pdiag sniff`, and read the
   over-rev report in Durametric while it records. Note what Durametric shows. One such
   capture likely decodes the counters for every car with the same engine computer.
2. **You have a 986, 987.1, 997.1 or Cayenne:** run `pdiag obd`, `pdiag id` and
   `pdiag lid-scan` and send the files from `logs/`. Tell us the model and year.
3. **You write code:** Linux and Windows support, decoding the live bytes in data
   blocks 04/05, a phone app with a Bluetooth K-line dongle.

Open an issue with the files attached, or reach us through [Eloquentix](https://eloquentix.com).
Please send traces privately or remove the VIN first (it's in the identification replies).

## Buying or selling one of these cars?

We're building **verified pre-purchase reports**: plug in for five minutes and get a
tamper-evident link with the over-rev ranges, fault codes and identification, one that a
buyer can trust more than a screenshot. Email
[info@eloquentix.com](mailto:info@eloquentix.com?subject=Porsche%20pre-purchase%20report)
to hear when it's ready, or if you run a shop and want it for inspections.

## FAQ

**Is there a Durametric alternative for Mac?**
pdiag runs on macOS with a $20 FTDI KKL cable. Today it reads live data, fault codes,
identification and the engine computer's Porsche data. The over-rev report, Durametric's
best-known feature, isn't decoded yet.

**Can I check a 996 or Boxster for over-revs before buying?**
Not with pdiag yet; today that takes Durametric or a dealer. pdiag already helps with the
rest: fault codes, and readiness monitors that show whether codes were cleared recently.

**Which cable do I need? Will a Bluetooth ELM327 work?**
An FTDI-based KKL USB cable ("VAG-COM 409.1"). ELM327 dongles hide the raw K-line these
cars use, and CH340-based cables can't time the wake-up reliably.

**Which cars does it support?**
Water-cooled K-line Porsches, about 1997–2008: 986 Boxster, 996, 997.1, 987.1 and Cayenne 955.
Tested on a 2002 996 with a Bosch ME7.8 engine computer; the others need testers.

**Can it damage the car?**
It only reads, except clearing fault codes, which asks first and saves every code. It never
codes, adapts, flashes or asks for security access.

**Does it work on Windows or Linux?**
Not yet: macOS only. Linux should need small changes; help is welcome.

## What's in this repository

- The root is **pdiag**: the protocol stack, decoders, command line and web UI (`src/pdiag/`).
- [`codex/`](codex/) is an **alternate front end**: a photo-real 996 instrument panel built
  by a second AI agent (OpenAI Codex) on top of pdiag's API, with its own guarded
  code-clearing endpoint (also mode 04, confirmation and audit log). Demo:
  https://apps.eloquentix.com/porsche/996Codex/

## Docs

- [docs/PROTOCOL.md](docs/PROTOCOL.md): K-line and KWP2000 notes, every finding with its source
- [docs/HARDWARE.md](docs/HARDWARE.md): cable, wiring, timing, sniffing setup
- [CLAUDE.md](CLAUDE.md): project context, decisions, status, next steps

## Disclaimer

Not affiliated with, endorsed by, or connected to Dr. Ing. h.c. F. Porsche AG, Robert Bosch
GmbH, or Durametric. Brand names are used only to describe compatibility.

## Credits and license

A project by [Eloquentix](https://eloquentix.com). [GPL-3.0-or-later](LICENSE).
