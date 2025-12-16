"""
Example showing how to use the DLL parser with MaxUsbTool

This demonstrates integrating the C DLL parser with the existing
MaxUsbTool I2C EEPROM reading functionality.
"""

import sys
import os

# Add parent directory to path to import MaxUsbTool
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from MaxUsbTool import MaxUsbTool
import rpi_hat_parser_wrapper as parser

try:
    # Initialize the FTDI I2C tool
    print("Initializing MaxUsbTool...")
    maxUsbTool = MaxUsbTool()
except RuntimeError as e:
    print(f'\n{e}')
    print('\nFailed to initialize. Exiting...')
    exit(1)

print(f'\nDetected EEPROM at address: 0x{maxUsbTool.slave_address:02x}')

# Read EEPROM data
print("\nReading EEPROM data...")
start_addr = 0x00
size = 256  # Read 256 bytes

ret, eeprom_data = maxUsbTool.read_eeprom_to_file(start_addr, size, should_save=False)

if ret != 0:
    print("Error reading EEPROM!")
    exit(1)

print(f"Successfully read {len(eeprom_data)} bytes\n")

# Parse using the DLL
print("="*80)
print("Parsing with C DLL Parser")
print("="*80 + "\n")

status = parser.parse_and_print_eeprom(eeprom_data)

if status != parser.PARSE_OK:
    print(f"\nParse error: {parser.get_parse_error_message(status)}")
else:
    print("\n" + "="*80)
    print("Parse completed successfully!")
    print("="*80)

# Alternative: Get structured data
print("\n\n" + "="*80)
print("Alternative: Getting Structured Data from DLL")
print("="*80 + "\n")

status, result = parser.parse_rpi_hat_eeprom(eeprom_data)

if status == parser.PARSE_OK and result:
    print(f"Signature: {result.header.signature.decode('ascii')}")
    print(f"Version: 0x{result.header.version:02x}")
    print(f"Number of Atoms: {result.header.numatoms}")
    print(f"EEPROM Length: {result.header.eeplen} bytes")
    
    if result.has_vendor_info:
        print(f"\nVendor: {result.vendor_info.vendor.decode('utf-8')}")
        print(f"Product: {result.vendor_info.product.decode('utf-8')}")
        print(f"Product ID: {result.vendor_info.product_id}")
        print(f"Product Version: {result.vendor_info.product_version}")
        
        # Access UUID
        uuid_hex = ''.join(f'{b:02x}' for b in result.vendor_info.uuid)
        print(f"UUID: {uuid_hex}")
else:
    print(f"Parse error: {parser.get_parse_error_message(status)}")
