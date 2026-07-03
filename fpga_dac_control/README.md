# FPGA/DAC Control through UART

A Python package for controlling FPGA waveform generation and DAC (Digital-to-Analog Converter) hardware through UART serial communication.

## Features

- **UART Communication**: Robust serial communication with packet framing and checksum validation
- **FPGA Control**: Configure waveform parameters (frequency, amplitude, phase, type)
- **DAC Control**: Set gain, offset, and output values for multiple channels
- **Graphical Interface**: Full-featured GUI for visual signal control and monitoring
- **Period Modulation**: Visualize and control frequency/period modulation effects
- **Interactive Console**: Command-line interface for manual control
- **Demo Mode**: Built-in demonstration sequence

## Installation

```bash
pip install -r requirements.txt
```

## Usage

### Basic Usage

```python
from fpga_dac_control import UARTCommunication, FPGAController, DACController

# Initialize UART connection
uart = UARTCommunication(port='/dev/ttyUSB0', baudrate=115200)
uart.connect()

# Create controllers
fpga = FPGAController(uart)
dac = DACController(uart)

# Configure waveform
fpga.set_frequency(1000)  # 1 kHz
fpga.set_amplitude(2.5)   # 2.5V
fpga.set_waveform_type(fpga.WAVE_SINE)

# Configure DAC
dac.set_gain(1.0)
dac.set_offset(0.0)

# Cleanup
uart.disconnect()
```

### Command Line Interface

```bash
# Run interactive console
python main.py -p /dev/ttyUSB0 -b 115200

# Run demo sequence
python main.py --demo

# Launch Graphical User Interface
python gui_controller.py

# Enable verbose logging
python main.py -v
```

### Interactive Commands

Once in interactive mode, use these commands:

| Command | Description |
|---------|-------------|
| `status` | Get FPGA status register |
| `freq <Hz>` | Set waveform frequency |
| `amp <V>` | Set amplitude in Volts |
| `gain <x>` | Set DAC gain multiplier |
| `offset <V>` | Set DAC offset voltage |
| `quit` | Exit the program |

## Project Structure

```
fpga_dac_control/
├── __init__.py          # Package initialization
├── main.py              # Main entry point and CLI
├── gui_controller.py    # Graphical user interface
├── uart_comm.py         # UART communication layer
├── fpga_controller.py   # FPGA waveform control
├── dac_controller.py    # DAC output control
└── requirements.txt     # Python dependencies
```

## GUI Features

The graphical interface (`gui_controller.py`) provides:

- **COM Port Selection**: Dropdown to select and refresh available serial ports
- **Baud Rate Configuration**: Select from standard baud rates (9600 - 921600)
- **Waveform Type Selector**: Choose between Sine, Square, Triangle, and Sawtooth
- **Parameter Sliders**: Real-time adjustment of:
  - Frequency (0.1 - 1000 Hz)
  - Amplitude (0 - 5 V)
  - Phase (0 - 360 degrees)
  - DC Offset (-5 to +5 V)
- **Period Modulation Controls**:
  - Modulation Depth (0 - 100%)
  - Modulation Frequency (0 - 50 Hz)
- **Real-time Visualization**: Matplotlib plot showing the generated waveform
- **Status Log**: Timestamped log of connection status and sent commands
- **One-click Send**: Transmit all parameters to FPGA with a single button

### Running the GUI

```bash
# Launch the graphical interface
python gui_controller.py
```

**Note**: The GUI requires `tkinter`, `numpy`, and `matplotlib`. On Linux, you may need to install tkinter separately:
```bash
# Ubuntu/Debian
sudo apt-get install python3-tk

# Fedora
sudo dnf install python3-tkinter
```

## Protocol

The communication protocol uses a simple packet format:

```
[HEADER][CMD][LENGTH][PAYLOAD...][CHECKSUM][FOOTER]
   0xAA   1B     1B      N B        1 B       0x55
```

- **Header**: 0xAA (packet start)
- **Command**: 1-byte command code
- **Length**: Payload length + 1 (for checksum)
- **Payload**: Command-specific data
- **Checksum**: Sum of CMD + LENGTH + PAYLOAD (lower 8 bits)
- **Footer**: 0x55 (packet end)

### Command Codes

| Code | Command | Description |
|------|---------|-------------|
| 0x01 | READ_STATUS | Read FPGA status register |
| 0x02 | SET_FREQUENCY | Set waveform frequency |
| 0x03 | SET_AMPLITUDE | Set waveform amplitude |
| 0x04 | DAC_GAIN | Set DAC gain |
| 0x05 | DAC_OFFSET | Set DAC offset |
| 0x10 | WRITE_REGISTER | Write to device register |
| 0x11 | READ_REGISTER | Read from device register |

## Configuration

### Serial Port Settings

- **Port**: `/dev/ttyUSB0` (Linux), `COM1` (Windows), etc.
- **Baud Rate**: 115200 (default), configurable
- **Data Bits**: 8
- **Parity**: None
- **Stop Bits**: 1

### Finding Available Ports

```python
from fpga_dac_control import UARTCommunication

uart = UARTCommunication()
ports = uart.list_available_ports()
print("Available ports:", ports)
```

## Customization

### Adding New Commands

1. Define command code in `uart_comm.py`:
```python
CMD_NEW_COMMAND = 0x20
```

2. Add controller method in appropriate module:
```python
def new_command(self, param: int) -> bool:
    payload = bytes([param & 0xFF])
    response = self.uart.send_command(UARTCommunication.CMD_NEW_COMMAND, payload)
    return response is not None
```

### Modifying Register Map

Update register addresses in `fpga_controller.py` or `dac_controller.py`:
```python
REG_CUSTOM = 0x20  # Add new register
```

## Troubleshooting

### Connection Issues

1. Verify the correct port name
2. Check permissions (may need `sudo` on Linux)
3. Ensure no other process is using the port
4. Verify baud rate matches FPGA configuration

### Communication Errors

1. Enable verbose logging: `python main.py -v`
2. Check wiring (TX/RX cross-connected, GND connected)
3. Verify protocol implementation matches FPGA firmware

## License

MIT License

## Contributing

Feel free to submit issues and enhancement requests!
