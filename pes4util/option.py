"""Работа с файлом опций PES4"""

import os
import struct
from .utils import *

class OptionFile:
    """Файл опций PES4"""
    
    def __init__(self):
        self.data = bytearray(OPTION_FILE_LENGTH)
        self.game_id = None
        self.file_name = ""
    
    # ============ ЗАГРУЗКА ============
    
    def read(self, filepath: str) -> bool:
        """Загрузить файл опций"""
        try:
            self.file_name = os.path.basename(filepath)
            
            with open(filepath, 'rb') as f:
                raw = bytearray(f.read())
            
            # Определяем формат
            if len(raw) > 21 and raw[0] == 0x0D and raw[1] == 0x00:
                # XPS (SharkPort)
                pos = 21
                for _ in range(3):
                    size = swab_int(struct.unpack('>I', raw[pos:pos+4])[0])
                    pos += 4 + size
                
                self.data = raw[pos:pos + OPTION_FILE_LENGTH]
                if len(self.data) < OPTION_FILE_LENGTH:
                    self.data += b'\x00' * (OPTION_FILE_LENGTH - len(self.data))
                self.game_id = 'ps2'
                
            else:
                # PC или XBOX
                if len(raw) >= OPTION_FILE_LENGTH:
                    self.data = raw[:OPTION_FILE_LENGTH]
                else:
                    self.data = raw + b'\x00' * (OPTION_FILE_LENGTH - len(raw))
                
                # Пробуем расшифровать как PC
                test = xor_decode(self.data)
                if test[0] != 0 or test[1] != 0:
                    self.game_id = 'pc'
                    self.data = bytearray(test)
                else:
                    self.game_id = 'xbox'
            
            return True
            
        except Exception as e:
            print(f"Ошибка загрузки: {e}")
            return False
    
    # ============ КОМАНДЫ ============
    
    def get_team_list(self):
        """Список всех команд [{id, name, abv}]"""
        teams = []
        for i in range(TEAMS_TOTAL):
            teams.append({
                'id': i,
                'name': self.get_team_name(i),
                'abv': self.get_team_abv(i)
            })
        return teams
    
    def get_team_name(self, team_id: int) -> str:
        """Название команды по ID"""
        if team_id < 0 or team_id >= TEAMS_TOTAL:
            return ""
        
        # Сборные
        if team_id < len(NATIONAL_TEAMS):
            return NATIONAL_TEAMS[team_id]
        
        # Клубы
        if team_id < TEAMS_CLUB_END:
            addr = TEAM_NAME_OFFSET + (team_id - TEAMS_CLUB_START) * TEAM_SIZE
            name = read_string(self.data, addr, 24)
            if name:
                return name
            return f"Club {team_id - TEAMS_CLUB_START}"
        
        # Особые
        special = {
            212: "<ML Default 1>",
            213: "Shop 1",
            214: "Shop 2", 
            215: "Shop 3",
            216: "<ML Default 2>",
            217: "<ML Default 3>",
            218: "Free"
        }
        return special.get(team_id, f"Team {team_id}")
    
    def get_team_abv(self, team_id: int) -> str:
        """Аббревиатура команды"""
        if TEAMS_CLUB_START <= team_id < TEAMS_CLUB_END:
            addr = TEAM_ABV_OFFSET + (team_id - TEAMS_CLUB_START) * TEAM_SIZE
            return read_string(self.data, addr, 3)
        return ""
    
    def get_team_players(self, team_id: int):
        """Список ID игроков команды"""
        if team_id == 218:
            return self._get_free_agents()
        
        if team_id < TEAMS_CLUB_START:
            size = SQUAD_NATIONAL_SIZE
            base = SQUAD_BASE + team_id * size * 2
        elif team_id < TEAMS_CLUB_END:
            size = SQUAD_CLUB_SIZE
            base = SQUAD_BASE + (team_id - TEAMS_CLUB_START) * size * 2
        else:
            return []
        
        players = []
        for i in range(size):
            addr = base + i * 2
            pid = get_u16(self.data, addr)
            if pid > 0 and pid != 65535:
                players.append(pid)
        return players
    
    def _get_free_agents(self):
        """Свободные агенты"""
        # Все игроки в командах
        used = set()
        for t in range(TEAMS_TOTAL):
            if t != 218:
                used.update(self.get_team_players(t))
        
        # Неиспользуемые
        free = []
        for i in range(1, PLAYER_MAX_NORMAL):
            if i not in used:
                free.append(i)
        return free
    
    # ============ ИГРОКИ ============
    
    def get_player_name(self, player_id: int) -> str:
        """Имя игрока по ID"""
        if player_id == 0 or player_id == 65535:
            return "<empty>"
        
        if player_id <= PLAYER_MAX_NORMAL:
            base = PLAYER_BASE
            offset = player_id * PLAYER_SIZE
        else:
            base = PLAYER_BASE_CREATED
            offset = (player_id - PLAYER_CREATED_START) * PLAYER_SIZE
        
        name = read_string(self.data, base + offset, 32)
        
        if not name:
            if player_id > PLAYER_MAX_NORMAL:
                return f"<created {player_id - PLAYER_CREATED_START}>"
            return f"<{player_id}>"
        return name
    
    def get_player_stat(self, player_id: int, stat_name: str):
        """Один стат игрока (число)"""
        stats = self.get_player_stats(player_id)
        return stats.get(stat_name, 0)
    
    def get_player_stats(self, player_id: int) -> dict:
        """Все статы игрока {stat: value}"""
        if player_id == 0 or player_id == 65535:
            return {}
        
        if player_id <= PLAYER_MAX_NORMAL:
            base = PLAYER_BASE + 48
            offset = player_id * PLAYER_SIZE
        else:
            base = PLAYER_BASE_CREATED + 48
            offset = (player_id - PLAYER_CREATED_START) * PLAYER_SIZE
        
        data = self.data
        addr = base + offset
        stats = {}
        
        # Основные статы
        for name, off, shift, mask in PLAYER_STATS:
            stats[name] = read_stat(data, addr + off, shift, mask)
        
        # Возраст
        age = read_stat(data, addr + 61, 11, 31)
        stats['Age'] = age + 15
        
        # Рост
        height = read_stat(data, addr + 40, 8, 63)
        stats['Height'] = height + 148
        
        # Вес
        weight = read_stat(data, addr + 41, 6, 127)
        stats['Weight'] = weight + 1
        
        # Нога
        foot = read_stat(data, addr + 31, 5, 1)
        stats['Foot'] = 'Left' if foot == 1 else 'Right'
        
        return stats
    
    def search_player(self, query: str):
        """Поиск игроков по имени [{id, name}]"""
        query = query.lower().strip()
        results = []
        
        # Обычные игроки
        for i in range(1, PLAYER_MAX_NORMAL):
            name = self.get_player_name(i)
            if query in name.lower():
                results.append({'id': i, 'name': name})
                if len(results) >= 100:
                    break
        
        return results