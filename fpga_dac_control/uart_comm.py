#!/usr/bin/env python3
"""
UART Communication module for FPGA/DAC control.
Handles serial communication with the FPGA board.
"""

import logging
from typing import Optional, List
import serial
import serial.tools.list_ports


class UARTCommunication:
    """Manages UART communication with FPGA device."""
    
    # Protocol constants
    HEADER = 0xAA
    FOOTER = 0x55
    
    # Command codes
    CMD_READ_STATUS = 0x01
    CMD_SET_FREQUENCY = 0x02
    CMD_SET_AMPLITUDE = 0x03
    CMD_DAC_GAIN = 0x04
    CMD_DAC_OFFSET = 0x05
    CMD_WRITE_REGISTER = 0x10
    CMD_READ_REGISTER = 0x11
    
    def __init__(self, port: str = '/dev/ttyUSB0', baudrate: int = 115200, 
                 timeout: float = 1.0):
        """
        Initialize UART communication.
        
        Args:
            port: Serial port device path
            baudrate: Baud rate for serial communication
            timeout: Read timeout in seconds
        """
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.serial_port: Optional[serial.Serial] = None
        self.logger = logging.getLogger(__name__)
    
    def list_available_ports(self) -> List[str]:
        """List all available serial ports."""
        ports = serial.tools.list_ports.comports()
        return [port.device for port in ports]
    
    def connect(self) -> bool:
        """
        Establish connection to the serial port.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            self.serial_port = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=self.timeout,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE
            )
            self.logger.info(f"Connected to {self.port}")
            return True
        except serial.SerialException as e:
            self.logger.error(f"Failed to connect: {e}")
            return False
    
    def disconnect(self) -> None:
        """Close the serial connection."""
        if self.serial_port and self.serial_port.is_open:
            self.serial_port.close()
            self.logger.info("Disconnected")
    
    def is_connected(self) -> bool:
        """Check if serial port is open."""
        return (self.serial_port is not None and 
                self.serial_port.is_open)
    
    def _calculate_checksum(self, data: bytes) -> int:
        """Calculate checksum for packet."""
        return sum(data) & 0xFF
    
    def _build_packet(self, command: int, payload: bytes = b'') -> bytes:
        """
        Build a protocol packet.
        
        Packet format: [HEADER][CMD][LENGTH][PAYLOAD...][CHECKSUM][FOOTER]
        
        Args:
            command: Command code
            payload: Command payload data
            
        Returns:
            Complete packet bytes
        """
        length = len(payload) + 1  # +1 for checksum
        checksum = self._calculate_checksum(bytes([command, length]) + payload)
        
        packet = bytes([
            self.HEADER,
            command,
            length,
            *payload,
            checksum,
            self.FOOTER
        ])
        
        self.logger.debug(f"TX: {packet.hex()}")
        return packet
    
    def _read_response(self, expected_length: int = 0) -> Optional[bytes]:
        """
        Read response from device.
        
        Args:
            expected_length: Expected payload length (0 for variable)
            
        Returns:
            Response payload or None if error
        """
        if not self.serial_port:
            return None
        
        try:
            # Read header
            header = self.serial_port.read(1)
            if not header or header[0] != self.HEADER:
                self.logger.warning("Invalid header received")
                return None
            
            # Read command and length
            cmd_len = self.serial_port.read(2)
            if len(cmd_len) < 2:
                self.logger.warning("Incomplete packet")
                return None
            
            command = cmd_len[0]
            length = cmd_len[1]
            
            # Read payload and checksum
            data = self.serial_port.read(length)
            if len(data) < length:
                self.logger.warning("Incomplete packet data")
                return None
            
            payload = data[:-1]
            checksum = data[-1]
            
            # Read footer
            footer = self.serial_port.read(1)
            if not footer or footer[0] != self.FOOTER:
                self.logger.warning("Invalid footer received")
                return None
            
            # Verify checksum
            calculated_checksum = self._calculate_checksum(
                bytes([command, length]) + payload
            )
            if checksum != calculated_checksum:
                self.logger.warning(
                    f"Checksum mismatch: expected {calculated_checksum}, "
                    f"got {checksum}"
                )
                return None
            
            self.logger.debug(f"RX: CMD={command:#x}, PAYLOAD={payload.hex()}")
            return payload
            
        except serial.SerialTimeoutException:
            self.logger.warning("Read timeout")
            return None
    
    def send_command(self, command: int, payload: bytes = b'', 
                     expect_response: bool = True) -> Optional[bytes]:
        """
        Send a command and optionally wait for response.
        
        Args:
            command: Command code
            payload: Command payload
            expect_response: Whether to wait for response
            
        Returns:
            Response payload or None
        """
        if not self.is_connected():
            self.logger.error("Not connected")
            return None
        
        packet = self._build_packet(command, payload)
        
        try:
            self.serial_port.write(packet)  # type: ignore
            self.serial_port.flush()  # type: ignore
            
            if expect_response:
                return self._read_response()
            return None
            
        except serial.SerialException as e:
            self.logger.error(f"Write error: {e}")
            return None
    
    def write_register(self, address: int, value: int) -> bool:
        """
        Write to a device register.
        
        Args:
            address: Register address
            value: Value to write
            
        Returns:
            True if successful
        """
        payload = bytes([address, (value >> 8) & 0xFF, value & 0xFF])
        response = self.send_command(self.CMD_WRITE_REGISTER, payload)
        return response is not None and response[0] == 0x00
    
    def read_register(self, address: int) -> Optional[int]:
        """
        Read from a device register.
        
        Args:
            address: Register address
            
        Returns:
            Register value or None
        """
        payload = bytes([address])
        response = self.send_command(self.CMD_READ_REGISTER, payload)
        if response and len(response) >= 3:
            return (response[1] << 8) | response[2]
        return None
