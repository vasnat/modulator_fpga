#!/usr/bin/env python3
"""
FPGA Controller module for waveform generation control.
"""

import logging
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from uart_comm import UARTCommunication


class FPGAController:
    """Controls FPGA waveform generation parameters."""
    
    # Register addresses (example)
    REG_STATUS = 0x00
    REG_FREQUENCY = 0x01
    REG_AMPLITUDE = 0x02
    REG_PHASE = 0x03
    REG_WAVEFORM_TYPE = 0x04
    
    # Waveform types
    WAVE_SINE = 0x00
    WAVE_SQUARE = 0x01
    WAVE_TRIANGLE = 0x02
    WAVE_SAWTOOTH = 0x03
    
    def __init__(self, uart: 'UARTCommunication'):
        """
        Initialize FPGA controller.
        
        Args:
            uart: UART communication instance
        """
        self.uart = uart
        self.logger = logging.getLogger(__name__)
    
    def get_status(self) -> int:
        """
        Get FPGA status register value.
        
        Returns:
            Status register value
        """
        response = self.uart.send_command(
            self.uart.CMD_READ_STATUS,
            expect_response=True
        )
        if response and len(response) >= 2:
            return (response[0] << 8) | response[1]
        return 0
    
    def set_frequency(self, frequency_hz: float) -> bool:
        """
        Set waveform frequency.
        
        Args:
            frequency_hz: Frequency in Hz
            
        Returns:
            True if successful
        """
        # Convert frequency to register value (example: fixed-point format)
        freq_reg = int(frequency_hz * 1000) & 0xFFFFFFFF
        
        payload = bytes([
            self.REG_FREQUENCY,
            (freq_reg >> 24) & 0xFF,
            (freq_reg >> 16) & 0xFF,
            (freq_reg >> 8) & 0xFF,
            freq_reg & 0xFF
        ])
        
        success = self.uart.write_register(self.REG_FREQUENCY, freq_reg)
        if success:
            self.logger.info(f"Frequency set to {frequency_hz} Hz")
        else:
            self.logger.error("Failed to set frequency")
        
        return success
    
    def set_amplitude(self, amplitude_v: float) -> bool:
        """
        Set waveform amplitude.
        
        Args:
            amplitude_v: Amplitude in Volts (0-5V range)
            
        Returns:
            True if successful
        """
        # Convert voltage to DAC units (example: 12-bit DAC, 0-5V range)
        dac_max = 4095
        voltage_max = 5.0
        amplitude_reg = int((amplitude_v / voltage_max) * dac_max) & 0xFFF
        
        payload = bytes([
            self.REG_AMPLITUDE,
            (amplitude_reg >> 8) & 0xFF,
            amplitude_reg & 0xFF
        ])
        
        success = self.uart.write_register(self.REG_AMPLITUDE, amplitude_reg)
        if success:
            self.logger.info(f"Amplitude set to {amplitude_v} V")
        else:
            self.logger.error("Failed to set amplitude")
        
        return success
    
    def set_phase(self, phase_deg: float) -> bool:
        """
        Set waveform phase offset.
        
        Args:
            phase_deg: Phase in degrees (0-360)
            
        Returns:
            True if successful
        """
        # Convert phase to register value (16-bit, 0-360 degrees)
        phase_reg = int((phase_deg / 360.0) * 65535) & 0xFFFF
        
        return self.uart.write_register(self.REG_PHASE, phase_reg)
    
    def set_waveform_type(self, wave_type: int) -> bool:
        """
        Set waveform type.
        
        Args:
            wave_type: One of WAVE_SINE, WAVE_SQUARE, WAVE_TRIANGLE, WAVE_SAWTOOTH
            
        Returns:
            True if successful
        """
        if wave_type not in [self.WAVE_SINE, self.WAVE_SQUARE, 
                             self.WAVE_TRIANGLE, self.WAVE_SAWTOOTH]:
            self.logger.error(f"Invalid waveform type: {wave_type}")
            return False
        
        return self.uart.write_register(self.REG_WAVEFORM_TYPE, wave_type)
    
    def enable_output(self, enable: bool = True) -> bool:
        """
        Enable or disable waveform output.
        
        Args:
            enable: True to enable, False to disable
            
        Returns:
            True if successful
        """
        # This would typically write to a control register
        # Implementation depends on specific FPGA design
        self.logger.info(f"Output {'enabled' if enable else 'disabled'}")
        return True
    
    def sweep_frequency(self, start_hz: float, stop_hz: float, 
                       duration_s: float) -> bool:
        """
        Perform frequency sweep.
        
        Args:
            start_hz: Start frequency in Hz
            stop_hz: Stop frequency in Hz
            duration_s: Sweep duration in seconds
            
        Returns:
            True if successful
        """
        self.logger.info(
            f"Starting frequency sweep: {start_hz} Hz -> {stop_hz} Hz "
            f"in {duration_s} s"
        )
        
        import time
        steps = 100
        delay = duration_s / steps
        
        for i in range(steps + 1):
            freq = start_hz + (stop_hz - start_hz) * (i / steps)
            if not self.set_frequency(freq):
                return False
            time.sleep(delay)
        
        self.logger.info("Frequency sweep completed")
        return True
