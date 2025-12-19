from MaxUsbTool import MaxUsbTool
import os

def generate_eeprom_binary_from_txt(txt_file, custom_data_json=None, output_dir="."):
    """
    Helper function to generate EEPROM binary from txt file with optional custom data.

    Args:
        txt_file: Name of the txt file in eeprom_rpi_txt folder
        custom_data_json: Optional JSON file with custom data
        output_dir: Directory to save the generated binary

    Returns:
        str: Path to generated binary file, or None on error
    """
    from eepmake import EepMake

    if txt_file is None:
        print("Error: txt_file parameter is required")
        print("Available files: eeprom_settings_ad4080.txt, eeprom_settings_a049.txt, eeprom_settings_sp77.txt")
        return None

    script_dir = os.path.dirname(os.path.abspath(__file__))
    txt_file_path = os.path.join(script_dir, "eeprom_rpi_txt", txt_file)
    
    if not os.path.exists(txt_file_path):
        print(f"Error: txt file not found at {txt_file_path}")
        print("Available files: eeprom_settings_ad4080.txt, eeprom_settings_a049.txt, eeprom_settings_sp77.txt")
        return None

    base_name = os.path.splitext(txt_file)[0]
    output_binary = os.path.join(output_dir, f"{base_name}.bin")

    print(f"Generating EEPROM binary from {txt_file}...")
    eepmake = EepMake()
    ret = eepmake.read_text(txt_file_path)
    if ret:
        print(f"Error reading and parsing {txt_file_path}")
        return None

    if custom_data_json is not None:
        json_file_path = os.path.join(script_dir, "eeprom_rpi_txt", custom_data_json)

        if not os.path.exists(json_file_path):
            print(f"Error: JSON file not found at {json_file_path}")
            return None

        print(f"Adding custom data from {custom_data_json}...")
        ret = eepmake.read_json_custom_data(json_file_path)
        if ret:
            print(f"Error reading custom data from {json_file_path}")
            return None

    ret = eepmake.write_binary(output_binary)
    if ret:
        print(f"Error writing binary to {output_binary}")
        return None

    print(f"Successfully generated EEPROM binary: {output_binary}")
    return output_binary


maxUsbTool = MaxUsbTool()

while 1:
	print('\n' + '='*80)
	print('Select operation:')
	print('  1. Read EEPROM to file')
	print('  2. Write file to EEPROM')
	print('  3. Write and verify')
	print('  4. Parse R-PI HAT+ EEPROM')
	print('  5. Compare bin files')
	print('  6. Write RPI HAT+ text to EEPROM')
	print('  q - quit')
	print('='*80)

	choice = input('Enter choice (1-6): ').strip()

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
		ret = maxUsbTool.parse_rpi_hat_eeprom_dll(0x00, eeprom_size)

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

	elif choice == '6':
		print('\nPlease provide the text file name from eeprom_rpi_txt folder:')
		print('(e.g., eeprom_settings_ad4080.txt, eeprom_settings_a049.txt, eeprom_settings_sp77.txt)')
		txt_file = input('Text file: ').strip()

		if not txt_file:
			print('\nError: text file name is required')
			continue

		print('\nDo you want to include custom data? (y/n)')
		custom_data_choice = input('> ').strip().lower()
		
		custom_data_json = None
		if custom_data_choice == 'y':
			print('\nPlease provide the custom data JSON file name from eeprom_rpi_txt folder:')
			print('(e.g., custom_data_ad4080.json, custom_data_a049.json, custom_data_sp77.json)')
			custom_data_json = input('JSON file: ').strip()
			if not custom_data_json:
				print('\nNo custom data file provided, continuing without custom data...')
				custom_data_json = None

		eeprom_file = generate_eeprom_binary_from_txt(txt_file, custom_data_json)
		
		if eeprom_file is None:
			print('\n[ERROR] Failed to generate EEPROM binary')
			continue

		print(f'\nGenerated EEPROM binary: {eeprom_file}')
		print('\n[WARNING] This will OVERWRITE your EEPROM with the generated binary')
		confirm = input('Are you sure? Type YES to confirm: ').strip()
		
		if confirm == 'YES':
			ret, bytes_written = maxUsbTool.write_eeprom_from_file(0x00, eeprom_file)
			if ret == 0:
				print(f'\n[OK] Successfully wrote {bytes_written} bytes to EEPROM')
			else:
				print('\n[ERROR] Write failed.')
		else:
			print('Write cancelled.')

	elif choice == 'q':
		break

	else:
		print('Invalid choice. Exiting.')