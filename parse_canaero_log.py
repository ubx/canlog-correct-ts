import argparse
import csv
import re
import struct
from datetime import datetime, timezone
from typing import Dict, Tuple, Union, Optional, Any, List, Set

# Pre-compile regex for better performance
CAN_LINE_PATTERN = re.compile(r"\(([\d.]+)\)\s+can\d+\s+([0-9A-Fa-f]+)#([0-9A-Fa-f]+)")

# Mapping of CAN ID to parameter name and unit
CANID_INFO = {
    # --- Flight Dynamics (0x12C-0x15C) ---
    0x12C: ("Body Longitudinal Acceleration", "m/s²"),
    0x12D: ("Body Lateral Acceleration", "m/s²"),
    0x12E: ("Body Normal Acceleration", "m/s²"),
    0x12F: ("Body Pitch Rate", "deg/s"),
    0x130: ("Body Roll Rate", "deg/s"),
    0x131: ("Body Yaw Rate", "deg/s"),
    0x132: ("Rudder Position", "deg"),
    0x133: ("Stabilizer Position", "deg"),
    0x134: ("Elevator Position", "deg"),
    0x135: ("Left Aileron Position", "deg"),
    0x136: ("Right Aileron Position", "deg"),
    0x137: ("Body Pitch Angle", "deg"),
    0x138: ("Body Roll Angle", "deg"),
    0x139: ("Body Sideslip", "deg"),
    0x13A: ("Altitude Rate", "m/s"),
    0x13B: ("Indicated Airspeed", "m/s"),
    0x13C: ("True Airspeed", "m/s"),
    0x13D: ("Calibrated Airspeed", "m/s"),
    0x13E: ("Mach Number", "Mach"),
    0x13F: ("Baro Correction", "hPa"),
    0x140: ("Baro Corrected Altitude", "m"),
    0x141: ("Heading Angle", "deg"),
    0x142: ("Standard Altitude", "m"),
    0x143: ("Total Air Temperature", "K"),
    0x144: ("Static Air Temperature", "K"),
    0x145: ("Differential Pressure", "hPa"),
    0x146: ("Static Pressure", "hPa"),
    0x147: ("Heading Rate", "deg/s"),
    0x148: ("Port Side Angle Of Attack", "deg"),
    0x149: ("Starbord Side Angle Of Attack", "deg"),
    0x14A: ("Density Altitude", "m"),
    0x14B: ("Turn Coordination Rate", "deg/s"),
    0x14C: ("True Altitude", "m"),
    0x14D: ("Wind Speed", "m/s"),
    0x14E: ("Wind Direction", "deg"),
    0x14F: ("Outside Air Temperature", "K"),
    0x150: ("Body Normal Velocity", "m/s"),
    0x151: ("Body Longitudinal Velocity", "m/s"),
    0x152: ("Body Lateral Velocity", "m/s"),
    0x153: ("Total Pressure", "hPa"),
    0x154: ("Flaps position", "deg"),
    0x156: ("Speed brake position", "deg"),
    0x159: ("Vertical speed of the airmass", "m/s"),
    0x15C: ("TEK altitude rate", "m/s"),

    # --- Flight Controls (0x190-0x1BA) ---
    0x190: ("Pitch Control Position", "deg"),
    0x191: ("Roll Control Position", "deg"),
    0x192: ("Lateral Stick Trim Position Command", "deg"),
    0x193: ("Yaw Control Position", "deg"),
    0x194: ("Collective Control Position", "deg"),
    0x195: ("Longitudinal Stick Trim Position Command", "deg"),
    0x196: ("Directional Pedals Trim Position Command", "deg"),
    0x197: ("Collective Lever Trim Position Command", "deg"),
    0x198: ("Cyclic Control Stick Switches", "enum"),
    0x199: ("Lateral Trim Speed", "deg/s"),
    0x19A: ("Longitudinal Trim Speed", "deg/s"),
    0x19B: ("Pedal Trim Speed", "deg/s"),
    0x19C: ("Collective Trim Speed", "deg/s"),
    0x19D: ("Nose Wheel Steering Handle Position", "deg"),
    0x19E: ("Engine 1 Throttle Lever Position Ecs Channel A", "%"),
    0x19F: ("Engine 2 Throttle Lever Position Ecs Channel A", "%"),
    0x1AE: ("Flaps Lever Position", "deg"),
    0x1AF: ("Slats Lever Position", "deg"),
    0x1B0: ("Park Brake Lever Position", "enum"),
    0x1B1: ("Speedbrake Lever Position", "deg"),
    0x1B2: ("Throttle Max Lever Position", "%"),
    0x1B3: ("Pilot Left Brake Pedal Position", "%"),
    0x1B4: ("Pilot Right Brake Pedal Position", "%"),
    0x1B5: ("Copilot Left Brake Pedal Position", "%"),
    0x1B6: ("Copilot Right Brake Pedal Position", "%"),
    0x1B7: ("Trim System Switches", "enum"),
    0x1B8: ("Trim System Lights", "enum"),
    0x1B9: ("Collective Control Stick Switches", "enum"),
    0x1BA: ("Stick Shaker Stall Warning Device", "enum"),

    # --- Propulsion/Engine (0x1F4-0x2BB) ---
    0x1F4: ("Engine 1 N1 Ecs Channel A", "%"),
    0x1F5: ("Engine 2 N1 Ecs Channel A", "%"),
    0x294: ("Fuel Pump 1 Flow Rate", "L/h"),
    0x295: ("Fuel Pump 2 Flow Rate", "L/h"),

    # --- Navigation/GPS (0x3E8-0x44F) ---
    0x3E8: ("Active Nav System Waypoint Latitude", "deg"),
    0x3E9: ("Active Nav System Waypoint Longitude", "deg"),
    0x3EA: ("Active Nav System Waypoint Height Above Ellipsoid", "m"),
    0x3EB: ("Active Nav System Waypoint Altitude", "m"),
    0x3EC: ("Active Nav System Ground Speed", "m/s"),
    0x3ED: ("Active Nav System True Track", "deg"),
    0x3EE: ("Active Nav System Magnetic Track", "deg"),
    0x3EF: ("Active Nav System Cross Track Error", "m"),
    0x3F0: ("Active Nav System Track Error Angle", "deg"),
    0x3F1: ("Active Nav System Time To Go", "s"),
    0x3F2: ("Active Nav System Estimated Time Of Arrival", "timestamp"),
    0x3F3: ("Active Nav System Estimated Enroute Time", "s"),
    0x3F4: ("Gps Aircraft Latitude", "deg"),
    0x3F5: ("Gps Aircraft Longitude", "deg"),
    0x3F6: ("Gps Aircraft Height Above Ellipsoid", "m"),
    0x3F7: ("Gps Ground Speed", "m/s"),
    0x3F8: ("Gps True Track", "deg"),
    0x3F9: ("Gps Magnetic Track", "deg"),
    0x3FA: ("Gps Cross Track Error", "m"),
    0x3FB: ("Gps Track Error Angle", "deg"),
    0x3FC: ("Gps Glideslope Deviation", "deg"),
    0x3FD: ("Gps Predicted Raim", "enum"),
    0x3FE: ("Gps Vertical Figure Of Merit", "m"),
    0x3FF: ("Gps Horizontal Figure Of Merit", "m"),
    0x400: ("Gps Mode Of Operation", "enum"),

    # --- Electrical/Hydraulic (0x320-0x3CF) ---
    0x320: ("Hydraulic System 1 Pressure", "kPa"),
    0x321: ("Hydraulic System 2 Pressure", "kPa"),

    # --- Time/Miscellaneous (0x4B0-0x4B6) ---
    0x4B0: ("Utc", "timestamp"),
    0x4B1: ("Cabin Pressure", "hPa"),
    0x4B2: ("Cabin Altitude", "m"),
    0x4B3: ("Cabin Temperature", "°C"),
    0x4B4: ("Longitudinal Center Of Gravity", "m"),
    0x4B5: ("Lateral Center Of Gravity", "m"),
    0x4B6: ("Date", "date")
}

# Mapping of data type code to (struct format, byte length, name)
DATA_TYPE_INFO = {
    0x00: (None, 0, 'NODATA'),  # No data (size 0)
    0x01: ('>I', 4, 'ERROR'),  # Error code
    0x02: ('>f', 4, 'FLOAT'),  # IEEE 754 single-precision floats
    0x03: ('>i', 4, 'LONG'),  # 32-bit signed integer
    0x04: ('>I', 4, 'ULONG'),  # 32-bit unsigned integer
    0x05: ('>I', 4, 'BLONG'),  # 32-bit unsigned
    0x06: ('>h', 2, 'SHORT'),  # 16-bit signed integer
    0x07: ('>H', 2, 'USHORT'),  # 16-bit unsigned integer
    0x08: ('>H', 2, 'BSHORT'),  # 16-bit unsigned
    0x09: ('>b', 1, 'CHAR'),  # 8-bit signed integer
    0x0A: ('>B', 1, 'UCHAR'),  # 8-bit unsigned integer
    0x0B: ('>B', 1, 'BCHAR'),  # 8-bit unsigned
    0x0C: ('>2h', 4, 'SHORT2'),  # Two 16-bit signed integers
    0x0D: ('>2H', 4, 'USHORT2'),  # Two 16-bit unsigned integers
    0x0E: ('>2H', 4, 'BSHORT2'),  # Two 16-bit unsigned
    0x0F: ('>4b', 4, 'CHAR4'),  # Four 8-bit signed integers
    0x10: ('>4B', 4, 'UCHAR4'),  # Four 8-bit unsigned integers
    0x11: ('>4B', 4, 'BCHAR4'),  # Typo: Should be 'BCHAR4'
    0x12: ('>2b', 2, 'CHAR2'),  # Two 8-bit signed integers
    0x13: ('>2B', 2, 'UCHAR2'),  # Two 8-bit unsigned integers
    0x14: ('>2B', 2, 'BCHAR2'),  # Two 8-bit unsigned
    0x15: ('>I', 4, 'MEMID'),  # 32-bit memory ID
    0x16: ('>I', 4, 'CHKSUM'),  # 32-bit checksum
    0x17: ('>B', 1, 'ACHAR'),  # 8-bit ASCII char
    0x18: ('>2B', 2, 'ACHAR2'),  # Two ASCII chars
    0x19: ('>4B', 4, 'ACHAR4'),  # Four ASCII chars
    0x1A: ('>3b', 3, 'CHAR3'),  # Three 8-bit signed integers
    0x1B: ('>3B', 3, 'UCHAR3'),  # Three 8-bit unsigned integers
    0x1C: ('>3B', 3, 'BCHAR3'),  # Three 8-bit unsigned
    0x1D: ('>4b', 4, 'CHAR4'),  # Duplicate of 0x0F
    0x1E: ('>d', 8, 'DOUBLEH'),  # Double-precision float
    0x1F: ('<d', 8, 'DOUBLEL'),  # Double-precision float
}

# Fill reserved and undefined ranges
DATA_TYPE_INFO.update({type_id: ('>x', 4, 'RESVD') for type_id in range(0x20, 0x63)})
DATA_TYPE_INFO.update({type_id: ('>x', 4, 'UDEF') for type_id in range(0x64, 0xFF)})


def decode_data_by_type(raw_bytes: bytes, data_type_code: int, raw_mode: bool = False) -> Tuple[
    Union[str, float, int], str]:
    """Decode raw bytes according to data type code."""
    if raw_mode:
        return raw_bytes.hex().upper(), f'raw_0x{data_type_code:02X}'

    info = DATA_TYPE_INFO.get(data_type_code)
    if not info:
        return raw_bytes.hex().upper(), f'unknown_0x{data_type_code:02X}'

    fmt, num_bytes, data_type = info
    data_slice = raw_bytes[:num_bytes]

    try:
        if not fmt:
            return data_slice.hex().upper(), data_type

        unpacked = struct.unpack(fmt, data_slice)
        if len(unpacked) > 1:
            return ','.join(map(str, unpacked)), data_type
        return unpacked[0], data_type
    except Exception:
        return data_slice.hex().upper(), f'decode_error_{data_type}'


def parse_line(line: str, raw_mode: bool = False) -> Optional[Dict[str, Any]]:
    """Parse a single line of CAN log data."""
    match = CAN_LINE_PATTERN.match(line)
    if not match:
        return None

    timestamp = float(match.group(1))
    time_str = datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat(timespec='milliseconds')
    can_id = int(match.group(2), 16)
    raw_data_hex = match.group(3).upper()

    try:
        raw_bytes = bytes.fromhex(raw_data_hex)
    except ValueError:
        return None

    if len(raw_bytes) < 4:
        return None  # Invalid CANaerospace frame

    node_id = raw_bytes[0]
    data_type_code = raw_bytes[1]
    service_code = raw_bytes[2]
    message_code = raw_bytes[3]
    payload = raw_bytes[4:]

    decoded_value, data_type = decode_data_by_type(payload, data_type_code, raw_mode)
    param_name, unit = CANID_INFO.get(can_id, ("Unknown", ""))

    return {
        "timestamp": time_str,
        "can_id": f"0x{can_id:X} ({can_id:d})",
        "can_id descr": param_name,
        "unit": unit,
        "node_id": node_id,
        "service_code": service_code,
        "message_code": message_code,
        "data_type_code": f"0x{data_type_code:02X}",
        "data_type": data_type,
        "decoded_value": decoded_value,
        "raw_data_hex": raw_data_hex
    }


def parse_log_file(
        input_path: str,
        output_path: str,
        filter_can_ids: Optional[List[int]] = None,
        raw_mode: bool = False
) -> None:
    """Parse CAN log file and write results to CSV."""
    fieldnames = [
        "timestamp", "can_id", "can_id descr", "unit", "node_id",
        "service_code", "message_code", "data_type_code",
        "data_type", "decoded_value", "raw_data_hex"
    ]

    with open(input_path, "r") as infile, open(output_path, "w", newline="") as outfile:
        writer = csv.DictWriter(outfile, fieldnames=fieldnames, quoting=csv.QUOTE_MINIMAL)
        writer.writeheader()

        # Create set of filter strings for faster lookup
        filter_set = {f"0x{can_id:X}" for can_id in filter_can_ids} if filter_can_ids else None

        for line in infile:
            parsed = parse_line(line, raw_mode)
            if parsed:
                if filter_set is None or parsed["can_id"].split()[0] in filter_set:
                    writer.writerow(parsed)


def hex_int(value: str) -> int:
    """Convert hex string to integer."""
    return int(value, 16)


def main() -> None:
    parser = argparse.ArgumentParser(description="Parse CANaerospace log to CSV")
    parser.add_argument("input_file", help="Path to log file")
    parser.add_argument("output_file", help="Path to output CSV")
    parser.add_argument(
        "--can-id",
        help="CAN IDs to filter (hex), e.g. --can-id 0x154 0x150 0x234",
        type=hex_int,
        nargs='+',  # Accept one or more arguments
        default=None
    )
    parser.add_argument("--raw", help="Disable decoding of data payload", action="store_true")

    args = parser.parse_args()
    parse_log_file(args.input_file, args.output_file, args.can_id, args.raw)


if __name__ == "__main__":
    main()