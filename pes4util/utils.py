"""Константы и утилиты для PES4"""

# ============ КЛЮЧИ ДЛЯ РАСШИФРОВКИ ============

# Ключ XOR для PC файлов
KEY_PC = bytes([
    87, 84, 37, 154, 195, 240, 177, 214, 111, 204, 125, 82, 91, 232, 137, 14,
    135, 68, 213, 10, 243, 224, 97, 70, 159, 188, 45, 194, 139, 216, 57, 126,
    183, 52, 133, 122, 35, 208, 17, 182, 207, 172, 221, 50, 187, 200, 233, 238,
    231, 36, 53, 234, 83, 192, 193, 38, 255, 156, 141, 162, 235, 184, 153, 94,
    23, 20, 229, 90, 131, 176, 113, 150, 47, 140, 61, 18, 27, 168, 73, 206,
    71, 4, 149, 202, 179, 160, 33, 6, 95, 124, 237, 130, 75, 152, 249, 62,
    119, 244, 69, 58, 227, 144, 209, 118, 143, 108, 157, 242, 123, 136, 169, 174,
    167, 228, 245, 170, 19, 128, 129, 230, 191, 92, 77, 98, 171, 120, 89, 30,
    215, 212, 165, 26, 67, 112, 49, 86, 239, 76, 253, 210, 219, 104, 9, 142,
    7, 196, 85, 138, 115, 96, 225, 198, 31, 60, 173, 66, 11, 88, 185, 254,
    55, 180, 5, 250, 163, 80, 145, 54, 79, 44, 93, 178, 59, 72, 105, 110,
    103, 164, 181, 106, 211, 64, 65, 166, 127, 28, 13, 34, 107, 56, 25, 222,
    151, 148, 101, 218, 3, 48, 241, 22, 175, 12, 189, 146, 155, 40, 201, 78,
    199, 132, 21, 74, 51, 32, 161, 134, 203, 252, 109, 2, 203, 24, 121, 190,
    249, 116, 197, 186, 99, 16, 81, 246, 15, 236, 29, 114, 251, 8, 41, 46,
    39, 100, 117, 42, 147, 0, 1, 102, 63, 220, 205, 226, 43, 248, 217, 158
])

# ============ КОНСТАНТЫ ФАЙЛА ОПЦИЙ ============

OPTION_FILE_LENGTH = 1264640

# Смещения
PLAYER_BASE = 31568          # база обычных игроков
PLAYER_BASE_CREATED = 8744   # база созданных игроков  
PLAYER_SIZE = 124            # размер блока игрока
PLAYER_MAX_NORMAL = 4999     # последний обычный игрок

TEAM_NAME_OFFSET = 797421
TEAM_ABV_OFFSET = 797445
TEAM_STADIUM_OFFSET = 797505
TEAM_SIZE = 140
TEAMS_CLUB_START = 74
TEAMS_CLUB_END = 212
TEAMS_TOTAL = 218

SQUAD_BASE = 657886
SQUAD_NATIONAL_SIZE = 23
SQUAD_CLUB_SIZE = 32

# Сборные (захардкожены в игре)
NATIONAL_TEAMS = [
    "Austria", "Belgium", "Bulgaria", "Croatia", "Czech Republic",
    "Denmark", "England", "Finland", "France", "Germany",
    "Greece", "Hungary", "Ireland", "Italy", "Latvia",
    "Netherlands", "Northern Ireland", "Norway", "Poland", "Portugal",
    "Romania", "Russia", "Scotland", "Serbia and Montenegro",
    "Slovakia", "Slovenia", "Spain", "Sweden", "Switzerland",
    "Turkey", "Ukraine", "Wales", "Cameroon", "Egypt",
    "Morocco", "Nigeria", "Senegal", "South Africa", "Tunisia",
    "Costa Rica", "Jamaica", "Mexico", "USA", "Argentina",
    "Brazil", "Chile", "Colombia", "Ecuador", "Paraguay",
    "Peru", "Uruguay", "China", "Iran", "Japan",
    "South Korea", "Saudi Arabia", "Australia",
    "Classic Argentina", "Classic Brazil", "Classic England",
    "Classic France", "Classic Germany", "Classic Italy",
    "Classic Netherlands"
]

# Статы игрока: (название, смещение, сдвиг, маска)
PLAYER_STATS = [
    ('Attack', 5, 4, 127),
    ('Defence', 6, 3, 127),
    ('Balance', 7, 2, 127),
    ('Stamina', 7, 9, 127),
    ('Speed', 8, 8, 127),
    ('Acceleration', 9, 7, 127),
    ('Response', 10, 6, 127),
    ('Agility', 29, 7, 127),
    ('Dribble Acc', 11, 5, 127),
    ('Dribble Speed', 12, 8, 127),
    ('Short Pass Acc', 13, 7, 127),
    ('Short Pass Speed', 14, 6, 127),
    ('Long Pass Acc', 15, 5, 127),
    ('Long Pass Speed', 16, 8, 127),
    ('Shot Acc', 18, 6, 127),
    ('Shot Power', 17, 7, 127),
    ('Shot Technique', 19, 5, 127),
    ('Free Kick', 27, 4, 127),
    ('Curling', 23, 5, 127),
    ('Heading', 21, 7, 127),
    ('Jump', 20, 8, 127),
    ('Technique', 22, 6, 127),
    ('Aggression', 24, 8, 127),
    ('Mental', 25, 7, 127),
    ('GK Ability', 30, 6, 127),
    ('Teamwork', 28, 8, 127),
]

# ============ УТИЛИТЫ ============

def xor_decode(data: bytes) -> bytes:
    """Decrypt PC option file data using XOR key"""
    result = bytearray(len(data))
    k = 0
    for i in range(len(data)):
        result[i] = data[i] ^ KEY_PC[k]
        k = (k + 1) % 256
    return bytes(result)

def swab_int(v: int) -> int:
    """Swap endianness of 32-bit integer"""
    return (v >> 24) | ((v << 24) & 0xFF000000) | ((v << 8) & 0xFF0000) | ((v >> 8) & 0xFF00)

def get_u16(data: bytes, addr: int) -> int:
    """Read 16-bit value at address (little-endian)"""
    if addr + 1 >= len(data):
        return 0
    return data[addr] | (data[addr + 1] << 8)

def read_stat(data: bytes, addr: int, shift: int, mask: int) -> int:
    """Read a player stat from data"""
    if addr >= len(data):
        return 0
    val = get_u16(data, addr - 1)
    val >>= shift
    val &= mask
    return val

def read_string(data: bytes, addr: int, max_len: int = 32, encoding: str = 'utf-16le') -> str:
    """Read a string from data with specified encoding"""
    if addr >= len(data):
        return ""
    
    end = min(addr + max_len, len(data))
    raw = data[addr:end]
    
    try:
        # Try UTF-16LE first
        s = raw.decode(encoding, errors='ignore')
        null_pos = s.find('\x00')
        if null_pos != -1:
            s = s[:null_pos]
        return s.strip()
    except:
        pass
    
    # Fallback to ASCII
    try:
        s = raw.decode('ascii', errors='ignore')
        null_pos = s.find('\x00')
        if null_pos != -1:
            s = s[:null_pos]
        return s.strip()
    except:
        return ""