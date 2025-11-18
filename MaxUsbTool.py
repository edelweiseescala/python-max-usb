"""
MAXUSB I2C EEPROM Reader/Writer using libMPSSE

This script provides functions to read and write I2C EEPROM devices using FTDI chips.
Supports both 8-bit and 16-bit addressing modes.

Main Functions:
- read_register_8bit():  Read from I2C devices with 8-bit register addressing
- read_register_16bit(): Read from I2C EEPROMs with 16-bit addressing
- scan_i2c_devices():    Scan for all I2C devices on the bus
- read_eeprom_to_file(): Read entire EEPROM and save to binary file
- compare_binary_files(): Compare two binary files byte-by-byte

Usage:
1. Connect FTDI device to I2C EEPROM
2. Run script to read EEPROM contents
3. Compare with original.bin if available
"""

import ctypes
import time
from enum import Enum

#Constants for FTDI config
START_BIT                   = 0x01
STOP_BIT                    = 0x02
BREAK_ON_NACK               = 0x04
NACK_LAST_BYTE              = 0x08
FAST_TRANSFER_BYTES         = 0x10
FAST_TRANSFER_BITS          = 0x20
FAST_TRANSFER               = 0x30
NO_ADDRESS                  = 0x40
I2C_DISABLE_3PHASE_CLOCKING = 0x01
I2C_ENABLE_DRIVE_ONLY_ZERO  = 0x02

class Channel():
	def __init__(self, name, index):
		self.name = name
		self.index = index
		self.handle = ctypes.c_void_p()

		
class ChannelConfig(ctypes.Structure):
	_fields_ = [('ClockRate', ctypes.c_int),
				('LatencyTimer', ctypes.c_ubyte),
				('Options', ctypes.c_int)]

	
class ChannelInfo(ctypes.Structure):
	_fields_ = [('Flags', ctypes.c_ulong),
				('Type', ctypes.c_ulong),
				('ID', ctypes.c_ulong),
				('LocId', ctypes.c_ulong),
				('SerialNumber', ctypes.c_char*16),
				('Description', ctypes.c_char*64),
				('ftHandle', ctypes.c_void_p)]
	
def __repr__(self):
		values = ', '.join(f'{name}={value}' for name, value in self._asdict().items())
		return f'<{self.__class__.__name__}: {values}>'
	
def _asdict(self):
		return {field[0]: getattr(self, field[0]) for field in self._fields_}
	
class FT_STATUS(Enum):
	FT_OK                             = 0
	FT_INVALID_HANDLE                 = 1
	FT_DEVICE_NOT_FOUND               = 2
	FT_DEVICE_NOT_OPENED              = 3
	FT_IO_ERROR                       = 4
	FT_INSUFFICIENT_RESOURCES         = 5
	FT_INVALID_PARAMETER              = 6
	FT_INVALID_BAUD_RATE              = 7
	FT_DEVICE_NOT_OPENED_FOR_ERASE    = 8
	FT_DEVICE_NOT_OPENED_FOR_WRITE    = 9
	FT_FAILED_TO_WRITE_DEVICE         = 10
	FT_EEPROM_READ_FAILED             = 11
	FT_EEPROM_WRITE_FAILED            = 12
	FT_EEPROM_ERASE_FAILED            = 13
	FT_EEPROM_NOT_PRESENT             = 14
	FT_EEPROM_NOT_PROGRAMMED          = 15
	FT_INVALID_ARGS                   = 16
	FT_NOT_SUPPORTED                  = 17
	FT_OTHER_ERROR                    = 18
	FT_DEVICE_LIST_NOT_READ           = 19

def status(code):
	return FT_STATUS(code).name

class MaxUsbTool:
	def __init__(self):
		self.libMPSSE = ctypes.cdll.LoadLibrary('./libMPSSE.dll')
		self.slave_address = 0x0
		print('Loaded MPSSE library')

		print('Listing channels...')
		self.libMPSSE.Init_libMPSSE()
		channel_count = ctypes.c_int()
		ret = self.libMPSSE.I2C_GetNumChannels(ctypes.byref(channel_count))
		print(f'Found {channel_count.value} channels (status {status(ret)})')

		print('\nAvailable channels:')
		for i in range(channel_count.value):
			ch_info = ChannelInfo()
			ret = self.libMPSSE.I2C_GetChannelInfo(i, ctypes.byref(ch_info))
			if ret == 0:
				desc = ch_info.Description.decode()
				serial = ch_info.SerialNumber.decode()
				print(f'  Channel {i}: {desc} (Serial: {serial}, LocId: 0x{ch_info.LocId:x})')

		target_channel_name = 'Dual RS232-HS A'
		channel_index = None
		for i in range(channel_count.value):
			ch_info = ChannelInfo()
			ret = self.libMPSSE.I2C_GetChannelInfo(i, ctypes.byref(ch_info))
			if ret == 0 and target_channel_name in ch_info.Description.decode():
				channel_index = i
				print(f'\nFound target channel at index {i}: {ch_info.Description.decode()}')
				break

		if channel_index is None:
			print(f'ERROR: Could not find channel with name "{target_channel_name}"')
			exit(1)

		self.channel = Channel(target_channel_name, channel_index)
		mode = START_BIT | STOP_BIT | NACK_LAST_BYTE
		channel_info = ChannelInfo()
		print(f'Getting info for channel with index {self.channel.index}...')
		ret = self.libMPSSE.I2C_GetChannelInfo(self.channel.index, ctypes.byref(channel_info))
		print(f'Channel description: {channel_info.Description.decode()} (status {status(ret)})')
		ret = self.libMPSSE.I2C_OpenChannel(self.channel.index, ctypes.byref(self.channel.handle))
		print(f'Channel {self.channel.name} opened with handle: 0x{self.channel.handle.value:x} (status {status(ret)})')
		channel_conf = ChannelConfig(400000, 25, 0)
		ret = self.libMPSSE.I2C_InitChannel(self.channel.handle, ctypes.byref(channel_conf))
		print(f'InitChannel() {self.channel.name} (status {status(ret)})')
		
		time.sleep(0.1)

	def __del__(self):
		if hasattr(self, 'channel'):
			ret = self.libMPSSE.I2C_CloseChannel(self.channel.handle)
			print(f'CloseChannel() {self.channel.name} (status {status(ret)})')

	def set_slave_address(self, address):
		"""
		Set the I2C slave device address.
		
		Args:
			address: I2C slave address (7-bit, 0x00-0x7F)
		"""
		if isinstance(address, str):
			address = int(address, 16) if address.startswith('0x') else int(address, 16)
		
		if 0x00 <= address <= 0x7F:
			self.slave_address = address
			print(f'Slave address set to 0x{self.slave_address:02x}')
		else:
			print(f'Error: Invalid I2C address 0x{address:02x}. Must be 0x00-0x7F')
			
	def read_register_8bit(self, register_addr, num_bytes=1):
		"""
		Read num_bytes from a specific register using 8-bit addressing.
		Use this for standard I2C devices with 8-bit register addresses.
		
		Args:
			register_addr: Register address to read from (8-bit)
			num_bytes: Number of bytes to read (default 1)
		
		Returns:
			tuple: (status_code, list of bytes read)
		"""
		write_buf = (ctypes.c_ubyte * 1)(register_addr)
		bytes_written = ctypes.c_ulong()

		ret = self.libMPSSE.I2C_DeviceWrite(self.channel.handle, self.slave_address, 1, write_buf, 
									ctypes.byref(bytes_written), 
									START_BIT | FAST_TRANSFER_BYTES)

		if ret != 0:
			return (ret, [])

		read_buf = (ctypes.c_ubyte * num_bytes)()
		bytes_read = ctypes.c_ulong()

		ret = self.libMPSSE.I2C_DeviceRead(self.channel.handle, self.slave_address, num_bytes, read_buf, 
									ctypes.byref(bytes_read), 
									START_BIT | STOP_BIT | FAST_TRANSFER_BYTES)

		data = list(read_buf[:bytes_read.value])
		return (ret, data)

	def read_register_16bit(self, register_addr, num_bytes=1):
		"""
		Read from an I2C EEPROM using 16-bit addressing.
		Use this for EEPROMs that require 2-byte address (MSB, LSB).
		
		IMPORTANT: Uses REPEATED START condition (no STOP between address write and data read)
		to maintain address context. This is critical for proper EEPROM sequential reads.
		
		Args:
			register_addr: 16-bit register address
			num_bytes: Number of bytes to read (default 1)
		
		Returns:
			tuple: (status_code, list of bytes read)
		"""
		write_buf = (ctypes.c_ubyte * 2)((register_addr >> 8) & 0xFF, register_addr & 0xFF)
		bytes_written = ctypes.c_ulong()
		
		ret = self.libMPSSE.I2C_DeviceWrite(self.channel.handle, self.slave_address, 2, write_buf, 
									ctypes.byref(bytes_written), 
									START_BIT | FAST_TRANSFER_BYTES)
		
		if ret != 0:
			return (ret, [])

		read_buf = (ctypes.c_ubyte * num_bytes)()
		bytes_read = ctypes.c_ulong()

		ret = self.libMPSSE.I2C_DeviceRead(self.channel.handle, self.slave_address, num_bytes, read_buf, 
									ctypes.byref(bytes_read), 
									START_BIT | STOP_BIT | FAST_TRANSFER_BYTES)

		data = list(read_buf[:bytes_read.value])
		return (ret, data)

	def scan_i2c_devices(self):
		"""
		Scan for I2C devices on the bus.

		Returns:
			list: List of I2C addresses where devices were found
		"""
		print(f'\nScanning for I2C devices on channel {self.channel.name}...')
		devices_found = []

		for addr in range(0x08, 0x78):
			test_buf = (ctypes.c_ubyte * 1)()
			transferred = ctypes.c_ulong()
			test_mode = START_BIT | STOP_BIT
			ret = self.libMPSSE.I2C_DeviceRead(self.channel.handle, addr, 1, test_buf, 
										ctypes.byref(transferred), test_mode)
			if ret == 0:
				devices_found.append(addr)
				print(f'  Found device at address 0x{addr:02x} (decimal {addr})')

		if not devices_found:
			print('  No I2C devices found on the bus')
		else:
			print(f'\nTotal devices found: {len(devices_found)}')

		return devices_found

	def read_eeprom_to_file(self, start_addr, size, should_save=False, filename="eeprom_readback.bin"):
		"""
		Read entire EEPROM content and save to a binary file.
		Uses 16-bit addressing for EEPROMs that require it.
		
		Args:
			start_addr: Starting register address (usually 0x00)
			size: Number of bytes to read (EEPROM size, e.g., 256, 512, 1024, etc.)
			should_save: Boolean if eeprom should be saved to a file
			filename: Output filename for the binary dump
		
		Returns:
			tuple: (status_code, bytes_read)
		"""
		write_buf = (ctypes.c_ubyte * 2)()
		write_buf[0] = (start_addr >> 8) & 0xFF
		write_buf[1] = start_addr & 0xFF
		bytes_written = ctypes.c_ulong()

		ret = self.libMPSSE.I2C_DeviceWrite(self.channel.handle, self.slave_address, 
											2, write_buf,
											ctypes.byref(bytes_written),
											START_BIT | FAST_TRANSFER_BYTES)
		if ret != 0:
			print(f'Error setting EEPROM address pointer (status {status(ret)})')
			return (ret, b'')

		time.sleep(0.01)

		print(f'\nReading {size} bytes from EEPROM at address 0x{self.slave_address:02x} using 16-bit addressing...')

		read_buf = (ctypes.c_ubyte * size)()
		bytes_read = ctypes.c_ulong()

		ret = self.libMPSSE.I2C_DeviceRead(self.channel.handle, self.slave_address, size, read_buf, 
									ctypes.byref(bytes_read), 
									START_BIT | STOP_BIT | FAST_TRANSFER_BYTES)

		if ret != 0:
			print(f'  Error reading EEPROM (status {status(ret)})')
			return (ret, b'')

		all_data = list(read_buf[:bytes_read.value])
		print(f'  Progress: 100.0%')

		if (should_save == False):
			return (0, bytes(all_data))

		with open(filename, 'wb') as f:
			f.write(bytes(all_data))

		print(f'  Saved {len(all_data)} bytes to {filename}')
		return (0, bytes(all_data))

	def compare_binary_files(self, file1, file2):
		"""Compare two binary files byte by byte and display all data"""
		try:
			with open(file1, 'rb') as f1:
				data1 = f1.read()
		except FileNotFoundError:
			print(f'Error: File "{file1}" not found')
			return
		
		try:
			with open(file2, 'rb') as f2:
				data2 = f2.read()
		except FileNotFoundError:
			print(f'Error: File "{file2}" not found')
			return
		
		print(f'\nComparing files:')
		print(f'  {file1}: {len(data1)} bytes')
		print(f'  {file2}: {len(data2)} bytes')
		
		if len(data1) != len(data2):
			print(f'\n[WARNING] File sizes differ: {len(data1)} vs {len(data2)} bytes')

		print('\n' + '='*80)
		print(f'{"Addr":<6} {"Original":<24} {"Readback":<24} {"Match":<6} {"ASCII"}')
		print('='*80)
		
		min_len = min(len(data1), len(data2))
		mismatches = []

		for i in range(0, min_len, 8):
			chunk_size = min(8, min_len - i)

			chunk1 = data1[i:i+chunk_size]
			chunk2 = data2[i:i+chunk_size]

			hex1 = ' '.join(f'{b:02x}' for b in chunk1)
			hex2 = ' '.join(f'{b:02x}' for b in chunk2)

			match = 'OK' if chunk1 == chunk2 else 'DIFF'
			if chunk1 != chunk2:
				for j in range(chunk_size):
					if chunk1[j] != chunk2[j]:
						mismatches.append((i+j, chunk1[j], chunk2[j]))

			ascii_repr = ''.join(chr(b) if 32 <= b < 127 else '.' for b in chunk1)

			print(f'0x{i:04x} {hex1:<24} {hex2:<24} {match:<6} {ascii_repr}')

		print('='*80)
		if not mismatches and len(data1) == len(data2):
			print(f'\n[OK] Files are identical! All {len(data1)} bytes match.')
		else:
			print(f'\n[ERROR] Found {len(mismatches)} byte differences out of {min_len} bytes')
			print(f'Match rate: {((min_len - len(mismatches)) / min_len * 100):.1f}%')

	def write_eeprom_from_file(self, start_addr, filename):
		"""
		Write data from a binary file to EEPROM.
		Uses 16-bit addressing and page writes for efficiency.
		
		IMPORTANT: For 24C32 EEPROM (4KB, 32-byte pages):
		- Page size: 32 bytes
		- Write cycle time: 5ms typical, 10ms max
		- WP pin must be LOW to allow writes
		- If WP pin is HIGH, upper half (0x800-0xFFF) is write-protected
		
		Args:
			start_addr: Starting register address (usually 0x00)
			filename: Input filename containing binary data to write
		
		Returns:
			tuple: (status_code, bytes_written)
		"""
		try:
			with open(filename, 'rb') as f:
				data = f.read()
		except FileNotFoundError:
			print(f'Error: File "{filename}" not found')
			return (1, 0)
		
		print(f'\nWriting {len(data)} bytes from {filename} to EEPROM at address 0x{self.slave_address:02x}...')
		
		page_size = 32  # 24C32 EEPROM has 32-byte pages
		total_written = 0
		
		addr = start_addr
		while addr < start_addr + len(data):
			if addr >= 0x40 and addr == 0x40:
				print(f'\n  [INFO] Waiting before writing to address 0x{addr:04x}...')
				time.sleep(0.1)  # 100ms delay before crossing the 64-byte boundary
			
			page_start = (addr // page_size) * page_size
			page_end = page_start + page_size
			bytes_remaining_in_page = page_end - addr

			offset = addr - start_addr
			bytes_remaining_total = len(data) - offset
			bytes_to_write = min(bytes_remaining_in_page, bytes_remaining_total)
			page_data = data[offset:offset + bytes_to_write]

			write_buf = (ctypes.c_ubyte * (2 + bytes_to_write))()
			write_buf[0] = (addr >> 8) & 0xFF  # Address MSB
			write_buf[1] = addr & 0xFF          # Address LSB
			for i, byte in enumerate(page_data):
				write_buf[2 + i] = byte

			bytes_written = ctypes.c_ulong()
			ret = self.libMPSSE.I2C_DeviceWrite(self.channel.handle, self.slave_address, 2 + bytes_to_write, write_buf,
										ctypes.byref(bytes_written), 
										START_BIT | STOP_BIT | FAST_TRANSFER_BYTES)
			
			if ret != 0:
				print(f'\n  Error writing at address 0x{addr:04x} (status {status(ret)})')
				return (ret, total_written)
			
			total_written += bytes_to_write

			time.sleep(0.01)

			if addr % 64 == 0 or total_written == len(data):
				progress = total_written / len(data) * 100
				print(f'  Progress: {progress:.1f}%', end='\r')

			addr += bytes_to_write

		print(f'  Progress: 100.0%')
		print(f'  Successfully wrote {total_written} bytes to EEPROM')
		
		return (0, total_written)

	def verify_eeprom_write(self, start_addr, filename):
		"""
		Verify that EEPROM contents match the file.
		
		Args:
			start_addr: Starting address
			filename: File to compare against
		
		Returns:
			bool: True if verification passed, False otherwise
		"""
		try:
			with open(filename, 'rb') as f:
				original_data = f.read()
		except FileNotFoundError:
			print(f'Error: File "{filename}" not found')
			return False
		
		print(f'\nVerifying {len(original_data)} bytes...')
		
		time.sleep(0.1)

		ret, all_data = self.read_register_16bit(start_addr, num_bytes=len(original_data))
		
		if ret != 0:
			print(f'  Error reading EEPROM (status {status(ret)})')
			return False

		readback_data = bytes(all_data)
		mismatches = []
		
		for i, (orig, read) in enumerate(zip(original_data, readback_data)):
			if orig != read:
				mismatches.append((i, orig, read))

		if not mismatches:
			print(f'[OK] Verification passed! All {len(original_data)} bytes match.')
			return True
		else:
			print(f'[ERROR] Verification failed! {len(mismatches)} bytes differ:')
			for addr, orig, read in mismatches[:10]:  # Show first 10 differences
				print(f'  Address 0x{addr:04x}: Expected 0x{orig:02x}, Read 0x{read:02x}')
			if len(mismatches) > 10:
				print(f'  ... and {len(mismatches) - 10} more differences')
			return False

	def parse_rpi_hat_eeprom(self, start_addr, size):
		"""
		Parse and display Raspberry Pi HAT EEPROM contents.
		Uses 16-bit addressing for EEPROMs that require it.
		
		Args:
			start_addr: Starting register address (usually 0x00)
			size: Number of bytes to read (EEPROM size, e.g., 256, 512, 1024, etc.)
		
		Returns:
			int: status_code (0 for success)
		"""
		print(f'\nReading {size} bytes from EEPROM for parsing...')
		ret, eeprom_data = self.read_register_16bit(start_addr, num_bytes=size)

		if ret != 0:
			print(f'Error reading EEPROM (status {status(ret)})')
			return ret

		signature = bytes(eeprom_data[0:4])
		print(f'EEPROM Signature: {signature}')

		if signature == b'R-Pi':
			print('Valid Raspberry Pi HAT EEPROM detected!')
			header = {
				'signature': signature.decode('ascii'),
				'version': eeprom_data[4],
				'reserved': eeprom_data[5],
				'numatoms': (eeprom_data[6]),
				'eeplen': (eeprom_data[8])
			}
			
			print(f'\nHeader Info:')
			print(f'  Signature: {header["signature"]}')
			print(f'  Version: 0x{header["version"]:02x}')
			print(f'  Number of Atoms: {header["numatoms"]}')
			print(f'  EEPROM Length: {header["eeplen"]} bytes')
			
			curr_atom = 0
			curr_address = 12
			while (curr_atom < header["numatoms"]):
				atom_header = {
					'atom_type': eeprom_data[curr_address],
					'atom_count': eeprom_data[curr_address+2],
					'dlen': eeprom_data[curr_address+4]
				}
				curr_address = curr_address + 8

				if (atom_header["atom_type"] == 1):
					uuid = bytes(eeprom_data[curr_address:curr_address+16])
					product_id = eeprom_data[curr_address+16]
					product_version = eeprom_data[curr_address+18]
					print(f"Product ID: {product_id}")
					print(f"Product Version: {product_version}")
					vendor_len = eeprom_data[curr_address+20]
					product_len = eeprom_data[curr_address+21]
					vendor = bytes(eeprom_data[curr_address+22:curr_address+22+vendor_len])
					product = bytes(eeprom_data[curr_address+22+vendor_len:curr_address+22+vendor_len+product_len])
					print(f"Vendor: {vendor}")
					print(f"Board: {product}")
				elif (atom_header["atom_type"] == 3):
					overlay = bytes(eeprom_data[curr_address:curr_address+atom_header["dlen"] - 2])
					print(f"{overlay}")
				elif (atom_header["atom_type"] == 4):
					print("custom")
				else:
					print(F'not supported {atom_header["atom_type"]}')

				curr_atom += 1
				curr_address = curr_address + atom_header["dlen"]
			return ret
		else:
			print('Not a valid Raspberry Pi HAT EEPROM format')
			return ret
