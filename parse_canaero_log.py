import csv
import re
import argparse
import struct

# Mapping of CAN ID to parameter name and unit
canid_info = {
    0x100: ("Airspeed", "m/s"),
    0x101: ("Altitude", "m"),
    0x102: ("Vertical_Speed", "m/s"),
    0x103: ("Pitch_Angle", "deg"),
    0x104: ("Roll_Angle", "deg"),
    0x105: ("Heading", "deg"),
    0x106: ("Latitude", "deg"),
    0x107: ("Longitude", "deg"),
    0x108: ("Ground_Speed", "m/s"),
    0x154: ("Flaps Position", "0..255"),
    0x200: ("Engine_RPM", "rpm"),
    0x201: ("Engine_Temp", "°C"),
    0x202: ("Fuel_Flow", "L/h"),
    0x203: ("Oil_Pressure", "kPa"),
    0x300: ("Command_Throttle", "%"),
    0x301: ("Command_Flaps", "deg"),
    0x302: ("Command_Gear", "bool"),
    0x400: ("Battery_Voltage", "V"),
    0x401: ("GPS_Fix", "enum"),
    0x402: ("Nav_Mode", "enum"),
    0x40C: ("GPS aircraft_lat", "deg"),
    0x40D: ("GPS aircraft_lon", "deg"),
    0x500: ("Reserved_1", "N/A"),
    0x501: ("Reserved_2", "N/A"),
}

# Mapping of data type code to (struct format, byte length, name)
DATA_TYPE_INFO = {
    0x00: ('>f', 0, 'NODATA'),      # No data (size 0)
    0x01: ('>I', 4, 'ERROR'),       # Error code
    0x02: ('>f', 4, 'FLOAT'),       # IEEE 754 single-precision floats
    0x03: ('>i', 4, 'LONG'),        # 32-bit signed integer
    0x04: ('>I', 4, 'ULONG'),       # 32-bit unsigned integer
    0x05: ('>I', 4, 'BLONG'),       # 32-bit unsigned
    0x06: ('>h', 2, 'SHORT'),       # 16-bit signed integer
    0x07: ('>H', 2, 'USHORT'),      # 16-bit unsigned integer
    0x08: ('>H', 2, 'BSHORT'),      # 16-bit unsigned
    0x09: ('>b', 1, 'CHAR'),        # 8-bit signed integer
    0x0A: ('>B', 1, 'UCHAR'),       # 8-bit unsigned integer
    0x0B: ('>B', 1, 'BCHAR'),       # 8-bit unsigned
    0x0C: ('>2h', 4, 'SHORT2'),     # Two 16-bit signed integers
    0x0D: ('>2H', 4, 'USHORT2'),    # Two 16-bit unsigned integers
    0x0E: ('>2H', 4, 'BSHORT2'),    # Two 16-bit unsigned
    0x0F: ('>4b', 4, 'CHAR4'),      # Four 8-bit signed integers
    0x10: ('>4B', 4, 'UCHAR4'),     # Four 8-bit unsigned integers
    0x11: ('>4B', 4, 'BCHAR4'),     # Typo: Should be 'BCHAR4'
    0x12: ('>2b', 2, 'CHAR2'),      # Two 8-bit signed integers
    0x13: ('>2B', 2, 'UCHAR2'),     # Two 8-bit unsigned integers
    0x14: ('>2B', 2, 'BCHAR2'),     # Two 8-bit unsigned
    0x15: ('>I', 4, 'MEMID'),       # 32-bit memory ID
    0x16: ('>I', 4, 'CHKSUM'),      # 32-bit checksum
    0x17: ('>B', 1, 'ACHAR'),       # 8-bit ASCII char
    0x18: ('>2B', 2, 'ACHAR2'),     # Two ASCII chars
    0x19: ('>4B', 4, 'ACHAR4'),     # Four ASCII chars
    0x1A: ('>3b', 3, 'CHAR3'),      # Three 8-bit signed integers
    0x1B: ('>3B', 3, 'UCHAR3'),     # Three 8-bit unsigned integers
    0x1C: ('>3B', 3, 'BCHAR3'),     # Three 8-bit unsigned
    0x1D: ('>4b', 4, 'CHAR4'),      # Duplicate of 0x0F
    0x1E: ('>d', 8, 'DOUBLEH'),     # Double-precision float
    0x1F: ('<d', 8, 'DOUBLEL'),     # Double-precision float
}
for type_id in range(0x20, 0x63):
    DATA_TYPE_INFO[type_id] = ('>x', 4, 'RESVD')
for type_id in range(0x64, 0xFF):
    DATA_TYPE_INFO[type_id] = ('>x', 4, 'UDEF')


def decode_data_by_type(raw_bytes, data_type_code, raw_mode=False):
    info = DATA_TYPE_INFO.get(data_type_code)
    if not info or raw_mode:
        return raw_bytes.hex().upper(), f'raw_0x{data_type_code:02X}'

    fmt, num_bytes, data_type = info
    data_slice = raw_bytes[:num_bytes]

    try:
        if fmt:
            unpacked = struct.unpack(fmt, data_slice)
            if len(unpacked) > 1:
                return ','.join(str(x) for x in unpacked), data_type
            else:
                return unpacked[0], data_type
        else:
            return data_slice.hex().upper(), data_type
    except Exception:
        return data_slice.hex().upper(), f'decode_error_{data_type}'

def parse_line(line, raw_mode=False):
    match = re.match(r"\(([\d.]+)\)\s+can\d+\s+([0-9A-Fa-f]+)#([0-9A-Fa-f]+)", line)
    if not match:
        return None

    timestamp = float(match.group(1))
    can_id = int(match.group(2), 16)
    raw_data_hex = match.group(3)

    raw_bytes = bytes.fromhex(raw_data_hex)
    if len(raw_bytes) < 4:
        return None  # too short for valid CANaerospace frame

    node_id = raw_bytes[0]
    data_type_code = raw_bytes[1]
    service_code = raw_bytes[2]
    message_code = raw_bytes[3]
    payload = raw_bytes[4:]

    decoded_value, data_type = decode_data_by_type(payload, data_type_code, raw_mode)

    param_name, unit = canid_info.get(can_id, ("Unknown", ""))

    return {
        "timestamp": timestamp,
        "can_id": f"0x{can_id:X}",
        "can_id descr": param_name,
        "unit": unit,
        "node_id": node_id,
        "service_code": service_code,
        "message_code": message_code,
        "data_type_code": f"0x{data_type_code:02X}",
        "data_type": data_type,
        "decoded_value": decoded_value,
        "raw_data_hex": raw_data_hex.upper()
    }

def parse_log_file(input_path, output_path, filter_can_id=None, raw_mode=False):
    fieldnames = [
        "timestamp", "can_id", "can_id descr", "unit", "node_id",
        "service_code", "message_code", "data_type_code",
        "data_type", "decoded_value", "raw_data_hex"
    ]

    with open(input_path, "r") as inf, open(output_path, "w", newline="") as outf:
        writer = csv.DictWriter(outf, fieldnames=fieldnames, quoting=csv.QUOTE_MINIMAL)
        writer.writeheader()
        for line in inf:
            parsed = parse_line(line, raw_mode=raw_mode)
            if parsed:
                if filter_can_id and f"0x{filter_can_id:X}" != parsed["can_id"]:
                    continue
                writer.writerow(parsed)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Parse CANaerospace log to CSV")
    parser.add_argument("input_file", help="Path to log file")
    parser.add_argument("output_file", help="Path to output CSV")
    parser.add_argument("--can-id", help="Optional CAN ID filter (hex)", type=lambda x: int(x, 16))
    parser.add_argument("--raw", help="Disable decoding of data payload", action="store_true")

    args = parser.parse_args()
    parse_log_file(args.input_file, args.output_file, args.can_id, args.raw)
