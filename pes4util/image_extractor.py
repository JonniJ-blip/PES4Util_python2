# pes4util/image_extractor.py

"""
Модуль для извлечения изображений из файлов сохранений PES 4 Master League
и файлов опций PES 4
"""

from .utils import xor_decode
from PIL import Image
import os
from typing import Optional, Tuple, List, Dict
from dataclasses import dataclass


@dataclass
class ImageInfo:
    """Информация об изображении"""
    name: str
    palette_offset: int
    pixel_offset: int
    width: int
    height: int
    pixel_size: int
    description: str = ""


class MLImageExtractor:
    """
    Извлекает изображения из файлов сохранений PES 4 Master League
    
    Структура изображений в файле:
    - Каждое изображение состоит из двух частей, идущих последовательно:
      1. Палитра (1024 байта, 256 цветов RGBA)
      2. Пиксели (индексы палитры)
    
    Основные изображения в ML файле:
    - Иконка 1: 22x15 (для меню)
    - Иконка 2: 22x15 (копия, для другого меню)
    - Флаг: 64x48 (основное изображение)
    
    В файле опций (OptionFile) изображения находятся в области флагов/эмблем:
    - Флаги: 64x48, смещение 0x0E1240 + n * 4160
    - Эмблемы: 32x32, смещение 0x0D53FC + n * 608
    """
    
    # Константы
    PALETTE_SIZE = 1024  # 256 цветов * 4 байта (RGBA)
    
    # Известные изображения в ML файле
    ML_IMAGES = {
        'icon1': ImageInfo(
            name='icon1',
            palette_offset=0x000000F0,
            pixel_offset=0x000004F0,
            width=22,
            height=15,
            pixel_size=330,
            description='Иконка 22x15 (основная)'
        ),
        'icon2': ImageInfo(
            name='icon2',
            palette_offset=0x00000650,
            pixel_offset=0x00000A50,
            width=22,
            height=15,
            pixel_size=330,
            description='Иконка 22x15 (копия)'
        ),
        'flag': ImageInfo(
            name='flag',
            palette_offset=0x000B7340,
            pixel_offset=0x000B7740,
            width=64,
            height=48,
            pixel_size=3072,
            description='Флаг 64x48'
        )
    }
    
    # Известные изображения в OptionFile
    OF_FLAG_SIZE = 4160
    OF_EMBLEM_SIZE = 608
    OF_FLAG_START = 0x0E1240
    OF_EMBLEM_START = 0x0D53FC
    
    def __init__(self, file_path: str, file_type: str = 'ml'):
        """
        Инициализация экстрактора
        
        Args:
            file_path: путь к файлу
            file_type: 'ml' или 'of' (option file)
        """
        self.file_path = file_path
        self.file_type = file_type
        self.data = None
        self._load_data()
    
    def _load_data(self):
        """Загружает и расшифровывает файл"""
        with open(self.file_path, 'rb') as f:
            raw = f.read()
        self.data = xor_decode(raw)
    
    def extract_palette(self, offset: int) -> List[Tuple[int, int, int]]:
        """
        Извлекает палитру из 1024 байт RGBA и преобразует в RGB
        
        Args:
            offset: смещение начала палитры в файле
            
        Returns:
            Список из 256 цветов RGB
        """
        if offset + self.PALETTE_SIZE > len(self.data):
            raise ValueError(f"Недостаточно данных по смещению 0x{offset:08X}")
        
        palette_raw = self.data[offset:offset + self.PALETTE_SIZE]
        palette_rgb = []
        
        for i in range(0, self.PALETTE_SIZE, 4):
            r, g, b, a = palette_raw[i], palette_raw[i+1], palette_raw[i+2], palette_raw[i+3]
            palette_rgb.append((r, g, b))
        
        return palette_rgb
    
    def extract_pixels(self, offset: int, size: int) -> List[int]:
        """
        Извлекает пиксельные данные (индексы палитры)
        
        Args:
            offset: смещение начала пиксельных данных
            size: количество байт (пикселей)
            
        Returns:
            Список индексов палитры
        """
        if offset + size > len(self.data):
            raise ValueError(f"Недостаточно данных по смещению 0x{offset:08X} (нужно {size} байт)")
        
        return list(self.data[offset:offset + size])
    
    def extract_image(self, image_info: ImageInfo) -> Image.Image:
        """
        Извлекает изображение по его описанию
        
        Args:
            image_info: информация об изображении
            
        Returns:
            PIL Image объект
        """
        # Извлекаем палитру
        palette = self.extract_palette(image_info.palette_offset)
        
        # Преобразуем палитру в плоский список для PIL
        palette_flat = []
        for r, g, b in palette:
            palette_flat.extend([r, g, b])
        
        # Извлекаем пиксели
        pixels = self.extract_pixels(image_info.pixel_offset, image_info.pixel_size)
        
        # Создаем изображение
        img = Image.new('P', (image_info.width, image_info.height))
        img.putpalette(palette_flat)
        
        # Заполняем пиксели (обрезаем до нужного размера)
        img.putdata(pixels[:image_info.width * image_info.height])
        
        return img
    
    def extract_ml_images(self) -> Dict[str, Image.Image]:
        """Извлекает все изображения из ML файла"""
        images = {}
        for name, info in self.ML_IMAGES.items():
            try:
                images[name] = self.extract_image(info)
            except Exception as e:
                print(f"⚠️ Не удалось извлечь {name}: {e}")
        return images
    
    def extract_of_flags(self, count: int = 64) -> Dict[int, Image.Image]:
        """
        Извлекает флаги из OptionFile
        
        Args:
            count: количество флагов (максимум 64)
            
        Returns:
            Словарь {индекс: PIL Image}
        """
        images = {}
        for i in range(count):
            try:
                # Каждый флаг: 4160 байт
                offset = self.OF_FLAG_START + i * self.OF_FLAG_SIZE
                
                # Палитра в начале флага (смещение 64)
                palette_offset = offset + 64
                palette = self.extract_palette(palette_offset)
                palette_flat = []
                for r, g, b in palette:
                    palette_flat.extend([r, g, b])
                
                # Пиксели после палитры (смещение 1088)
                pixel_offset = offset + 1088
                pixels = self.extract_pixels(pixel_offset, 3072)
                
                img = Image.new('P', (64, 48))
                img.putpalette(palette_flat)
                img.putdata(pixels[:3072])
                images[i] = img
                
            except Exception as e:
                print(f"⚠️ Не удалось извлечь флаг {i}: {e}")
        
        return images
    
    def extract_of_emblems(self, count: int = 80) -> Dict[int, Image.Image]:
        """
        Извлекает эмблемы из OptionFile
        
        Args:
            count: количество эмблем (максимум 80)
            
        Returns:
            Словарь {индекс: PIL Image}
        """
        images = {}
        for i in range(count):
            try:
                # Каждая эмблема: 608 байт
                offset = self.OF_EMBLEM_START + i * self.OF_EMBLEM_SIZE
                
                # Палитра в начале эмблемы (смещение 32)
                palette_offset = offset + 32
                palette = self.extract_palette(palette_offset)
                palette_flat = []
                for r, g, b in palette:
                    palette_flat.extend([r, g, b])
                
                # Пиксели после палитры (смещение 96)
                pixel_offset = offset + 96
                pixels = self.extract_pixels(pixel_offset, 512)  # 32*32 = 1024 / 2 = 512
                
                # Распаковываем 4-bit пиксели (2 пикселя в байте)
                unpacked = []
                for b in pixels:
                    p1 = (b >> 4) & 0x0F
                    p2 = b & 0x0F
                    unpacked.append(p1)
                    unpacked.append(p2)
                
                img = Image.new('P', (32, 32))
                img.putpalette(palette_flat)
                img.putdata(unpacked[:1024])
                images[i] = img
                
            except Exception as e:
                print(f"⚠️ Не удалось извлечь эмблему {i}: {e}")
        
        return images
    
    def save_image(self, img: Image.Image, output_path: str, scale: int = 8):
        """Сохраняет изображение и его увеличенную версию"""
        img.save(output_path)
        w, h = img.size
        img_large = img.resize((w * scale, h * scale), Image.NEAREST)
        base, ext = os.path.splitext(output_path)
        img_large.save(f"{base}_large{ext}")
    
    def save_all_ml_images(self, output_dir: str, scale: int = 8):
        """Извлекает и сохраняет все ML изображения"""
        os.makedirs(output_dir, exist_ok=True)
        base_name = os.path.splitext(os.path.basename(self.file_path))[0]
        
        images = self.extract_ml_images()
        for name, img in images.items():
            output_path = os.path.join(output_dir, f"{base_name}_{name.upper()}.png")
            self.save_image(img, output_path, scale)
            print(f"  ✅ {name}: {img.size[0]}x{img.size[1]}")
    
    def save_of_flags(self, output_dir: str, count: int = 64, scale: int = 8):
        """Извлекает и сохраняет флаги из OptionFile"""
        os.makedirs(output_dir, exist_ok=True)
        base_name = os.path.splitext(os.path.basename(self.file_path))[0]
        
        images = self.extract_of_flags(count)
        for idx, img in images.items():
            output_path = os.path.join(output_dir, f"{base_name}_flag_{idx:02d}.png")
            self.save_image(img, output_path, scale)
            print(f"  ✅ Флаг {idx}: {img.size[0]}x{img.size[1]}")
    
    def save_of_emblems(self, output_dir: str, count: int = 80, scale: int = 8):
        """Извлекает и сохраняет эмблемы из OptionFile"""
        os.makedirs(output_dir, exist_ok=True)
        base_name = os.path.splitext(os.path.basename(self.file_path))[0]
        
        images = self.extract_of_emblems(count)
        for idx, img in images.items():
            output_path = os.path.join(output_dir, f"{base_name}_emblem_{idx:02d}.png")
            self.save_image(img, output_path, scale)
            print(f"  ✅ Эмблема {idx}: {img.size[0]}x{img.size[1]}")