# RPi HAT EEPROM Parser DLL

This directory contains a C implementation of the Raspberry Pi HAT EEPROM parser that can be compiled to a DLL and used from Python.

## Folder Structure

```
pythonPLay/
├── MaxUsbTool.py                    # Original Python I2C EEPROM tool
├── example_dll_parser.py            # Example using the DLL parser package
└── rpihatparser/                    # RPi HAT Parser package
    ├── __init__.py                  # Package initialization
    ├── rpi_hat_parser.h             # C header file
    ├── rpi_hat_parser.c             # C implementation
    ├── rpi_hat_parser_wrapper.py   # Python ctypes wrapper
    ├── build_dll.bat                # Build script for Windows
    ├── test_dll_parser.py           # Internal test script
    └── README_DLL.md                # This file
```

## Files

### C Source Files
- **rpi_hat_parser.h** - Header file with structure definitions and function declarations
- **rpi_hat_parser.c** - Implementation of the parser in C
- **build_dll.bat** - Windows batch script to build the DLL

### Python Files
- **__init__.py** - Package initialization, exports public API
- **rpi_hat_parser_wrapper.py** - Python ctypes wrapper for the DLL
- **test_dll_parser.py** - Example showing integration with MaxUsbTool
- **../example_dll_parser.py** - Example in parent directory for easy usage

## Building the DLL

Navigate to the `rpihatparser` folder first:
```bash
cd rpihatparser
```

### Option 1: Using the batch script (Recommended)
```bash
build_dll.bat
```

### Option 2: Manual compilation
```bash
gcc -Wall -Wextra -O2 -std=c99 -c rpi_hat_parser.c -o rpi_hat_parser.o
gcc -shared -o rpi_hat_parser.dll rpi_hat_parser.o
```

## Requirements

- **MinGW GCC** or **MSVC** compiler for Windows
- Python 3.x with ctypes (standard library)

### Installing MinGW on Windows

1. Download MinGW from https://sourceforge.net/projects/mingw-w64/
2. Install and add the bin directory to your PATH
3. Verify installation: `gcc --version`

## Usage

### Quick Start with MaxUsbTool

From the parent directory:
```python
python example_dll_parser.py
```

### Standalone Usage (Parse a binary file)

```bash
cd rpihatparser
python rpi_hat_parser_wrapper.py ../original.bin
```

### Using as a Package

```python
from rpihatparser import parse_and_print_eeprom, parse_rpi_hat_eeprom, PARSE_OK

# Read EEPROM data (as bytes)
with open('eeprom.bin', 'rb') as f:
    eeprom_data = f.read()

# Parse and print
status = parse_and_print_eeprom(eeprom_data)
if status != PARSE_OK:
    print(f"Error parsing EEPROM")
```

# Method 2: Parse and get structured data
status, result = parser.parse_rpi_hat_eeprom(eeprom_data)
if status == parser.PARSE_OK:
    print(f"Vendor: {result.vendor_info.vendor.decode('utf-8')}")
    print(f"Product: {result.vendor_info.product.decode('utf-8')}")
    print(f"Product ID: {result.vendor_info.product_id}")
```

## API Reference

### C Functions (exported by DLL)

#### `parse_rpi_hat_eeprom`
```c
int parse_rpi_hat_eeprom(const uint8_t* eeprom_data, uint32_t data_size, ParsedEeprom* result);
```
Parses EEPROM data into a structured format.

**Version Check:** Validates that the EEPROM version field is 0x02 (RPi HAT specification).

**Returns:**
- `PARSE_OK (0)` - Success
- `PARSE_ERROR_INVALID_SIG (-1)` - Invalid signature (not "R-Pi")
- `PARSE_ERROR_INVALID_DATA (-2)` - Invalid data or NULL pointer
- `PARSE_ERROR_BUFFER_TOO_SMALL (-3)` - Buffer too small
- `PARSE_ERROR_UNSUPPORTED_VERSION (-4)` - Version is not 0x02

#### `parse_and_print_eeprom`
```c
int parse_and_print_eeprom(const uint8_t* eeprom_data, uint32_t data_size, OutputCallback callback);
```
Parses and prints EEPROM data with formatted output.

#### `get_parse_error_message`
```c
const char* get_parse_error_message(int error_code);
```
Returns a human-readable error message for an error code.

### Python Wrapper Functions

#### `parse_rpi_hat_eeprom(eeprom_data: bytes) -> tuple[int, Optional[ParsedEeprom]]`
Parses EEPROM data and returns (status_code, ParsedEeprom_object).

#### `parse_and_print_eeprom(eeprom_data: bytes, output_callback=None) -> int`
Parses and prints EEPROM data. Optional callback receives each output line.

#### `get_parse_error_message(error_code: int) -> str`
Returns error message string for an error code.

#### `print_parsed_eeprom(result: ParsedEeprom)`
Pretty-prints a ParsedEeprom structure.

## Data Structures

### ParsedEeprom
```python
class ParsedEeprom:
    header: RpiHatHeader          # Header information
    has_vendor_info: int          # 1 if vendor info present
    vendor_info: VendorInfo       # Vendor information
    has_custom_data: int          # 1 if custom data present
    custom_data: CustomData       # Custom data
    has_dt_overlay: int           # 1 if device tree overlay present
    dt_overlay_length: int        # Length of overlay data
    has_gpio_map: int             # 1 if GPIO map present
```

### VendorInfo
```python
class VendorInfo:
    uuid: bytes                   # 16-byte UUID
    product_id: int               # Product ID
    product_version: int          # Product version
    vendor: str                   # Vendor name string
    product: str                  # Product name string
```

## Performance Comparison

The C DLL parser offers several advantages:

1. **Speed**: ~10-50x faster than Python for parsing (though I2C read time dominates total time)
2. **Memory**: Lower memory footprint
3. **Reusability**: Can be used from other languages (C++, C#, etc.)
4. **Type Safety**: Compiled code with strong typing

## Advantages of DLL Approach

1. **Performance**: Faster parsing, especially for large EEPROMs or repeated parsing
2. **Code Reuse**: Same parser can be used in C/C++ applications, LabVIEW, MATLAB, etc.
3. **Distribution**: Can distribute compiled DLL without Python source
4. **Optimization**: Can be heavily optimized by compiler
5. **Embedded Integration**: Easier to integrate with embedded firmware tools

## Disadvantages of DLL Approach

1. **Complexity**: Requires C compiler and build tools
2. **Platform-Specific**: Need to compile for each platform (Windows/Linux/Mac)
3. **Maintenance**: Must maintain both C code and Python wrapper
4. **Debugging**: Harder to debug than pure Python

## When to Use Each Approach

**Use the Python parser (`MaxUsbTool.py`) when:**
- Development speed is important
- You only need Python support
- Parsing performance is not critical
- Easy debugging and modification is needed

**Use the DLL parser when:**
- Performance is critical
- You need to use the parser from multiple languages
- You're distributing a compiled tool
- You want to integrate with C/C++ applications

## Integration with MaxUsbTool

The DLL parser is designed to be a drop-in replacement for the `parse_rpi_hat_eeprom()` method:

```python
# Original Python parser
maxUsbTool.parse_rpi_hat_eeprom(0x00, 256)

# DLL parser (faster)
ret, eeprom_data = maxUsbTool.read_eeprom_to_file(0x00, 256, should_save=False)
status = parser.parse_and_print_eeprom(eeprom_data)
```

## Troubleshooting

### "DLL not found" error
- Make sure you've compiled the DLL first: `build_dll.bat`
- Check that `rpi_hat_parser.dll` is in the same directory as the Python scripts

### "gcc is not recognized" error
- Install MinGW and add it to your PATH
- Or use MSVC: `cl /LD rpi_hat_parser.c`

### Compilation errors
- Make sure you're using a C99-compatible compiler
- Check that both `.c` and `.h` files are in the same directory

## License

Same license as MaxUsbTool.py
