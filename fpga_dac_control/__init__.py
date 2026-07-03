"""
FPGA/DAC Control Package

A Python package for controlling FPGA and DAC hardware through UART communication.
"""

from .uart_comm import UARTCommunication
from .fpga_controller import FPGAController
from .dac_controller import DACController

__version__ = '1.0.0'
__author__ = 'Your Name'

__all__ = [
    'UARTCommunication',
    'FPGAController', 
    'DACController',
]
