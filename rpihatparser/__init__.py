"""
RPi HAT EEPROM Parser Package

This package provides a C/C++ DLL-based parser for Raspberry Pi HAT EEPROM data.
The parser can be used standalone or integrated with MaxUsbTool for I2C EEPROM reading.
"""

from .rpi_hat_parser_wrapper import (
    parse_rpi_hat_eeprom,
    parse_and_print_eeprom,
    get_parse_error_message,
    print_parsed_eeprom,
    ParsedEeprom,
    VendorInfo,
    CustomData,
    RpiHatHeader,
    PARSE_OK,
    PARSE_ERROR_INVALID_SIG,
    PARSE_ERROR_INVALID_DATA,
    PARSE_ERROR_BUFFER_TOO_SMALL,
    PARSE_ERROR_UNSUPPORTED_VERSION,
)

__version__ = '1.0.0'
__all__ = [
    'parse_rpi_hat_eeprom',
    'parse_and_print_eeprom',
    'get_parse_error_message',
    'print_parsed_eeprom',
    'ParsedEeprom',
    'VendorInfo',
    'CustomData',
    'RpiHatHeader',
    'PARSE_OK',
    'PARSE_ERROR_INVALID_SIG',
    'PARSE_ERROR_INVALID_DATA',
    'PARSE_ERROR_BUFFER_TOO_SMALL',
    'PARSE_ERROR_UNSUPPORTED_VERSION',
]
