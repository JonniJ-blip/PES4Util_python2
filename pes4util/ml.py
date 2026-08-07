"""Работа с файлами сохранения Master League PES4"""

import os
from pes4util.utils import xor_decode, read_string

# Константы
ML_PLAYER_AREAS = [
    (0x09A000, 0x09C000),  # Созданные игроки (основные)
    (0x0B5000, 0x0B7000),  # Созданные игроки (дополнительные)
]
ML_PLAYER_SIZE = 124
ML_NAME_SIZE = 32
ML_SHIRT_SIZE = 16

# Смещения статов (из OptionFile)
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


class MLFile:
    """Файл сохранения Master League"""
    
    def __init__(self):
        self.data = None
        self.file_name = ""
        self.players = []  # список созданных игроков
    
    def read(self, filepath: str) -> bool:
        """Загрузить ML файл"""
        try:
            self.file_name = os.path.basename(filepath)
            with open(filepath, 'rb') as f:
                raw = f.read()
            self.data = bytearray(xor_decode(raw))
            self._parse_players()
            return True
        except Exception as e:
            print(f"Error: {e}")
            return False
    
    def _parse_players(self):
        """Извлечь созданных игроков"""
        self.players = []
        for start, end in ML_PLAYER_AREAS:
            pos = start
            while pos + ML_PLAYER_SIZE <= end and pos + ML_PLAYER_SIZE <= len(self.data):
                name = read_string(self.data, pos, ML_NAME_SIZE)
                shirt = read_string(self.data, pos + ML_NAME_SIZE, ML_SHIRT_SIZE)
                
                if name and len(name) >= 2:
                    self.players.append({
                        'name': name,
                        'shirt': shirt,
                        'pos': pos,
                        'raw': bytes(self.data[pos:pos + ML_PLAYER_SIZE])
                    })
                pos += ML_PLAYER_SIZE
    
    def _read_stat(self, raw: bytes, offset: int, shift: int, mask: int) -> int:
        """Читает стат из сырого блока (смещение 48 от начала)"""
        base = 48
        if base + offset >= len(raw):
            return 0
        val = raw[base + offset] << 8 | raw[base + offset - 1]
        return (val >> shift) & mask
    
    # ============ МЕТОДЫ ДЛЯ ПОЛЬЗОВАТЕЛЯ ============
    
    def get_players(self):
        """Список всех созданных игроков [{name, shirt, pos, raw}]"""
        return self.players
    
    def get_player_names(self):
        """Только имена созданных игроков"""
        return [p['name'] for p in self.players]
    
    def find_player(self, query: str):
        """Найти игрока по имени (частичное совпадение)"""
        query = query.lower().strip()
        for p in self.players:
            if query in p['name'].lower():
                return p
        return None
    
    def get_player_stats(self, player: dict) -> dict:
        """Получить все статы созданного игрока из ML"""
        if 'raw' not in player:
            return {}
        
        raw = player['raw']
        stats = {}
        
        for name, offset, shift, mask in PLAYER_STATS:
            stats[name] = self._read_stat(raw, offset, shift, mask)
        
        # Возраст
        age_val = self._read_stat(raw, 61, 11, 31)
        stats['Age'] = age_val + 15
        
        # Рост
        height_val = self._read_stat(raw, 40, 8, 63)
        stats['Height'] = height_val + 148
        
        # Вес
        weight_val = self._read_stat(raw, 41, 6, 127)
        stats['Weight'] = weight_val + 1
        
        # Нога
        foot_val = self._read_stat(raw, 31, 5, 1)
        stats['Foot'] = 'Left' if foot_val == 1 else 'Right'
        
        return stats
    
    def get_player_stat(self, player: dict, stat_name: str) -> int:
        """Получить один стат игрока"""
        stats = self.get_player_stats(player)
        return stats.get(stat_name, 0)
    
    def get_player_age(self, player: dict) -> int:
        """Получить возраст игрока из ML"""
        return self.get_player_stat(player, 'Age')
    
    def get_player_height(self, player: dict) -> int:
        """Получить рост игрока из ML"""
        return self.get_player_stat(player, 'Height')
    
    def get_player_count(self) -> int:
        """Количество созданных игроков"""
        return len(self.players)
    
    def get_week(self) -> int:
        """Получить текущую неделю из ML файла (0x5E)"""
        if 0x5E < len(self.data):
            week = self.data[0x5E]
            if 1 <= week <= 52:
                return week
        return None
    
    def get_season(self) -> int:
        """Получить сезон (год) из ML файла (2003 + байт 0x36)"""
        if 0x36 < len(self.data):
            season_num = self.data[0x36]
            if 1 <= season_num <= 10:
                return 2003 + season_num
        return None