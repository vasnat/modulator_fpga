#!/usr/bin/env python3
"""
Main entry point for FPGA/DAC control through UART.
"""

import argparse
import logging
from fpga_controller import FPGAController
from dac_controller import DACController
from uart_comm import UARTCommunication


def setup_logging(verbose: bool = False) -> None:
    """Configure logging based on verbosity level."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Control FPGA/DAC through UART'
    )
    parser.add_argument(
        '-p', '--port',
        type=str,
        default='/dev/ttyUSB0',
        help='UART port (default: /dev/ttyUSB0)'
    )
    parser.add_argument(
        '-b', '--baudrate',
        type=int,
        default=115200,
        help='Baud rate (default: 115200)'
    )
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    parser.add_argument(
        '--demo',
        action='store_true',
        help='Run demo sequence'
    )
    
    return parser.parse_args()


def main() -> int:
    """Main function to run the FPGA/DAC controller."""
    args = parse_arguments()
    setup_logging(args.verbose)
    
    logger = logging.getLogger(__name__)
    logger.info(f"Initializing UART on {args.port} at {args.baudrate} baud")
    
    try:
        # Initialize UART communication
        uart = UARTCommunication(
            port=args.port,
            baudrate=args.baudrate,
            timeout=1.0
        )
        
        # Initialize controllers
        fpga_ctrl = FPGAController(uart)
        dac_ctrl = DACController(uart)
        
        # Connect to device
        if not uart.connect():
            logger.error("Failed to connect to device")
            return 1
        
        logger.info("Connected successfully")
        
        # Run demo or interactive mode
        if args.demo:
            logger.info("Running demo sequence...")
            run_demo(fpga_ctrl, dac_ctrl)
        else:
            logger.info("Ready for commands. Use Ctrl+C to exit.")
            interactive_mode(fpga_ctrl, dac_ctrl)
        
        return 0
        
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        return 0
    except Exception as e:
        logger.exception(f"Error: {e}")
        return 1
    finally:
        if 'uart' in locals():
            uart.disconnect()


def run_demo(fpga_ctrl: FPGAController, dac_ctrl: DACController) -> None:
    """Run a demonstration sequence."""
    logger = logging.getLogger(__name__)
    
    # Check FPGA status
    logger.info("Checking FPGA status...")
    status = fpga_ctrl.get_status()
    logger.info(f"FPGA Status: {status:#x}")
    
    # Configure DAC
    logger.info("Configuring DAC...")
    dac_ctrl.set_gain(1.0)
    dac_ctrl.set_offset(0.0)
    
    # Set waveform parameters
    logger.info("Setting waveform parameters...")
    fpga_ctrl.set_frequency(1000)  # 1 kHz
    fpga_ctrl.set_amplitude(2.5)   # 2.5V
    
    logger.info("Demo completed successfully")


def interactive_mode(fpga_ctrl: FPGAController, dac_ctrl: DACController) -> None:
    """Run interactive command mode."""
    logger = logging.getLogger(__name__)
    
    print("\n=== FPGA/DAC Control Console ===")
    print("Commands:")
    print("  status     - Get FPGA status")
    print("  freq <Hz>  - Set frequency")
    print("  amp <V>    - Set amplitude")
    print("  gain <x>   - Set DAC gain")
    print("  offset <V> - Set DAC offset")
    print("  quit       - Exit")
    print()
    
    while True:
        try:
            cmd = input("> ").strip().split()
            if not cmd:
                continue
            
            command = cmd[0].lower()
            
            if command == "quit" or command == "exit":
                break
            elif command == "status":
                status = fpga_ctrl.get_status()
                print(f"FPGA Status: {status:#x}")
            elif command == "freq" and len(cmd) > 1:
                fpga_ctrl.set_frequency(float(cmd[1]))
                print(f"Frequency set to {cmd[1]} Hz")
            elif command == "amp" and len(cmd) > 1:
                fpga_ctrl.set_amplitude(float(cmd[1]))
                print(f"Amplitude set to {cmd[1]} V")
            elif command == "gain" and len(cmd) > 1:
                dac_ctrl.set_gain(float(cmd[1]))
                print(f"Gain set to {cmd[1]}")
            elif command == "offset" and len(cmd) > 1:
                dac_ctrl.set_offset(float(cmd[1]))
                print(f"Offset set to {cmd[1]} V")
            else:
                print("Unknown command or invalid arguments")
                
        except EOFError:
            break
        except Exception as e:
            print(f"Error: {e}")


if __name__ == "__main__":
    exit(main())
