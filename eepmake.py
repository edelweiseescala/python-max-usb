#!/usr/bin/env python3
"""
EEPROM Text File Parser and Binary Generator (Python version)
Parses EEPROM text file and creates binary .eep file
Usage: python3 eepmake.py [-v1] input_file output_file [dt_file] [-c custom_file_1 ... custom_file_n]

This is a Python port of the original C eepmake tool.
"""

import sys
import os
import struct
import argparse
from dataclasses import dataclass, field
from typing import List, Optional, BinaryIO
import uuid
import re
import json

#CONSTANTS
CRC_LEN = 2
EEPLEN_INDEX = 8
GPIO_MIN = 2
GPIO_COUNT = 28
GPIO_COUNT_BANK1 = 18
GPIO_COUNT_TOTAL = GPIO_COUNT + GPIO_COUNT_BANK1

HEADER_SIGN = 0x69502D52  # struct.unpack('<I', b'R-Pi')[0]

class AtomType:
	INVALID = 0x0000
	VENDOR = 0x0001
	GPIO = 0x0002
	DT = 0x0003
	CUSTOM = 0x0004
	GPIO_BANK1 = 0x0005
	POWER_SUPPLY = 0x0006
	HINVALID = 0xffff

class FileVersion:
	HATV1 = 0x01
	HATPLUS = 0x02
	DEFAULT = HATPLUS

@dataclass
class VendorInfo:
	serial: List[int] = field(default_factory=lambda: [0, 0, 0, 0])
	pid: int = 0
	pver: int = 0
	vstr: str = ""
	pstr: str = ""

	@property
	def vslen(self) -> int:
		return len(self.vstr)

	@property 
	def pslen(self) -> int:
		return len(self.pstr)

@dataclass
class GpioMap:
	flags: int = 0
	power: int = 0
	pins: List[int] = field(default_factory=lambda: [0] * GPIO_COUNT)

@dataclass
class PowerSupply:
	current_supply: int = 0  #milliamps

@dataclass
class VarBlob:
	data: bytearray = field(default_factory=bytearray)

	@property
	def dlen(self) -> int:
		return len(self.data)

class EepMake:
	def __init__(self):
		self.vinf = VendorInfo()
		self.dt_blob = VarBlob()
		self.custom_blobs: List[VarBlob] = []
		self.data_blob: Optional[VarBlob] = None
		self.in_string = False

		# Common features
		self.product_serial_set = False
		self.product_id_set = False
		self.product_ver_set = False
		self.vendor_set = False
		self.product_set = False
		self.has_dt = False

		# Legacy V1 features
		self.gpiomap_bank0 = GpioMap()
		self.gpiomap_bank1 = GpioMap()
		self.has_gpio_bank0 = False
		self.has_gpio_bank1 = False
		self.gpio_drive_set = False
		self.gpio_slew_set = False
		self.gpio_hysteresis_set = False
		self.gpio_power_set = False
		self.bank1_gpio_drive_set = False
		self.bank1_gpio_slew_set = False
		self.bank1_gpio_hysteresis_set = False

		# HAT+ features
		self.power_supply = PowerSupply()
		self.current_supply_set = False
		self.has_power_supply = False

		self.hat_format = FileVersion.HATPLUS
		self.atom_count = 0

	def fatal_error(self, msg: str, *args):
		"""Print fatal error and exit."""
		print(f"FATAL: {msg}" % args if args else f"FATAL: {msg}")
		sys.exit(1)

	def hatplus_required(self, cmd: str):
		"""Check if HAT+ format is required for this command."""
		if self.hat_format >= FileVersion.HATPLUS:
			return
		print(f"'{cmd}' not supported on V1 HAT")
		sys.exit(1)

	def hatplus_unsupported(self, cmd: str):
		"""Check if command is unsupported on HAT+."""
		if self.hat_format == FileVersion.HATV1:
			return
		print(f"'{cmd}' not supported on HAT+")
		sys.exit(1)

	def add_data_byte(self, byte: int):
		"""Add a byte to the current data blob."""
		if self.data_blob is None:
			return
		self.data_blob.data.append(byte)

	def finish_data(self):
		"""Finish the current data blob."""
		self.data_blob = None

	def add_custom_blob(self) -> VarBlob:
		"""Add a new custom blob and return it."""
		blob = VarBlob()
		self.custom_blobs.append(blob)
		return blob

	def parse_string(self, line: str) -> int:
		"""Parse string data with escape sequences."""
		i = 0
		while i < len(line):
			c = line[i]
			if c == '\\' and i + 1 < len(line):
				c2 = line[i + 1]
				if c2 == 'r':
					self.add_data_byte(ord('\r'))
				elif c2 == '\\':
					self.add_data_byte(ord('\\'))
				elif c2 == '0':
					self.add_data_byte(0)
					break
				elif c2 == '"':
					self.in_string = False
					self.finish_data()
					break
				else:
					self.fatal_error(f"Bad escape sequence '\\{c2}'")
				i += 2
			elif c == '\r':
				i += 1
				continue
			else:
				self.add_data_byte(ord(c))
				i += 1
		return 0

	def parse_data(self, line: str) -> int:
		"""Parse hex data or string data."""
		line = line.strip()

		if line.startswith('"'):
			if len(line) == 1 or line[1] in '\n\r':
				self.in_string = True
				return 0

			if len(line) >= 2 and line.endswith('"') and '\\' not in line:
				content = line[1:-1]
				for char in content:
					if not char.isprintable() and char not in '\t\n\r':
						self.fatal_error(f"Bad character 0x{ord(char):02x} in simple string '{line}'")
						return -1
					self.add_data_byte(ord(char))
				self.finish_data()
				return 0

			i = 1  # Skip opening quote
			while i < len(line):
				char = line[i]
				if char == '\\' and i + 1 < len(line):
					next_char = line[i + 1]
					if next_char == 'r':
						self.add_data_byte(ord('\r'))
						i += 2
					elif next_char == '\\':
						self.add_data_byte(ord('\\'))
						i += 2
					elif next_char == '"':
						self.add_data_byte(ord('"'))
						i += 2
					elif next_char == 'n':
						self.add_data_byte(ord('\n'))
						i += 2
					elif next_char == 't':
						self.add_data_byte(ord('\t'))
						i += 2
					elif next_char == '0':
						self.add_data_byte(0)
						i += 2
					else:
						self.fatal_error(f"Bad escape sequence '\\{next_char}' in simple string")
						return -1
				elif char == '"':
					self.finish_data()
					return 0
				else:
					if not char.isprintable():
						self.fatal_error(f"Bad character 0x{ord(char):02x} in simple string '{line}'")
						return -1
					self.add_data_byte(ord(char))
					i += 1

			self.fatal_error(f"Unclosed string: {line}")
			return -1

		hex_chars = ''.join(c for c in line if c in '0123456789abcdefABCDEF')
		
		if len(hex_chars) % 2 != 0:
			print("Error: data must have an even number of hex digits")
			return -1

		for i in range(0, len(hex_chars), 2):
			byte_val = int(hex_chars[i:i+2], 16)
			self.add_data_byte(byte_val)

		return 0

	def parse_command(self, cmd: str, line: str) -> int:
		"""Parse a command from the input file."""
		parts = line.split(None, 1)
		if len(parts) < 2:
			return 0

		args = parts[1].strip()

		if cmd == "product_uuid":
			self.product_serial_set = True
			match = re.search(r'([0-9a-fA-F]{8})-([0-9a-fA-F]{4})-([0-9a-fA-F]{4})-([0-9a-fA-F]{4})-([0-9a-fA-F]{4})([0-9a-fA-F]{8})', args)
			if match:
				self.vinf.serial[3] = int(match.group(1), 16)
				self.vinf.serial[2] = (int(match.group(2), 16) << 16) | int(match.group(3), 16)
				self.vinf.serial[1] = (int(match.group(4), 16) << 16) | int(match.group(5), 16)
				self.vinf.serial[0] = int(match.group(6), 16)

				if (self.vinf.serial[3] == 0 and self.vinf.serial[2] == 0 and 
					self.vinf.serial[1] == 0 and self.vinf.serial[0] == 0):
					random_uuid = uuid.uuid4()
					uuid_bytes = random_uuid.bytes
					self.vinf.serial = list(struct.unpack('<4I', uuid_bytes))
			else:
				random_uuid = uuid.uuid4()
				uuid_bytes = random_uuid.bytes
				self.vinf.serial = list(struct.unpack('<4I', uuid_bytes))

		elif cmd == "product_id":
			self.product_id_set = True
			try:
				self.vinf.pid = int(args.split()[0], 16)
				if self.vinf.pid > 0xFFFF:
					print(f"Warning: product_id value 0x{self.vinf.pid:x} exceeds 16-bit limit, truncating")
					self.vinf.pid &= 0xFFFF
			except (ValueError, IndexError) as e:
				print(f"Error: Invalid product_id value '{args}'")
				return -1

		elif cmd == "product_ver":
			self.product_ver_set = True
			try:
				self.vinf.pver = int(args.split()[0], 16)
				if self.vinf.pver > 0xFFFF:
					print(f"Warning: product_ver value 0x{self.vinf.pver:x} exceeds 16-bit limit, truncating")
					self.vinf.pver &= 0xFFFF
			except (ValueError, IndexError) as e:
				print(f"Error: Invalid product_ver value '{args}'")
				return -1

		elif cmd == "vendor":
			self.vendor_set = True
			match = re.search(r'"([^"]*)"', args)
			if match:
				vendor_str = match.group(1)
				if len(vendor_str) > 255:
					print(f"Warning: vendor string too long ({len(vendor_str)} chars), truncating to 255")
					vendor_str = vendor_str[:255]
				self.vinf.vstr = vendor_str
			else:
				print("Error: vendor string must be in quotes")
				return -1

		elif cmd == "product":
			self.product_set = True
			match = re.search(r'"([^"]*)"', args)
			if match:
				product_str = match.group(1)
				if len(product_str) > 255:
					print(f"Warning: product string too long ({len(product_str)} chars), truncating to 255")
					product_str = product_str[:255]
				self.vinf.pstr = product_str
			else:
				print("Error: product string must be in quotes")
				return -1

		elif cmd == "current_supply":
			self.hatplus_required(cmd)
			try:
				self.power_supply.current_supply = int(args.split()[0])
				if self.power_supply.current_supply > 0xFFFFFFFF:
					print(f"Warning: current_supply value {self.power_supply.current_supply} exceeds 32-bit limit, truncating")
					self.power_supply.current_supply &= 0xFFFFFFFF
				if self.power_supply.current_supply:
					self.current_supply_set = True
					self.has_power_supply = True
			except (ValueError, IndexError) as e:
				print(f"Error: Invalid current_supply value '{args}'")
				return -1

		# GPIO commands (HAT V1 only)
		elif cmd == "gpio_drive":
			self.hatplus_unsupported(cmd)
			self.gpio_drive_set = True
			self.has_gpio_bank0 = True
			try:
				val = int(args.split()[0], 16)
				if 0 <= val <= 8:
					self.gpiomap_bank0.flags |= val
				else:
					print("Warning: gpio_drive property in invalid region, using default value instead")
			except (ValueError, IndexError) as e:
				print(f"Error: Invalid gpio_drive value '{args}'")
				return -1
				
		elif cmd == "gpio_slew":
			self.hatplus_unsupported(cmd)
			self.gpio_slew_set = True
			self.has_gpio_bank0 = True
			val = int(args.split()[0], 16)
			if 0 <= val <= 2:
				self.gpiomap_bank0.flags |= val << 4
			else:
				print("Warning: gpio_slew property in invalid region, using default value instead")

		elif cmd == "gpio_hysteresis":
			self.hatplus_unsupported(cmd)
			self.gpio_hysteresis_set = True
			self.has_gpio_bank0 = True
			val = int(args.split()[0], 16)
			if 0 <= val <= 2:
				self.gpiomap_bank0.flags |= val << 6
			else:
				print("Warning: gpio_hysteresis property in invalid region, using default value instead")

		elif cmd == "back_power":
			self.hatplus_unsupported(cmd)
			self.gpio_power_set = True
			self.has_gpio_bank0 = True
			val = int(args.split()[0], 16)
			if 0 <= val <= 2:
				self.gpiomap_bank0.power = val
			else:
				print("Warning: back_power property in invalid region, using default value instead")

		# GPIO setgpio command
		elif cmd == "setgpio":
			self.hatplus_unsupported(cmd)
			args_parts = args.split()
			if len(args_parts) < 3:
				print(f"Error: setgpio requires 3 arguments (gpio_num, function, pull), got {len(args_parts)}")
				return -1

			try:
				gpio_num = int(args_parts[0])
				fn = args_parts[1]
				pull = args_parts[2]
				
				if gpio_num < GPIO_MIN or gpio_num >= GPIO_COUNT_TOTAL:
					print("Error: GPIO number out of bounds")
					return -1

				if gpio_num >= GPIO_COUNT:
					gpiomap = self.gpiomap_bank1
					gpio_num -= GPIO_COUNT
					self.has_gpio_bank1 = True
				else:
					gpiomap = self.gpiomap_bank0

				pin = 0
				if fn == "INPUT":
					pin = 0
				elif fn == "OUTPUT":
					pin = 1
				elif fn == "ALT0":
					pin = 4
				elif fn == "ALT1":
					pin = 5
				elif fn == "ALT2":
					pin = 6
				elif fn == "ALT3":
					pin = 7
				elif fn == "ALT4":
					pin = 3
				elif fn == "ALT5":
					pin = 2
				else:
					print(f"Error: Unknown function '{fn}'")
					return -1

				if pull == "DEFAULT":
					pass
				elif pull == "UP":
					pin |= 0x10
				elif pull == "DOWN":
					pin |= 0x20
				elif pull == "NONE":
					pin |= 0x30
				else:
					print(f"Error: Unknown pull setting '{pull}'")
					return -1

				gpiomap.pins[gpio_num] = pin

			except (ValueError, IndexError) as e:
				print(f"Error: Invalid setgpio parameters '{args}'")
				return -1
		elif cmd == "custom_data":
			blob = self.add_custom_blob()
			self.data_blob = blob
			if len(parts) > 1 and parts[1].strip():
				return self.parse_data(parts[1])

		elif cmd == "end":
			self.finish_data()

		elif cmd == "dt_blob":
			self.hatplus_required(cmd)
			match = re.search(r'"([^"]*)"', args)
			if match:
				dt_name = match.group(1)
				self.dt_blob.data = bytearray(dt_name.encode('utf-8'))
				self.has_dt = True

		else:
			if not cmd.isalpha():
				if self.data_blob is None:
					blob = self.add_custom_blob()
					self.data_blob = blob
				return self.parse_data(line)
			else:
				print(f"Warning: Unknown command '{cmd}', ignoring")

		return 0

	def read_text(self, filename: str) -> int:
		"""Read and parse the input text file."""
		print(f"Opening file '{filename}' for read")

		try:
			with open(filename, 'r') as fp:
				line_count = 0
				for line in fp:
					line_count += 1
					
					if self.in_string:
						if self.parse_string(line):
							return -1
						continue

					if '#' in line:
						line = line[:line.index('#')]

					line = line.strip()

					if not line:
						continue

					if line[0].isalnum():
						parts = line.split(None, 1)
						command = parts[0]
						if self.parse_command(command, line):
							return -1
					else:
						print(f"Can't parse line {line_count}: {line}")

		except FileNotFoundError:
			self.fatal_error(f"Error opening input file '{filename}'")
			return -1

		self.finish_data()

		if not all([self.product_serial_set, self.product_id_set, self.product_ver_set, 
				   self.vendor_set, self.product_set]):
			print("Warning: required fields missing in vendor information, using default values")

		if self.hat_format == FileVersion.HATV1 and not self.has_gpio_bank0:
			self.fatal_error("GPIO bank 0 is required for HAT V1")

		if self.has_gpio_bank0 and not all([self.gpio_drive_set, self.gpio_slew_set, 
										  self.gpio_hysteresis_set, self.gpio_power_set]):
			print("Warning: required fields missing in GPIO map, using default values")

		if (self.has_gpio_bank1 and 
			not all([self.bank1_gpio_drive_set, self.bank1_gpio_slew_set, 
					self.bank1_gpio_hysteresis_set])):
			print("Warning: required fields missing in GPIO map of bank 1, using default values")

		if (self.hat_format != FileVersion.HATV1 and self.dt_blob.data and 
			self.dt_blob.data and not chr(self.dt_blob.data[0]).isalnum()):
			self.fatal_error("Only embed the name of the overlay")

		print("Done reading")
		return 0

	def read_blob_file(self, filename: str, blob_type: str, blob: VarBlob) -> int:
		"""Read a binary file into a blob."""
		print(f"Opening {blob_type} file '{filename}' for read")

		try:
			with open(filename, 'rb') as fp:
				data = fp.read()
				blob.data = bytearray(data)
				print(f"Adding {len(data)} bytes of {blob_type} data")
				return 0
		except FileNotFoundError:
			self.fatal_error(f"Error opening input file '{filename}'")
			return -1

	def read_json_custom_data(self, filename: str) -> int:
		"""Read custom data from a JSON file and create separate atoms for each entry."""
		print(f"Opening JSON custom data file '{filename}' for read")

		try:
			with open(filename, 'r') as fp:
				data = json.load(fp)

				if 'custom_data' not in data:
					print(f"Warning: No 'custom_data' array found in {filename}")
					return 0

				custom_data_array = data['custom_data']
				if not isinstance(custom_data_array, list):
					print(f"Warning: 'custom_data' is not an array in {filename}")
					return 0

				for i, entry in enumerate(custom_data_array):
					blob = self.add_custom_blob()
					
					json_str = json.dumps(entry, separators=(',', ':'))
					blob.data = bytearray(json_str.encode('utf-8'))

					print(f"Adding custom_data atom {i+1}: {len(blob.data)} bytes - {json_str}")

				print(f"Added {len(custom_data_array)} custom_data atoms from JSON file")
				return 0

		except FileNotFoundError:
			self.fatal_error(f"Error opening JSON file '{filename}'")
			return -1
		except json.JSONDecodeError as e:
			self.fatal_error(f"Error parsing JSON file '{filename}': {e}")
			return -1

	def calculate_crc16(self, data: bytes) -> int:
		"""Calculate CRC16 checksum for data using the same algorithm as the C code."""
		CRC16_POLY = 0x8005
		crc_state = 0

		for byte_val in data:
			bits_read = 0
			while bits_read < 8:
				bit_flag = crc_state >> 15

				crc_state <<= 1
				crc_state |= (byte_val >> bits_read) & 1
				crc_state &= 0xFFFF

				bits_read += 1

				if bit_flag:
					crc_state ^= CRC16_POLY

		for _ in range(16):
			bit_flag = crc_state >> 15
			crc_state <<= 1
			crc_state &= 0xFFFF
			if bit_flag:
				crc_state ^= CRC16_POLY

		crc = 0
		i = 0x8000
		j = 0x0001
		while i != 0:
			if i & crc_state:
				crc |= j
			i >>= 1
			j <<= 1

		return crc & 0xFFFF

	def write_atom_header(self, fp: BinaryIO, atom_type: int, data_len: int):
		"""Write an atom header."""
		dlen = data_len + CRC_LEN
		fp.write(struct.pack('<HHI', atom_type, self.atom_count, dlen))
		self.atom_count += 1

	def write_atom_vendor(self, fp: BinaryIO):
		"""Write vendor info atom."""
		data = bytearray()

		for serial in self.vinf.serial:
			data.extend(struct.pack('<I', serial))

		data.extend(struct.pack('<HH', self.vinf.pid, self.vinf.pver))

		data.append(self.vinf.vslen)
		data.append(self.vinf.pslen)

		data.extend(self.vinf.vstr.encode('utf-8'))
		data.extend(self.vinf.pstr.encode('utf-8'))

		self.write_complete_atom(fp, AtomType.VENDOR, data)
		
	def write_complete_atom(self, fp: BinaryIO, atom_type: int, data: bytes):
		"""Write complete atom: header + data + CRC."""
		self.write_atom_header(fp, atom_type, len(data))

		fp.write(data)

		crc = self.calculate_crc16(data)
		fp.write(struct.pack('<H', crc))

	def write_atom_gpio(self, fp: BinaryIO, gpiomap: GpioMap, bank1: bool = False):
		"""Write GPIO atom."""
		data = bytearray()
		data.append(gpiomap.flags)
		data.append(gpiomap.power)

		pin_count = GPIO_COUNT_BANK1 if bank1 else GPIO_COUNT  
		for i in range(pin_count):
			if i < len(gpiomap.pins):
				data.append(gpiomap.pins[i])
			else:
				data.append(0)

		atom_type = AtomType.GPIO_BANK1 if bank1 else AtomType.GPIO
		self.write_complete_atom(fp, atom_type, data)

	def write_atom_power_supply(self, fp: BinaryIO):
		"""Write power supply atom."""
		data = struct.pack('<I', self.power_supply.current_supply)
		self.write_complete_atom(fp, AtomType.POWER_SUPPLY, data)

	def write_atom_var(self, fp: BinaryIO, blob: VarBlob, atom_type: int):
		"""Write variable data atom."""
		self.write_complete_atom(fp, atom_type, blob.data)

	def write_binary(self, filename: str) -> int:
		"""Write the binary EEPROM file."""
		print(f"Writing binary file '{filename}'")

		self.atom_count = 0

		try:
			with open(filename, 'wb') as fp:
				num_atoms = 1
				if self.has_gpio_bank0:
					num_atoms += 1
				if self.has_dt:
					num_atoms += 1
				if self.custom_blobs:
					num_atoms += len(self.custom_blobs)
				if self.has_gpio_bank1:
					num_atoms += 1
				if self.has_power_supply:
					num_atoms += 1

				header_data = struct.pack('<IBBHI', 
										HEADER_SIGN, 
										self.hat_format, 
										0,
										num_atoms,
										0xffffffff)
				fp.write(header_data)

				self.write_atom_vendor(fp)

				if self.has_gpio_bank0:
					self.write_atom_gpio(fp, self.gpiomap_bank0)

				if self.has_dt:
					print("Writing out DT...")
					self.write_atom_var(fp, self.dt_blob, AtomType.DT)

				for blob in self.custom_blobs:
					self.write_atom_var(fp, blob, AtomType.CUSTOM)

				if self.has_gpio_bank1:
					self.write_atom_gpio(fp, self.gpiomap_bank1, bank1=True)

				if self.has_power_supply:
					self.write_atom_power_supply(fp)

				file_size = fp.tell()
				fp.seek(EEPLEN_INDEX)
				fp.write(struct.pack('<I', file_size))
				
		except Exception as e:
			print(f"Error writing file {filename}: {e}")
			return -1
			
		return 0
