import struct
from calendar import month
from datetime import datetime
from operator import index
from time import monotonic_ns
from tkinter.font import names
import hashlib
import hmac
import base64
from datetime import datetime
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad


# Mapping between names and numeric codes for type encoding
TYPE_MAP = {
    "get-request": 0,
    "set-request": 1,
    "notification": 2,
    "response": 3
}

ERROR_CODES = {
    0: "no errors",
    1: "message decoding error",
    2: "Tag error",
    3: "unknown message type",
    4: "duplicate message",
    5: "invalid or unknown IID",
    6: "unknown value type",
    7: "unsupported value",
    8: "value list does not match IID list"
}

def encode_timestamp_type0(timestamp_str):
    """
    TimeStamp encoding, return impossivel values if the input is invalid
    """
    try:
        parts = timestamp_str.split(':')
        if len(parts) != 7:
            return struct.pack('<3H', 0, 0, 0xFFFF)  # ERROR CODE

        day, month, year, hour, minute, second, ms = map(int, timestamp_str.split(':'))

        if not (1 <= day <= 31) or not (1 <= month <= 12) or not (2000 <= year <= 2127):
            return struct.pack('<3H', 0, 0, 0xFFFF)  # ERROR CODE

        if not (0 <= hour <= 23) or not (0 <= minute <= 59) or not (0 <= second <= 59) or not (0 <= ms <= 999):
            return struct.pack('<3H', 0, 0, 0xFFFF)  # ERROR CODE
        if month in [4, 6, 9, 11] and day > 30:
            return struct.pack('<3H', 0, 0, 0xFFFF)  # ERROR CODE
        if month == 2 and day > 29:
            return struct.pack('<3H', 0, 0, 0xFFFF)  # ERROR CODE
        # 1. seconds + milliseconds
        secs_ms = second * 1000 + ms

        # 2. hours + minutes
        hours_mins = hour * 60 + minute

        # 3. data: (year-2000)*2^B + month*2⁴ + day
        data = (year - 2000) * 512 + month * 32 + day

        # 4. Pack como 3 valores de 16 bits
        return struct.pack('3H', secs_ms, hours_mins, data)

    except (ValueError, IndexError, TypeError):
        return struct.pack('<3H', 0, 0, 0xFFFF)  # ERROR CODE

def decode_timestamp_type0(data):
    secs_ms, hours_mins, date = struct.unpack('3H', data)

    # 1. seconds + milliseconds
    second = secs_ms // 1000
    ms = secs_ms % 1000

    # 2. hours + minutes
    hour = hours_mins // 60
    minute = hours_mins % 60

    # 3. date
    year = (date >> 9) + 2000
    month = (date >> 5) & 0xF
    day = date & 0x1F

    return f"{day}:{month}:{year}:{hour}:{minute}:{second}:{ms}"


def encode_timestamp_type1(timestamp_str):
    """
    Encode: Timestamp Type 1 with proper error handling
    """
    try:
        # 1. Validação básica do formato
        parts = timestamp_str.split(':')
        if len(parts) != 5:
            return struct.pack('<3H', 0, 0, 0xFFFF)  # ⚠️ ERROR CODE

        # 2. Conversão para inteiros
        days, hours, minutes, seconds, ms = map(int, parts)

        # 3. Validação de ranges
        if not (0 <= days <= 65535):  # Dias: 0-65535 (16 bits)
            return struct.pack('<3H', 0, 0, 0xFFFF)  # ⚠️ ERROR CODE

        if not (0 <= hours <= 23):  # Horas: 0-23
            return struct.pack('<3H', 0, 0, 0xFFFF)  # ⚠️ ERROR CODE

        if not (0 <= minutes <= 59):  # Minutos: 0-59
            return struct.pack('<3H', 0, 0, 0xFFFF)  # ⚠️ ERROR CODE

        if not (0 <= seconds <= 59):  # Segundos: 0-59
            return struct.pack('<3H', 0, 0, 0xFFFF)  # ⚠️ ERROR CODE

        if not (0 <= ms <= 999):  # Milissegundos: 0-999
            return struct.pack('<3H', 0, 0, 0xFFFF)  # ⚠️ ERROR CODE

        # 4. Encoding normal (o teu código original)
        secs_ms = seconds * 1000 + ms
        hours_mins = hours * 60 + minutes

        return struct.pack('<3H', secs_ms, hours_mins, days)

    except (ValueError, IndexError, TypeError):
        # Qualquer exceção → error code
        return struct.pack('<3H', 0, 0, 0xFFFF)  # ⚠️ ERROR CODE

def decode_timestamp_type1(data):
    """
    Decode: Timestamp type 1
    """
    secs_ms, hours_mins, days = struct.unpack('<3H', data)

    secs = secs_ms // 1000
    ms = secs_ms % 1000

    hours = hours_mins // 60
    mins = hours_mins % 60

    return f"{days}:{hours}:{mins}:{secs}:{ms}"

def encode_tag():
    """
    Encode protocol tag - SEMPRE o mesmo valor!
    Spec página 4: "fixed and predefined value, the same for all PDUs"
    """
    return b'LSNMPv2\x00'

def decode_tag(tag_bytes):
    """
    Decode and validate protocol tag
    """
    expected = b'LSNMPv2\x00'
    if tag_bytes != expected:
        raise ValueError(f"Invalid protocol tag. Expected {expected}, got {tag_bytes}")
    return "LSNMPv2"  # Devolve string para debugging

def encode_type(type):
    """
    Encodes type
    """
    try:
        if type not in TYPE_MAP:
            return struct.pack('B', 4)

        value = TYPE_MAP[type]
        return struct.pack('B', value)
    except:
        return struct.pack('B', 4)

def decode_type(type_bytes):
    """
    Decodes type
    """
    try:
        if isinstance(type_bytes, bytes):
            value = struct.unpack('B', type_bytes)[0]
        elif isinstance(type_bytes, int):
            value = type_bytes
        else:
            return "Erro"

        for name, code in TYPE_MAP.items():
            if code == value:
                return name
    except:
        return "Erro"



def encode_MSGID(msgId):
    """
    Encodes MSG-ID
    """
    try:
        return struct.pack('>Q', msgId)
    except Exception:
        # Return 8 zero bytes (value = 0)
        return struct.pack('>Q', 0)

def decode_MSGID(msgId_bytes):
    """
    Decodes MSG-ID
    """
    try:
        return struct.unpack('>Q', msgId_bytes)[0]
    except Exception:
        return 0

def encode_single_iid( iid_str):
    """
    Encode a single IID
    """
    parts = iid_str.split('.')

    # Validation parts
    if not (2 <= len(parts) <= 4):
        raise ValueError(f"IDD must have 2-4 parts: {iid_str}")

    try:
        parts = list(map(int, parts))
    except ValueError:
        raise ValueError(f"IID must contain only integers: {iid_str}")

    # Validation ranges
    structure, object_id = parts[0], parts[1]
    if not (1 <= structure <= 255 ):
        raise ValueError(f"Structure must be 1-255: {structure}")
    if not (1 <= object_id <= 255):
        raise ValueError(f"Object must be 1-255: {object_id}")

    # Encoding
    if len(parts) == 2:
        data_type = 0b01000000
        return struct.pack('>BBB', data_type, structure, object_id)

    elif len(parts) == 3:
        index1 = parts[2]
        if not (0 <= index1 <= 65535):
            raise ValueError(f"Index1 must be 0-65535: {index1}")
        data_type = 0b01000001
        return struct.pack('>BBBH', data_type, structure, object_id, index1)

    else:
        index1, index2 = parts[2], parts[3]
        if not (0 <= index1 <= 65535) or not (0 <= index2 <= 65535):
            raise ValueError(f"Indexes must be 0-65535: {index1}, {index2}")
        if index2 < index1:
            raise ValueError(f"Index2 must be >= Index1: {index1}, {index2} ")
        data_type = 0b01000011
        return struct.pack('>BBBHH', data_type, structure, object_id, index1, index2)

def encode_iid_list(iid_list, strict=True):
    """
    Encode IID list
    """
    if not iid_list:
        return struct.pack('>B', 0)

    encoded_iids = []
    errors = []
    for i, iid in enumerate(iid_list):
        try:
            encoded = encode_single_iid(iid)
            encoded_iids.append(encoded)
        except ValueError as e:
            if strict:
                raise
            errors.append((i, iid, str(e)))
            continue

        if errors and strict:
            raise ValueError(f"Invalid IIDs found: {errors}")

    # ⬇️⬇️⬇️ FORA DO LOOP - EXECUTA DEPOIS DE PROCESSAR TODOS OS IIDs!
    if not encoded_iids:
        return struct.pack('>B', 0)

    # ⬇️⬇️⬇️ FORA DO LOOP - EXECUTA DEPOIS DE PROCESSAR TODOS OS IIDs!
    return struct.pack('>B', len(encoded_iids)) + b''.join(encoded_iids)

def decode_single_iid(data):
    """
    DECODE single IID
    """
    if len(data) < 1:
        raise ValueError("Data too short for IID")

    data_type = data[0]

    # check DataType to format
    if data_type == 0b01000000:  # 2-part IID
        if len(data) < 3:
            raise ValueError(f"Need 3 bytes for 2-part IID, got {len(data)}")
        structure, object_id = struct.unpack('>BB', data[1:3])
        return f"{structure}.{object_id}", data[3:]
    elif data_type == 0b01000001:
        if len(data) < 5:
            raise ValueError("Not enough data for 3-part IID")
        structure, object_id, index1 = struct.unpack('>BBH', data[1:5])
        return f"{structure}.{object_id}.{index1}", data[5:]
    elif data_type == 0b01000011:
        if len(data) < 7:
            raise ValueError("Not enough data for 4-part IID")
        structure, object_id, index1, index2 = struct.unpack('>BBHH', data[1:7])
        return f"{structure}.{object_id}.{index1}.{index2}", data[7:]
    else:
        raise ValueError(f"Unknow IID data type: {data_type:08b}")

def decode_iid_list(data):
    """
    DECODE IID list
    """
    if not data or len(data) == 0:
        return [], data

    try:
        num_elements = struct.unpack('>B', data[:1])[0]
    except:
        raise ValueError("Invalid IID list header")

    remaining_data = data[1:]
    decoded_iids = []

    for i in range(num_elements):
        try:
            iid_str, remaining_data = decode_single_iid(remaining_data)
            decoded_iids.append(iid_str)
        except ValueError as e:
            # SKIP ID OR RAISE ERROR???, TO DECIDE LATER !!!!!!!
            print(f"⚠️ Skipping corrupted IID {i + 1}/{num_elements}: {e}")
            continue

    return decoded_iids, remaining_data

def encode_value(value_data, value_type=None):
    """
    Encode a single value
    """
    try:
        #Auto-detect type if not provided
        if value_type is None:
            if isinstance(value_data, int):
                if value_data < -128 or value_data > 255:
                    value_type = "integer"
                value_type = "integer"
            elif isinstance(value_data, str):
                if ":" in str(value_data):
                    value_type = "timestamp"
                else:
                    value_type = "string"
            elif isinstance(value_data, bytes):
                value_type = "byte"
            elif isinstance(value_data, list):
                if not value_data:
                    raise ValueError("Empty list cannot be auto-detected")

                if all(isinstance(x, int) for x in value_data):
                    value_type = "integer"

                elif all(isinstance(x, str) and x.isdigit() for x in value_data):
                    value_data = [int(x) for x in value_data]
                    value_type = "integer"

                elif all(isinstance(x, bytes) for x in value_data):
                    value_data = b''.join(value_data)
                    value_type = "bytes"

                else:
                    raise ValueError(f"Cannot auto-detect type for list: {value_data}. Mixed types or unsopported elemtes")
            else:
                raise ValueError(f"Cannot auto-detect type for: {value_data}")


        # Byte types
        if value_type == "byte":
            if isinstance(value_data, int):
                if 0 <= value_data <= 255:
                    return struct.pack('>B', 0b00000000) + struct.pack('>B', value_data)
                else:
                    raise ValueError(f"Byte value out of range: {value_data}. Must be 0-255")
            elif isinstance(value_data, bytes):
                if len(value_data) <= 255:
                    return struct.pack('>BB', 0b00000001, len(value_data)) + value_data
                elif len(value_data) <= 65535:
                    return struct.pack('>BH', 0b00000010, len(value_data)) + value_data
                else:
                    raise ValueError(f"Byte sequence too long: {len(value_data)}")

        #INTEGER types
        elif value_type == "integer":
            if isinstance(value_data, int):
                if -128 <= value_data <= 127:
                    return struct.pack('>Bb', 0b00000100, value_data)
                elif -32768 <= value_data <= 32767:
                    return struct.pack('>Bh', 0b00000101, value_data)
                elif -2147483648 <= value_data <= 2147483647:
                    return struct.pack('>Bi', 0b00000110, value_data)
                else:
                    return struct.pack('>Bq', 0b00000111, value_data)
            elif isinstance(value_data, list):
                if not value_data:
                    raise ValueError("Empty integer sequence")

                #Check all elements are integers
                if not all(isinstance(x, int) for x in value_data):
                    raise ValueError("All sequence elements must be integers")

                # Determine size needed
                max_val = max(max(value_data), abs(min(value_data))) if value_data else 0

                if max_val <= 127:
                    if len(value_data) <= 255:
                        encoded = struct.pack('>BB', 0b00001000, len(value_data))
                        encoded += struct.pack('>' + 'b' * len(value_data), *value_data)
                        return encoded
                    else:
                        encoded = struct.pack('>BH', 0b00001100, len(value_data))
                        encoded += struct.pack('>' + 'b' * len(value_data), *value_data)
                        return encoded
                elif max_val <= 32767:
                    if len(value_data) <= 255:
                        encoded = struct.pack('>BB', 0b00001001, len(value_data))
                        encoded += struct.pack('>' + 'h' * len(value_data), *value_data)
                        return encoded
                    else:
                        encoded = struct.pack('>BH', 0b00001101, len(value_data))
                        encoded += struct.pack('>' + 'i' * len(value_data), *value_data)
                        return encoded
                elif max_val <= 2147483647:
                    if len(value_data) <= 255:
                        encoded = struct.pack('>BB', 0b00001010, len(value_data))
                        encoded += struct.pack('>' + 'i' * len(value_data), *value_data)
                        return encoded
                    else:
                        encoded = struct.pack('>BH', 0b00001110, len(value_data))
                        encoded += struct.pack('>' + 'i' * len(value_data), *value_data)
                        return encoded
                else: # 64 bit
                    if len(value_data) <= 255:
                        encoded = struct.pack('>BH', 0b00001111, len(value_data))
                        encoded += struct.pack('>' + 'q' * len(value_data), *value_data)
                        return encoded

        # TimeStamp types:
        elif value_type == "timestamp":
            if isinstance(value_data, str):
                if value_data.count(':') == 6:
                    encoded_ts = encode_timestamp_type0(value_data)
                    return struct.pack('>B', 0b00010000) + encoded_ts
                elif value_data.count(':') == 4:
                    encoded_ts = encode_timestamp_type1(value_data)
                    return struct.pack('>B', 0b00010001) + encoded_ts
                else:
                    raise ValueError(f"Invalid timestamp format: {value_data}")
            else:
                raise ValueError(f"Timestamp must be string: {value_data}")

        # STRING types
        elif value_type == "string":
            if isinstance(value_data, str):
                #ASCII normalized
                try:
                    encoded_str = value_data.encode('ascii')
                    if len(encoded_str) <= 65535:
                        return struct.pack('>BH', 0b00100000, len(encoded_str)) + encoded_str
                    else:
                        raise ValueError(f"String too long: {len(encoded_str)}")
                except UnicodeError:
                    # Extended ASCII
                    encoded_str = value_data.encode('latin-1')
            if len(encoded_str) <= 65535:
                return struct.pack('>BH', 0b00100001, len(encoded_str)) + encoded_str
            else:
                raise ValueError(f"String too long: {value_data}")

        #IID type
        elif value_type == "iid":
            if isinstance(value_data, str):
                encoded_iid = encode_single_iid(value_data)
                # Extract the data type bits from the encoded IID
                iid_data_type = encoded_iid[0]
                #MAP to IID value type encoding
                if iid_data_type == 0b01000000:
                    return struct.pack('>B', 0b01000000) + encoded_iid[1:]
                elif iid_data_type == 0b01000001:
                    return struct.pack('>b', 0b01000001) + encoded_iid[1:]
                elif iid_data_type == 0b01000011:
                    return struct.pack('>B', 0b01000011) + encoded_iid[1:]
                else: raise ValueError(f"Invalid IID data type: {iid_data_type:08b}")
            else:
                raise ValueError(f"IID must be string: {value_data}")
        else:
            raise ValueError(f"Unsupported value type: {value_data}")

    except Exception as e:
        raise ValueError(f"Value encoding failed: {e}")

def decode_value(data):
    """
    Decode a single value from bytes
    """
    if len(data) < 1:
        raise ValueError("No data for value decoding")

    data_type = data[0]

    try:
        #Byte types
        if data_type == 0b00000000: # Single byte
            if len(data) < 2:
                raise ValueError("Not enough data for single byte")
            value = struct.unpack('>B', data[1:2])[0]
            return value, data[2:]

        elif data_type == 0b00000001: # Short byte sequence
            if len(data) < 2:
                raise ValueError("Not enough data for byte sequence header")
            n_bytes = data[1]
            if len(data) < 2 + n_bytes:
                raise ValueError(f"Not enough data for byte sequence: need {n_bytes}, got {len(data)-2}")
            if n_bytes == 0:
                raise ValueError("Empty byte sequence not allowed")
            if len(data) < 2 + n_bytes:
                raise ValueError(f"Not enough data for byte sequence: need {n_bytes}, got {len(data)-2}")
            value = data[2:2+n_bytes]
            return value, data[2+n_bytes:]

        elif data_type == 0b00000010: # Long byte sequence
            if len(data) < 3:
                raise ValueError("Not enough data for, long byte sequence header")
            n_bytes = struct.unpack('>H', data[1:3])[0]
            if len(data) < 3 + n_bytes:
                raise ValueError(f"Not enough data for long byte sequence: need {n_bytes}, got {len(data)-3}")
            if n_bytes == 0:
                raise ValueError("Empty long byte sequence not allowed")
            value = data[3:3+n_bytes]
            return value, data[3+n_bytes:]

        # Integer types
        elif data_type in [0b00000100, 0b00000101, 0b00000110, 0b00000111]:
            if data_type == 0b00000100: # 8 bit int
                if len(data) < 2:
                    raise ValueError("Not enough data for 8-bit integer")
                value = struct.unpack('>b', data[1:2])[0]
                return value, data[2:]
            elif data_type == 0b00000101: # 16 bit int
                if len(data) < 3:
                    raise ValueError("Not enough data for 16-bit integer")
                value = struct.unpack('>h', data[1:3])[0]
                return value, data[3:]
            elif data_type == 0b00000110:   # 32 bit int
                if len(data) < 5:
                    raise ValueError("Not enough data for 32-bit integer")
                value = struct.unpack('>i', data[1:5])[0]
                return value, data[5:]
            elif data_type == 0b00000111:   # 64 bit int
                if len(data) < 9:
                    raise ValueError("not enough data for 64 bit integer")
                value = struct.unpack('>q', data[1:9])[0]
                return value, data[9:]

        # INTEGER SEQUENCE types
        elif data_type in range(0b00001000, 0b00010000):
            # Determine size and count from data_type
            size_bits = (data_type & 0b00000011)
            is_short = (data_type & 0b00000100) == 0

            sizes = {0: 1, 1: 2, 2: 4, 3: 8}    # bytes per element
            format_chars = {0: 'b', 1: 'h', 2: 'i', 3: 'q'}  # struct format chars

            size = sizes[size_bits]
            fmt_char = format_chars[size_bits]

            if is_short:
                if len(data) < 2:
                    raise ValueError("not enough data for integer sequence header")
                count = data[1]
                header_size = 2
            else:
                if len(data) < 3:
                    raise ValueError("Not enough data for long integer sequence header")
                count = struct.unpack('>H', data[1:3])[0]
                header_size = 3

            total_size = header_size + count * size
            if len(data) < total_size:
                raise ValueError(f"not enough data for integer sequence : need {total_size}, got {len(data)}")
            values = list(struct.unpack('>' + fmt_char * count, data[header_size:total_size]))
            return values, data[total_size:]

        # TIMESTAMP types
        elif data_type in [0b00010000, 0b00010001]:
            if len(data) < 7: # 3 * uint16 = 6 bytes
                raise ValueError("Not enough data for timestamp")

            timestamp_data = data[1:7]
            if data_type == 0b00010000: # Type 0
                value = decode_timestamp_type0(timestamp_data)
            else: # Type 1
                value = decode_timestamp_type1(timestamp_data)
            return value, data[7:]

        # STRING types
        elif (data_type & 0b11110000) == 0b00100000:
            if len(data) < 3:
                raise ValueError("Not enough data for string header")

            str_len = struct.unpack('>H', data[1:3])[0]
            if len(data) < 3 + str_len:
                raise ValueError(f"Not enough data for string: need {str_len}, got {len(data)-3}")

            string_data = data[3:3+str_len]
            encoding_bits = data_type & 0b00001111

            if encoding_bits == 0b0000: #ASCII normalized
                value = string_data.decode('ascii')
            elif encoding_bits == 0b001:   # Extended ASCII/ISO-8859-1
                value = string_data.decode('latin-1')
            else:
                value = string_data.decode('latin-1')   # Fallback

            return value, data[3+str_len:]

        #IID types
        elif data_type in [0b01000000, 0b01000001, 0b01000011]:
            # REconstruct the IID data type byte
            iid_data_type = 0b01000000 | (data_type & 0b00000011)
            iid_data = bytes([iid_data_type]) + data[1:]

            value, remaining = decode_single_iid(iid_data)
            return value, remaining
        else:
            raise ValueError(f"Unknow value data type: {data_type:08b}")

    except Exception as e:
        raise ValueError(f"Value decoding failed: {e}")


def encode_v_list(values, strict=True):
    """
    ENCODE A V-LIST - VERSÃO MAIS RESTRITIVA
    """
    if not values:
        return struct.pack('>B', 0)

    encoded_values = []
    for value in values:
        try:
            if isinstance(value, tuple) and len(value) == 2:
                value_data, value_type = value
                encoded = encode_value(value_data, value_type)
            else:
                # ✅ Para IIDs, tenta primeiro como IID específico
                if isinstance(value, str) and '.' in value:
                    try:
                        # Tenta como IID primeiro
                        encoded = encode_value(value, "iid")
                    except ValueError:
                        # Se falhar como IID, trata como string normal
                        if not strict:
                            encoded = encode_value(value, "string")
                        else:
                            raise ValueError(f"Invalid IID format: {value}")
                else:
                    encoded = encode_value(value)

            encoded_values.append(encoded)

        except Exception as e:
            if strict:
                raise ValueError(f"Failed to encode value {value}: {e}")
            else:
                print(f"⚠️ Skipping invalid value {value}: {e}")
                continue

    if not encoded_values:
        return struct.pack('>B', 0)

    return struct.pack('>B', len(encoded_values)) + b''.join(encoded_values)

def decode_v_list(data):
    """
    DECODE a V-List
    """
    if not data or len(data) == 0:
        return [], data

    try:
        num_elements = struct.unpack('>B', data[:1])[0]
    except:
        raise ValueError("Invalid V-List header")

    remaining_data = data[1:]
    decoded_values = []

    for i in range(num_elements):
        try:
            value, remaining_data = decode_value(remaining_data)
            decoded_values.append(value)
        except ValueError as e:
            print(f"⚠️ Skipping corrupted value {i + 1}/{num_elements}: {e}")
            continue

    return decoded_values, remaining_data

def encode_t_list(timestamps):
    """
    Encode a T-List
    """
    if not timestamps:
        return struct.pack('>B', 0)

    encoded_timestamps = []
    for timestamp in timestamps:
        try:
            if isinstance(timestamp, str):
                if timestamp.count(':') == 6:
                    encoded_ts = encode_timestamp_type0(timestamp)
                    encoded = struct.pack('>B', 0b00010000) + encoded_ts
                elif timestamp.count(':') == 4:
                    encoded_ts = encode_timestamp_type1(timestamp)
                    encoded = struct.pack('>B', 0b00010001) + encoded_ts
                else:
                    raise ValueError(f"Invalid timestamp format: {timestamp}")
            else:
                raise ValueError(f"Timestmap must be string, got {type(timestamp)}")

            encoded_timestamps.append(encoded)

        except Exception as e:
            print(f"⚠️ Error encoding timestamp {timestamp}: {e}")
            continue

    if not encoded_timestamps:
        return struct.pack('>B', 0)

    return struct.pack('>B', len(encoded_timestamps)) + b''.join(encoded_timestamps)

def decode_t_list(data):
    """
    DECODE A T-List
    """
    if not data or len(data) == 0:
        return [], data

    try:
        num_elements = struct.unpack('>B', data[:1])[0]
    except:
        raise ValueError("Invalid T-List header")

    remaining_data = data[1:]
    decoded_timestamps = []

    for i in range(num_elements):
        try:
            timestamp, remaining_data = decode_timestamp(remaining_data)
            decoded_timestamps.append(timestamp)
        except ValueError as e:
            print(f"⚠️ Skipping corrupted timestamp {i + 1}/{num_elements}: {e}")
            continue

    return decoded_timestamps, remaining_data

def decode_timestamp(data):
    """
    Decode a single timestap
    """
    if len(data) < 1:
        raise ValueError("No data for timestap decoding")

    data_type = data[0]

    if data_type == 0b00010000: #type0
        if len(data) < 7:
            raise ValueError("Not enough data for timestamp type0")
        timestamp_data = data[1:7]
        value = decode_timestamp_type0(timestamp_data)
        return value, data[7:]

    elif data_type == 0b00010001:   # type 1
        if len(data) < 7:
            raise ValueError("Not enough data for timestmap type 1")
        timestamp_data = data[1:7]
        value = decode_timestamp_type1(timestamp_data)
        return value, data[7:]

    else:
        raise ValueError(f"Invalid timestmap data type: {data_type:08b}")


def encode_e_list(error_codes):
    """
    Encode E-List conforme especificação L-SNMPvS
    """
    # 1. Validação de input
    if not isinstance(error_codes, list):
        return struct.pack('>B', 0)  # Retorna lista vazia

    # 2. Lista vazia
    if len(error_codes) == 0:
        return struct.pack('>B', 0)  # 00

    # 3. Processa cada código de erro
    encoded_errors = []
    valid_count = 0

    for error_code in error_codes:
        try:
            # Converte para integer
            code = int(error_code)

            # Verifica range (0-255)
            if 0 <= code <= 255:
                encoded_errors.append(struct.pack('>B', code))
                valid_count += 1

        except (ValueError, TypeError):
            # Elemento inválido - skip
            continue

    # 4. Se nenhum elemento válido, retorna lista vazia
    if valid_count == 0:
        return struct.pack('>B', 0)

    # 5. Constrói resultado final
    header = struct.pack('>B', valid_count)  # N-Elements
    data = b''.join(encoded_errors)  # Error codes
    return header + data


def decode_e_list(data):
    """
    Decode E-List conforme especificação L-SNMPvS
    Returns: (error_codes, remaining_data)
    """
    # 1. Validação de input
    if not data or len(data) == 0:
        return [], data

    try:
        # 2. Lê número de elementos
        num_elements = data[0]  # 1º byte
        remaining = data[1:]  # Resto dos dados

        # 3. Lê cada código de erro
        error_codes = []
        for i in range(num_elements):
            if len(remaining) < 1:
                break  # Dados insuficientes

            error_code = remaining[0]  # Lê 1 byte
            error_codes.append(error_code)
            remaining = remaining[1:]  # Avança

        return error_codes, remaining

    except Exception:
        # Em caso de erro, retorna lista vazia
        return [], data

def error_code_to_string(error_code):
    """
    Convert an error code to string
    """
    return ERROR_CODES.get(error_code, f"unknown error code: {error_code}")


def encode_complete_pdu(msg_type, timestamp, msg_id, iid_list, v_list, t_list, e_list=None):
    """
    Encode completo L-SNMPvS PDU
    """
    if e_list is None:
        e_list = []

    encoded = b''

    # 1. Tag (8 bytes)
    encoded += encode_tag()

    # 2. Type (1 byte)
    encoded += encode_type(msg_type)

    # 3. Timestamp (6 bytes - current time)
    #current_time = get_current_timestamp()
    encoded += encode_timestamp_type0(timestamp)

    # 4. MSG-ID (8 bytes)
    encoded += encode_MSGID(msg_id)

    # 5. IID-List (variável)
    encoded += encode_iid_list(iid_list)

    # 6. V-List (variável)
    encoded += encode_v_list(v_list)

    # 7. T-List (variável)
    encoded += encode_t_list(t_list)

    # 8. E-List (variável)
    encoded += encode_e_list(e_list)

    return encoded


def decode_complete_pdu(data):
    """
    Decode completo L-SNMPvS PDU
    """
    remaining = data

    # 1. Tag (8 bytes)
    if len(remaining) < 8:
        raise ValueError("Not enough data for tag")
    tag_bytes = remaining[:8]
    tag = decode_tag(tag_bytes)
    remaining = remaining[8:]

    # 2. Type (1 byte)
    if len(remaining) < 1:
        raise ValueError("Not enough data for type")
    type_byte = remaining[0]
    msg_type = decode_type(type_byte)
    remaining = remaining[1:]

    # 3. Timestamp (6 bytes)
    if len(remaining) < 6:
        raise ValueError("Not enough data for timestamp")
    timestamp_data = remaining[:6]
    timestamp = decode_timestamp_type0(timestamp_data)
    remaining = remaining[6:]

    # 4. MSG-ID (8 bytes)
    if len(remaining) < 8:
        raise ValueError("Not enough data for MSG-ID")
    msgid_data = remaining[:8]
    msg_id = decode_MSGID(msgid_data)
    remaining = remaining[8:]

    # 5. IID-List (variável)
    iid_list, remaining = decode_iid_list(remaining)

    # 6. V-List (variável)
    v_list, remaining = decode_v_list(remaining)

    # 7. T-List (variável)
    t_list, remaining = decode_t_list(remaining)

    # 8. E-List (variável)
    e_list, remaining = decode_e_list(remaining)

    return {
        'tag': tag,
        'type': msg_type,
        'timestamp': timestamp,
        'msg_id': msg_id,
        'iid_list': iid_list,
        'v_list': v_list,
        't_list': t_list,
        'e_list': e_list,
        'remaining_data': remaining
    }


def get_current_timestamp():
    """
    Get current timestamp in Type 0 format
    """
    now = datetime.now()
    return f"{now.day}:{now.month}:{now.year}:{now.hour}:{now.minute}:{now.second}:{now.microsecond // 1000}"

def encrypt(pdu_bytes, key):
    """Encrypt PDU bytes - call this BEFORE sending"""
    # Simple AES-ECB (for simplicity - CBC would be better)
    cipher = AES.new(key, AES.MODE_ECB)
    padded = pad(pdu_bytes, AES.block_size)
    return cipher.encrypt(padded)

def decrypt(encrypted_bytes, key):
    """Decrypt PDU bytes - call this AFTER receiving"""
    cipher = AES.new(key, AES.MODE_ECB)
    decrypted = cipher.decrypt(encrypted_bytes)
    return unpad(decrypted, AES.block_size)

if __name__ == "__main__":
    # PDU da Feature 1
    pdu_data = {
        'tag': 'LSNMPv2',
        'type': 'get-request',
        'timestamp': '13:11:2025:23:5:51:478',
        'msg_id': 3,
        'iid_list': ['1.1', '1.2', '1.3', '1.4', '1.5', '1.6', '1.7', '1.8', '1.9'],
        'v_list': [],
        't_list': [],
        'e_list': [],
        'remaining_data': b''
    }

    print("ENCODE:")
    encoded = encode_complete_pdu(
        msg_type=pdu_data['type'],
        timestamp=pdu_data['timestamp'],
        msg_id=pdu_data['msg_id'],
        iid_list=pdu_data['iid_list'],
        v_list=pdu_data['v_list'],
        t_list=pdu_data['t_list'],
        e_list=pdu_data['e_list']
    )
    print(f"Encoded ({len(encoded)} bytes): {encoded.hex()}")

    print("\nDECODE:")
    decoded = decode_complete_pdu(encoded)
    print(f"Decoded: {decoded}")