#!/usr/bin/env python3
"""
🍓 Greenhouse Device QR Code Generator

Генерирует QR коды для устройств теплицы.
Каждый QR код содержит информацию для подключения телефона к AP устройства.

Использование:
    python generate_qr.py GH-0001
    python generate_qr.py GH-0001 GH-0002 GH-0003
    python generate_qr.py --range 1 10  # Генерирует GH-0001 до GH-0010
"""

import argparse
import sys

try:
    import qrcode
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    print("Установите зависимости: pip install qrcode pillow")
    sys.exit(1)


DEFAULT_AP_PASSWORD = "greenhouse2024"


def generate_qr_content(device_id: str, ap_password: str = DEFAULT_AP_PASSWORD) -> str:
    """Генерирует содержимое QR кода для устройства"""
    ssid = f"Greenhouse-{device_id}"
    return f"GREENHOUSE:UID={device_id};SSID={ssid};PWD={ap_password}"


def generate_qr_image(device_id: str, ap_password: str = DEFAULT_AP_PASSWORD, 
                      output_dir: str = ".") -> str:
    """
    Генерирует QR код с подписью устройства
    
    Args:
        device_id: ID устройства (например, "GH-0001")
        ap_password: Пароль точки доступа
        output_dir: Директория для сохранения
        
    Returns:
        Путь к сохранённому файлу
    """
    content = generate_qr_content(device_id, ap_password)
    
    # Создаём QR код
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=4,
    )
    qr.add_data(content)
    qr.make(fit=True)
    
    qr_img = qr.make_image(fill_color="black", back_color="white")
    qr_width, qr_height = qr_img.size
    
    # Добавляем подпись с ID устройства
    label_height = 40
    total_height = qr_height + label_height
    
    # Создаём финальное изображение
    final_img = Image.new('RGB', (qr_width, total_height), 'white')
    final_img.paste(qr_img, (0, 0))
    
    # Добавляем текст
    draw = ImageDraw.Draw(final_img)
    
    # Пытаемся использовать шрифт
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 20)
    except:
        try:
            font = ImageFont.truetype("arial.ttf", 20)
        except:
            font = ImageFont.load_default()
    
    # Центрируем текст
    text = f"🍓 {device_id}"
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_x = (qr_width - text_width) // 2
    text_y = qr_height + 8
    
    draw.text((text_x, text_y), text, fill="black", font=font)
    
    # Сохраняем
    output_path = f"{output_dir}/qr_{device_id}.png"
    final_img.save(output_path, "PNG")
    
    print(f"✅ Создан: {output_path}")
    print(f"   Содержимое: {content}")
    
    return output_path


def generate_range(start: int, end: int, ap_password: str = DEFAULT_AP_PASSWORD,
                   output_dir: str = "."):
    """Генерирует диапазон QR кодов"""
    for i in range(start, end + 1):
        device_id = f"GH-{i:04d}"
        generate_qr_image(device_id, ap_password, output_dir)


def main():
    parser = argparse.ArgumentParser(
        description="🍓 Генератор QR кодов для устройств теплицы"
    )
    
    parser.add_argument(
        'device_ids', 
        nargs='*',
        help='ID устройств (например: GH-0001 GH-0002)'
    )
    
    parser.add_argument(
        '--range', '-r',
        nargs=2,
        type=int,
        metavar=('START', 'END'),
        help='Диапазон номеров устройств (например: --range 1 10)'
    )
    
    parser.add_argument(
        '--password', '-p',
        default=DEFAULT_AP_PASSWORD,
        help=f'Пароль AP (по умолчанию: {DEFAULT_AP_PASSWORD})'
    )
    
    parser.add_argument(
        '--output', '-o',
        default='.',
        help='Директория для сохранения (по умолчанию: текущая)'
    )
    
    args = parser.parse_args()
    
    if args.range:
        start, end = args.range
        generate_range(start, end, args.password, args.output)
    elif args.device_ids:
        for device_id in args.device_ids:
            generate_qr_image(device_id, args.password, args.output)
    else:
        # Генерируем один пример
        print("Генерация примера QR кода...")
        generate_qr_image("GH-0001", args.password, args.output)
        print("\nИспользование:")
        print("  python generate_qr.py GH-0001 GH-0002")
        print("  python generate_qr.py --range 1 10")


if __name__ == "__main__":
    main()

