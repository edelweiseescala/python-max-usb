from MaxUsbTool import MaxUsbTool
import os

maxUsbTool = MaxUsbTool()
print('\n' + '='*80)
print('Do you want to scan for I2C devices? (y/n)')
scan_choice = input('> ').strip().lower()
if scan_choice == 'y':
	devices = maxUsbTool.scan_i2c_devices()

print('\n' + '='*80)
print('Enter the I2C device address (in hex, e.g., 0x52 or 52):')
addr_input = input('> ').strip()
try:
	if addr_input.startswith('0x') or addr_input.startswith('0X'):
		write_address = int(addr_input, 16)
	else:
		write_address = int(addr_input, 16)

	maxUsbTool.set_slave_address(write_address)
	print(f'Using I2C device address: 0x{write_address:02x}')
except ValueError:
	print(f'Invalid address format. Using default: 0x52')
	maxUsbTool.set_slave_address(0x52)

while 1:
	print('\n' + '='*80)
	print('Select operation:')
	print('  1. Read EEPROM to file')
	print('  2. Write file to EEPROM')
	print('  3. Write and verify')
	print('  4. Parse R-PI HAT+ EEPROM')
	print('  5. Compare bin files')
	print('  q - quit')
	print('='*80)

	choice = input('Enter choice (1-4): ').strip()

	if choice == '1':
		eeprom_size = 256
		should_save = True
		ret, eeprom_data = maxUsbTool.read_eeprom_to_file(0x00, eeprom_size, should_save,'eeprom_readback.bin')
		
		print('\n[OK] EEPROM read successful!')

	elif choice == '2':
		print('\nPlease provide eeprom bin file')
		eeprom_file = input('eeprom file: ').strip()

		if not os.path.exists(eeprom_file):
			print('\nError: file does not exist')
			continue

		print('\n[WARNING] This will OVERWRITE your EEPROM with data from the eeprom provided')
		confirm = input('Are you sure? Type YES to confirm: ').strip()
		
		if confirm == 'YES':
			ret, bytes_written = maxUsbTool.write_eeprom_from_file(0x00, eeprom_file)
			if ret == 0:
				print(f'\n[OK] Successfully wrote {bytes_written} bytes to EEPROM')
			else:
				print('\n[ERROR] Write failed.')
		else:
			print('Write cancelled.')

	elif choice == '3':
		print('\nPlease provide eeprom bin file')
		eeprom_file = input('eeprom file: ').strip()

		if not os.path.exists(eeprom_file):
			print('\nError: file does not exist')
			continue

		print('\n[WARNING] This will OVERWRITE your EEPROM with data from the eeprom provided')
		confirm = input('Are you sure? Type YES to confirm: ').strip()
		
		if confirm == 'YES':
			ret, bytes_written = maxUsbTool.write_eeprom_from_file(0x00, eeprom_file)
			
			if ret == 0:
				print(f'\n[OK] Successfully wrote {bytes_written} bytes to EEPROM')
				
				if maxUsbTool.verify_eeprom_write(0x00, eeprom_file):
					print('\n[SUCCESS] EEPROM write and verification completed successfully!')
				else:
					print('\n[ERROR] Verification failed. EEPROM data does not match file.')
			else:
				print('\n[ERROR] Write failed.')
		else:
			print('Write cancelled.')

	elif choice == '4':
		eeprom_size = 256
		ret = maxUsbTool.parse_rpi_hat_eeprom(0x00, eeprom_size)

	elif choice == '5':
		print('\nPlease provide eeprom bin file')
		eeprom_file_1 = input('eeprom file: ').strip()

		if not os.path.exists(eeprom_file_1):
			print(f"File {eeprom_file_1} does not exist")
			continue

		print('\nPlease provide eeprom bin file to compare with')
		eeprom_file_2 = input('eeprom file: ').strip()

		if not os.path.exists(eeprom_file_2):
			print(f"File {eeprom_file_2} does not exist")
			continue

		maxUsbTool.compare_binary_files(eeprom_file_1, eeprom_file_2)

	elif choice == 'q':
		break

	else:
		print('Invalid choice. Exiting.')
