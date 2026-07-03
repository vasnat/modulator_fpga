#!/usr/bin/env python3
"""
DAC Controller module for Digital-to-Analog Converter control.
"""

import logging
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from uart_comm import UARTCommunication


class DACController:
    """Controls DAC parameters for analog output."""
    
    # Register addresses (example)
    REG_DAC_CONTROL = 0x10
    REG_DAC_GAIN = 0x11
    REG_DAC_OFFSET = 0x12
    REG_DAC_VALUE = 0x13
    
    # DAC channels
    CHANNEL_A = 0x00
    CHANNEL_B = 0x01
    
    def __init__(self, uart: 'UARTCommunication'):
        """
        Initialize DAC controller.
        
        Args:
            uart: UART communication instance
        """
        self.uart = uart
        self.logger = logging.getLogger(__name__)
        self._gain = 1.0
        self._offset = 0.0
    
    def set_gain(self, gain: float) -> bool:
        """
        Set DAC gain factor.
        
        Args:
            gain: Gain multiplier (typically 0.5 to 2.0)
            
        Returns:
            True if successful
        """
        # Convert gain to register value (example: Q8.8 fixed-point)
        gain_reg = int(gain * 256) & 0xFFFF
        
        success = self.uart.write_register(self.REG_DAC_GAIN, gain_reg)
        if success:
            self._gain = gain
            self.logger.info(f"DAC gain set to {gain}")
        else:
            self.logger.error("Failed to set DAC gain")
        
        return success
    
    def get_gain(self) -> float:
        """Get current gain setting."""
        return self._gain
    
    def set_offset(self, offset_v: float) -> bool:
        """
        Set DAC output offset voltage.
        
        Args:
            offset_v: Offset voltage in Volts (-2.5V to +2.5V range)
            
        Returns:
            True if successful
        """
        # Convert offset to register value (signed, Q12.4 format example)
        offset_max = 2.5
        offset_reg = int((offset_v / offset_max) * 2047) & 0xFFF
        
        success = self.uart.write_register(self.REG_DAC_OFFSET, offset_reg)
        if success:
            self._offset = offset_v
            self.logger.info(f"DAC offset set to {offset_v} V")
        else:
            self.logger.error("Failed to set DAC offset")
        
        return success
    
    def get_offset(self) -> float:
        """Get current offset setting."""
        return self._offset
    
    def set_value(self, channel: int, value: int) -> bool:
        """
        Set raw DAC output value.
        
        Args:
            channel: DAC channel (CHANNEL_A or CHANNEL_B)
            value: Raw DAC value (0-4095 for 12-bit DAC)
            
        Returns:
            True if successful
        """
        if not 0 <= value <= 4095:
            self.logger.error(f"Invalid DAC value: {value}")
            return False
        
        # Combine channel and value
        reg_value = (channel << 12) | value
        
        return self.uart.write_register(self.REG_DAC_VALUE, reg_value)
    
    def set_voltage(self, channel: int, voltage: float) -> bool:
        """
        Set DAC output voltage.
        
        Args:
            channel: DAC channel
            voltage: Output voltage in Volts (0-5V)
            
        Returns:
            True if successful
        """
        # Apply gain and offset
        adjusted_voltage = voltage * self._gain + self._offset
        
        # Clamp to valid range
        adjusted_voltage = max(0.0, min(5.0, adjusted_voltage))
        
        # Convert to DAC units (12-bit, 0-5V range)
        dac_max = 4095
        voltage_max = 5.0
        dac_value = int((adjusted_voltage / voltage_max) * dac_max)
        
        self.logger.debug(
            f"Channel {channel}: {voltage}V -> {adjusted_voltage}V "
            f"(DAC: {dac_value})"
        )
        
        return self.set_value(channel, dac_value)
    
    def enable_channel(self, channel: int, enable: bool = True) -> bool:
        """
        Enable or disable DAC channel.
        
        Args:
            channel: DAC channel
            enable: True to enable, False to disable
            
        Returns:
            True if successful
        """
        # Read current control register
        control_reg = self.uart.read_register(self.REG_DAC_CONTROL)
        if control_reg is None:
            control_reg = 0
        
        # Set or clear channel enable bit
        if enable:
            control_reg |= (1 << channel)
        else:
            control_reg &= ~(1 << channel)
        
        success = self.uart.write_register(self.REG_DAC_CONTROL, control_reg)
        if success:
            self.logger.info(
                f"Channel {channel} {'enabled' if enable else 'disabled'}"
            )
        return success
    
    def read_back_value(self, channel: int) -> Optional[int]:
        """
        Read back the current DAC value (if supported).
        
        Args:
            channel: DAC channel
            
        Returns:
            Current DAC value or None
        """
        # This would read from a shadow register or ADC feedback
        # Implementation depends on specific hardware
        self.logger.warning("Read-back not implemented for this hardware")
        return None
    
    def calibrate(self, channel: int, target_voltage: float, 
                  measured_voltage: float) -> bool:
        """
        Perform simple calibration adjustment.
        
        Args:
            channel: DAC channel
            target_voltage: Expected output voltage
            measured_voltage: Actually measured voltage
            
        Returns:
            True if calibration successful
        """
        if target_voltage == 0:
            self.logger.error("Target voltage cannot be zero")
            return False
        
        error = measured_voltage - target_voltage
        correction = -error / target_voltage
        
        new_gain = self._gain * (1 + correction)
        new_gain = max(0.5, min(2.0, new_gain))  # Clamp to valid range
        
        self.logger.info(
            f"Calibration: error={error:.3f}V, "
            f"gain adjustment: {self._gain:.3f} -> {new_gain:.3f}"
        )
        
        return self.set_gain(new_gain)
