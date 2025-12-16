#include "rpi_hat_parser.h"
#include <stdio.h>
#include <string.h>
#include <stdlib.h>

static uint16_t read_le16(const uint8_t* data, uint32_t offset) {
	return data[offset] | (data[offset + 1] << 8);
}

static uint32_t read_le32(const uint8_t* data, uint32_t offset) {
	return data[offset] | 
		   (data[offset + 1] << 8) | 
		   (data[offset + 2] << 16) | 
		   (data[offset + 3] << 24);
}

static void safe_string_copy(char* dest, const uint8_t* src, uint32_t length, uint32_t max_length) {
	uint32_t copy_len = (length < max_length - 1) ? length : max_length - 1;
	memcpy(dest, src, copy_len);
	dest[copy_len] = '\0';
}

int parse_rpi_hat_eeprom(const uint8_t* eeprom_data, uint32_t data_size, ParsedEeprom* result) {
	if (eeprom_data == NULL || result == NULL || data_size < 12) {
		return PARSE_ERROR_INVALID_DATA;
	}

	memset(result, 0, sizeof(ParsedEeprom));

	if (memcmp(eeprom_data, "R-Pi", 4) != 0) {
		return PARSE_ERROR_INVALID_SIG;
	}

	memcpy(result->header.signature, eeprom_data, 4);
	result->header.signature[4] = '\0';
	result->header.version = eeprom_data[4];
	if (result->header.version != EXPECTED_VERSION)
		return PARSE_ERROR_UNSUPPORTED_VERSION;

	result->header.reserved = eeprom_data[5];
	result->header.numatoms = read_le16(eeprom_data, 6);
	result->header.eeplen = read_le32(eeprom_data, 8);

	if (result->header.eeplen > data_size)
		return PARSE_ERROR_BUFFER_TOO_SMALL;

	uint32_t curr_address = FIRST_ATOM_OFFSET;

	for (uint16_t atom_num = 0; atom_num < result->header.numatoms; atom_num++) {
		if (curr_address + ATOM_HEADER_SIZE > data_size) {
			break;
		}

		AtomHeader atom_header;
		atom_header.atom_type = read_le16(eeprom_data, curr_address);
		atom_header.atom_count = read_le16(eeprom_data, curr_address + 2);
		atom_header.atom_dlen = read_le32(eeprom_data, curr_address + 4);

		uint32_t data_start = curr_address + ATOM_HEADER_SIZE;

		if (data_start + atom_header.atom_dlen > data_size) {
			break;
		}

		switch (atom_header.atom_type) {
			case ATOM_TYPE_VENDOR_INFO: {
				memcpy(result->vendor_info.uuid, &eeprom_data[data_start], 16);

				result->vendor_info.product_id = read_le16(eeprom_data, data_start + 16);
				result->vendor_info.product_version = read_le16(eeprom_data, data_start + 18);

				uint8_t vendor_len = eeprom_data[data_start + 20];
				uint8_t product_len = eeprom_data[data_start + 21];

				uint32_t vendor_start = data_start + 22;
				safe_string_copy(result->vendor_info.vendor, 
							   &eeprom_data[vendor_start], 
							   vendor_len, 
							   MAX_STRING_LENGTH);

				uint32_t product_start = vendor_start + vendor_len;
				safe_string_copy(result->vendor_info.product, 
							   &eeprom_data[product_start], 
							   product_len, 
							   MAX_STRING_LENGTH);
				
				result->has_vendor_info = 1;
				break;
			}

			case ATOM_TYPE_CUSTOM: {
				if (strcmp(result->vendor_info.vendor, "Analog Devices Inc.") == 0)
					break;

				result->has_custom_data = 1;
				uint32_t custom_data_len = atom_header.atom_dlen - 2;

				if (custom_data_len > MAX_CUSTOM_DATA_SIZE) {
					custom_data_len = MAX_CUSTOM_DATA_SIZE;
				}

				result->custom_data.data_length = custom_data_len;
				memcpy(result->custom_data.data, &eeprom_data[data_start], custom_data_len);

				result->custom_data.is_json = (custom_data_len > 0 && 
											 (result->custom_data.data[0] == '{' || 
											  result->custom_data.data[0] == '['));
				break;
			}

			case ATOM_TYPE_DT_OVERLAY: {
				result->has_dt_overlay = 1;
				uint32_t overlay_len = atom_header.atom_dlen - 2;

				safe_string_copy(result->dt_overlay, 
							   &eeprom_data[data_start], 
							   overlay_len, 
							   MAX_STRING_LENGTH);
				break;
			}

			default:
				break;
		}

		curr_address += ATOM_HEADER_SIZE + atom_header.atom_dlen;
	}

	return PARSE_OK;
}

int parse_and_print_eeprom(const uint8_t* eeprom_data, uint32_t data_size, OutputCallback callback) {
	ParsedEeprom result;
	int ret = parse_rpi_hat_eeprom(eeprom_data, data_size, &result);

	if (ret != PARSE_OK) {
		const char* error_msg = get_parse_error_message(ret);
		if (callback) {
			callback(error_msg);
		} else {
			printf("%s\n", error_msg);
		}
		return ret;
	}

	char buffer[1024];

	snprintf(buffer, sizeof(buffer), "EEPROM Signature: %s", result.header.signature);
	if (callback) callback(buffer); else printf("%s\n", buffer);

	snprintf(buffer, sizeof(buffer), "Valid Raspberry Pi HAT EEPROM detected!");
	if (callback) callback(buffer); else printf("%s\n", buffer);

	snprintf(buffer, sizeof(buffer), "\nHeader Info:");
	if (callback) callback(buffer); else printf("%s\n", buffer);

	snprintf(buffer, sizeof(buffer), "  Signature: %s", result.header.signature);
	if (callback) callback(buffer); else printf("%s\n", buffer);

	snprintf(buffer, sizeof(buffer), "  Version: 0x%02x", result.header.version);
	if (callback) callback(buffer); else printf("%s\n", buffer);

	snprintf(buffer, sizeof(buffer), "  Number of Atoms: %u", result.header.numatoms);
	if (callback) callback(buffer); else printf("%s\n", buffer);

	snprintf(buffer, sizeof(buffer), "  EEPROM Length: %u bytes", result.header.eeplen);
	if (callback) callback(buffer); else printf("%s\n", buffer);

	if (result.has_vendor_info) {
		snprintf(buffer, sizeof(buffer), "\nVendor Information:");
		if (callback) callback(buffer); else printf("%s\n", buffer);

		snprintf(buffer, sizeof(buffer), "  Product ID: %u", result.vendor_info.product_id);
		if (callback) callback(buffer); else printf("%s\n", buffer);

		snprintf(buffer, sizeof(buffer), "  Product Version: %u", result.vendor_info.product_version);
		if (callback) callback(buffer); else printf("%s\n", buffer);

		snprintf(buffer, sizeof(buffer), "  Vendor: %s", result.vendor_info.vendor);
		if (callback) callback(buffer); else printf("%s\n", buffer);

		snprintf(buffer, sizeof(buffer), "  Board: %s", result.vendor_info.product);
		if (callback) callback(buffer); else printf("%s\n", buffer);
	}

	if (result.has_custom_data) {
		snprintf(buffer, sizeof(buffer), "\nCustom Data (%u bytes):", result.custom_data.data_length);
		if (callback) callback(buffer); else printf("%s\n", buffer);

		if (result.custom_data.is_json) {
			char* json_str = (char*)malloc(result.custom_data.data_length + 1);
			if (json_str) {
				memcpy(json_str, result.custom_data.data, result.custom_data.data_length);
				json_str[result.custom_data.data_length] = '\0';
				
				int len = result.custom_data.data_length;
				while (len > 0 && json_str[len - 1] == '\0') {
					len--;
				}
				json_str[len] = '\0';
				
				snprintf(buffer, sizeof(buffer), "  JSON: %s", json_str);
				if (callback) callback(buffer); else printf("%s\n", buffer);
				
				free(json_str);
			}
		} else {
			snprintf(buffer, sizeof(buffer), "  Hex data (first 64 bytes):");
			if (callback) callback(buffer); else printf("%s\n", buffer);

			uint32_t print_len = (result.custom_data.data_length < 64) ? 
								 result.custom_data.data_length : 64;
			
			for (uint32_t i = 0; i < print_len; i += 16) {
				char hex_line[256] = "    ";
				char* ptr = hex_line + 4;
				
				for (uint32_t j = 0; j < 16 && (i + j) < print_len; j++) {
					ptr += snprintf(ptr, 256 - (ptr - hex_line), "%02x ", 
								  result.custom_data.data[i + j]);
				}
				
				if (callback) callback(hex_line); else printf("%s\n", hex_line);
			}
		}
	}

	if (result.has_dt_overlay) {
		snprintf(buffer, sizeof(buffer), "  Overlay: %s", result.dt_overlay);
		if (callback) callback(buffer); else printf("%s\n", buffer);
	}

	return PARSE_OK;
}

const char* get_parse_error_message(int error_code) {
	switch (error_code) {
		case PARSE_OK:
			return "Success";
		case PARSE_ERROR_INVALID_SIG:
			return "Error: Invalid signature (not a valid RPi HAT EEPROM)";
		case PARSE_ERROR_INVALID_DATA:
			return "Error: Invalid data or NULL pointer";
		case PARSE_ERROR_BUFFER_TOO_SMALL:
			return "Error: Buffer too small for specified EEPROM length";
		case PARSE_ERROR_UNSUPPORTED_VERSION:
			return "Error: Unsupported version (expected 0x02)";
		default:
			return "Error: Unknown error code";
	}
}
