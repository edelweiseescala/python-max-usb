/**
 * rpi_hat_parser.h
 * 
 * Raspberry Pi HAT EEPROM Parser Library
 * Header file for DLL interface
 */

#ifndef RPI_HAT_PARSER_H
#define RPI_HAT_PARSER_H

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#define ATOM_TYPE_VENDOR_INFO  1
#define ATOM_TYPE_GPIO_MAP     2
#define ATOM_TYPE_DT_OVERLAY   3
#define ATOM_TYPE_CUSTOM       4

#define ATOM_HEADER_SIZE       8
#define FIRST_ATOM_OFFSET      12
#define MAX_STRING_LENGTH      256
#define MAX_CUSTOM_DATA_SIZE   4096
#define EXPECTED_VERSION       0x02

#define PARSE_OK                     0
#define PARSE_ERROR_INVALID_SIG      -1
#define PARSE_ERROR_INVALID_DATA     -2
#define PARSE_ERROR_BUFFER_TOO_SMALL -3
#define PARSE_ERROR_UNSUPPORTED_VERSION -4

typedef struct {
    char signature[5];
    uint8_t version;
    uint8_t reserved;
    uint16_t numatoms;
    uint32_t eeplen;
} RpiHatHeader;

typedef struct {
    uint16_t atom_type;
    uint16_t atom_count;
    uint32_t atom_dlen;
} AtomHeader;

typedef struct {
    uint8_t uuid[16];
    uint16_t product_id;
    uint16_t product_version;
    char vendor[MAX_STRING_LENGTH];
    char product[MAX_STRING_LENGTH];
} VendorInfo;

typedef struct {
    uint32_t data_length;
    uint8_t data[MAX_CUSTOM_DATA_SIZE];
    int is_json;
} CustomData;

typedef struct {
    RpiHatHeader header;
    int has_vendor_info;
    VendorInfo vendor_info;
    int has_custom_data;
    CustomData custom_data;
    int has_dt_overlay;
    char dt_overlay[MAX_STRING_LENGTH];
} ParsedEeprom;

// Callback function type for formatted output
typedef void (*OutputCallback)(const char* message);

/**
 * Parse RPi HAT EEPROM data
 * 
 * @param eeprom_data: Pointer to raw EEPROM data buffer
 * @param data_size: Size of the EEPROM data in bytes
 * @param result: Pointer to ParsedEeprom structure to store results
 * @return: PARSE_OK on success, error code on failure
 */
int parse_rpi_hat_eeprom(const uint8_t* eeprom_data, uint32_t data_size, ParsedEeprom* result);

/**
 * Parse and print RPi HAT EEPROM data with formatted output
 * 
 * @param eeprom_data: Pointer to raw EEPROM data buffer
 * @param data_size: Size of the EEPROM data in bytes
 * @param callback: Optional callback function for output (NULL to use stdout)
 * @return: PARSE_OK on success, error code on failure
 */
int parse_and_print_eeprom(const uint8_t* eeprom_data, uint32_t data_size, OutputCallback callback);

/**
 * Get a human-readable error message for a parse error code
 * 
 * @param error_code: Error code returned by parse functions
 * @return: Pointer to error message string (statically allocated)
 */
const char* get_parse_error_message(int error_code);

#ifdef __cplusplus
}
#endif

#endif // RPI_HAT_PARSER_H
