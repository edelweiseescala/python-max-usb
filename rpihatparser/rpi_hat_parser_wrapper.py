"""
Python wrapper for rpi_hat_parser DLL
"""

import ctypes
import os
from typing import Optional, Callable, Tuple

script_dir = os.path.dirname(os.path.abspath(__file__))
dll_path = os.path.join(script_dir, 'rpi_hat_parser.dll')

if not os.path.exists(dll_path):
	raise FileNotFoundError(f"DLL not found: {dll_path}\nPlease compile the C code first.")

parser_lib = ctypes.cdll.LoadLibrary(dll_path)

ATOM_TYPE_VENDOR_INFO = 1
ATOM_TYPE_GPIO_MAP = 2
ATOM_TYPE_DT_OVERLAY = 3
ATOM_TYPE_CUSTOM = 4

PARSE_OK = 0
PARSE_ERROR_INVALID_SIG = -1
PARSE_ERROR_INVALID_DATA = -2
PARSE_ERROR_BUFFER_TOO_SMALL = -3
PARSE_ERROR_UNSUPPORTED_VERSION = -4

MAX_STRING_LENGTH = 256
MAX_CUSTOM_DATA_SIZE = 4096

class RpiHatHeader(ctypes.Structure):
	_fields_ = [
		('signature', ctypes.c_char * 5),
		('version', ctypes.c_uint8),
		('reserved', ctypes.c_uint8),
		('numatoms', ctypes.c_uint16),
		('eeplen', ctypes.c_uint32)
	]

class VendorInfo(ctypes.Structure):
	_fields_ = [
		('uuid', ctypes.c_uint8 * 16),
		('product_id', ctypes.c_uint16),
		('product_version', ctypes.c_uint16),
		('vendor', ctypes.c_char * MAX_STRING_LENGTH),
		('product', ctypes.c_char * MAX_STRING_LENGTH)
	]

class CustomData(ctypes.Structure):
	_fields_ = [
		('data_length', ctypes.c_uint32),
		('data', ctypes.c_uint8 * MAX_CUSTOM_DATA_SIZE),
		('is_json', ctypes.c_int)
	]

class ParsedEeprom(ctypes.Structure):
	_fields_ = [
		('header', RpiHatHeader),
		('has_vendor_info', ctypes.c_int),
		('vendor_info', VendorInfo),
		('has_custom_data', ctypes.c_int),
		('custom_data', CustomData),
		('has_dt_overlay', ctypes.c_int),
		('dt_overlay_length', ctypes.c_uint32),
		('dt_overlay', ctypes.c_char * MAX_STRING_LENGTH)
	]

parser_lib.parse_rpi_hat_eeprom.argtypes = [
	ctypes.POINTER(ctypes.c_uint8),
	ctypes.c_uint32,
	ctypes.POINTER(ParsedEeprom)
]
parser_lib.parse_rpi_hat_eeprom.restype = ctypes.c_int

OutputCallback = ctypes.CFUNCTYPE(None, ctypes.c_char_p)
parser_lib.parse_and_print_eeprom.argtypes = [
	ctypes.POINTER(ctypes.c_uint8),
	ctypes.c_uint32,
	OutputCallback
]
parser_lib.parse_and_print_eeprom.restype = ctypes.c_int

parser_lib.get_parse_error_message.argtypes = [ctypes.c_int]
parser_lib.get_parse_error_message.restype = ctypes.c_char_p

def parse_rpi_hat_eeprom(eeprom_data: bytes) -> Tuple[int, Optional[ParsedEeprom]]:
	"""
	Parse RPi HAT EEPROM data using the C DLL.
	
	Args:
		eeprom_data: Raw EEPROM data as bytes
		
	Returns:
		Tuple: (status_code, ParsedEeprom object or None)
	"""
	if not isinstance(eeprom_data, (bytes, bytearray, list)):
		raise TypeError("eeprom_data must be bytes, bytearray, or list of integers")
	
	# Convert to ctypes array
	data_array = (ctypes.c_uint8 * len(eeprom_data))(*eeprom_data)
	result = ParsedEeprom()
	
	# Call the DLL function
	status = parser_lib.parse_rpi_hat_eeprom(data_array, len(eeprom_data), ctypes.byref(result))
	
	if status == PARSE_OK:
		return (status, result)
	else:
		return (status, None)


def parse_and_print_eeprom(eeprom_data: bytes, output_callback: Optional[Callable[[str], None]] = None) -> int:
	"""
	Parse and print RPi HAT EEPROM data with formatted output.
	
	Args:
		eeprom_data: Raw EEPROM data as bytes
		output_callback: Optional callback function for output lines (receives string)
		
	Returns:
		int: Status code (PARSE_OK on success)
	"""
	if not isinstance(eeprom_data, (bytes, bytearray, list)):
		raise TypeError("eeprom_data must be bytes, bytearray, or list of integers")
	
	# Convert to ctypes array
	data_array = (ctypes.c_uint8 * len(eeprom_data))(*eeprom_data)
	
	# Create callback wrapper if provided
	if output_callback:
		def c_callback(msg):
			output_callback(msg.decode('utf-8'))
		callback_func = OutputCallback(c_callback)
		status = parser_lib.parse_and_print_eeprom(data_array, len(eeprom_data), callback_func)
	else:
		# Pass NULL (None cast to the callback type)
		status = parser_lib.parse_and_print_eeprom(data_array, len(eeprom_data), ctypes.cast(None, OutputCallback))
	
	return status


def get_parse_error_message(error_code: int) -> str:
	"""
	Get human-readable error message for a parse error code.
	
	Args:
		error_code: Error code from parse functions
		
	Returns:
		str: Error message
	"""
	msg = parser_lib.get_parse_error_message(error_code)
	return msg.decode('utf-8')


def print_parsed_eeprom(result: ParsedEeprom):
	"""
	Print a ParsedEeprom structure in a human-readable format.
	
	Args:
		result: ParsedEeprom object returned from parse_rpi_hat_eeprom
	"""
	print(f"EEPROM Signature: {result.header.signature.decode('ascii')}")
	print("Valid Raspberry Pi HAT EEPROM detected!")
	
	print("\nHeader Info:")
	print(f"  Signature: {result.header.signature.decode('ascii')}")
	print(f"  Version: 0x{result.header.version:02x}")
	print(f"  Number of Atoms: {result.header.numatoms}")
	print(f"  EEPROM Length: {result.header.eeplen} bytes")
	
	if result.has_vendor_info:
		print("\nVendor Information:")
		print(f"  Product ID: {result.vendor_info.product_id}")
		print(f"  Product Version: {result.vendor_info.product_version}")
		print(f"  Vendor: {result.vendor_info.vendor.decode('utf-8')}")
		print(f"  Board: {result.vendor_info.product.decode('utf-8')}")
	
	if result.has_custom_data:
		print(f"\nCustom Data ({result.custom_data.data_length} bytes):")
		if result.custom_data.is_json:
			# Try to decode as JSON
			try:
				import json
				data_bytes = bytes(result.custom_data.data[:result.custom_data.data_length])
				data_str = data_bytes.decode('utf-8').rstrip('\x00')
				data_json = json.loads(data_str)
				print("  JSON Parsed:")
				print(json.dumps(data_json, indent=4))
			except Exception as e:
				print(f"  (JSON parsing failed: {e})")
				print(f"  Hex: {data_bytes.hex()}")
		else:
			data_bytes = bytes(result.custom_data.data[:result.custom_data.data_length])
			print(f"  Hex: {data_bytes.hex()}")
			ascii_repr = ''.join(chr(b) if 32 <= b < 127 else '.' for b in data_bytes)
			print(f"  ASCII: {ascii_repr}")
	
	if result.has_dt_overlay:
		print(f"\nDevice Tree Overlay: Present ({result.dt_overlay_length} bytes)")
		print(f"  Overlay: {result.dt_overlay.decode('utf-8')}")


# Example usage
if __name__ == '__main__':
	# Example: Read a binary file and parse it
	import sys
	
	if len(sys.argv) > 1:
		filename = sys.argv[1]
		try:
			with open(filename, 'rb') as f:
				data = f.read()
			
			print(f"Parsing {filename} ({len(data)} bytes)...\n")
			
			# Method 1: Parse and get structured data
			status, result = parse_rpi_hat_eeprom(data)
			if status == PARSE_OK:
				print_parsed_eeprom(result)
			else:
				print(f"Error: {get_parse_error_message(status)}")
			
			print("\n" + "="*80)
			print("Method 2: Direct printing from DLL")
			print("="*80 + "\n")
			
			# Method 2: Parse and print directly from DLL
			status = parse_and_print_eeprom(data)
			if status != PARSE_OK:
				print(f"Error: {get_parse_error_message(status)}")
				
		except FileNotFoundError:
			print(f"Error: File not found: {filename}")
		except Exception as e:
			print(f"Error: {e}")
	else:
		print("Usage: python rpi_hat_parser_wrapper.py <eeprom_file.bin>")
