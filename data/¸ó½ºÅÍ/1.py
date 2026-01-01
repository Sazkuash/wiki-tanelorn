import os
import struct
from PIL import Image

def decompress_rle(data, width, height):
    size = width * height
    pixels = [0] * size
    ptr = 0
    i = 0
    while ptr < size and i < len(data):
        byte = data[i]
        i += 1
        if byte == 0x00:
            if i < len(data):
                count = data[i]
                i += 1
                ptr += count
        else:
            pixels[ptr] = byte
            ptr += 1
    return pixels[:size]

def extract_first_frame(filepath, output_folder):
    try:
        with open(filepath, 'rb') as f:
            if f.read(2) != b'SP': return
            f.seek(4)
            count_8bit = struct.unpack('<H', f.read(2))[0]
            if count_8bit == 0: return

            # --- CORREÇÃO DE PALETA (PADRÃO BGR -> RGB) ---
            f.seek(-1024, 2)
            palette_raw = f.read(1024)
            palette_rgb = []
            for i in range(0, 1024, 4):
                # Invertendo a ordem para corrigir o azul
                # Mudamos de [i+2, i+1, i] para [i, i+1, i+2] ou vice-versa
                r = palette_raw[i]
                g = palette_raw[i+1]
                b = palette_raw[i+2]
                palette_rgb.extend([r, g, b])

            f.seek(8)
            for _ in range(count_8bit):
                w = struct.unpack('<H', f.read(2))[0]
                h = struct.unpack('<H', f.read(2))[0]
                d_size = struct.unpack('<H', f.read(2))[0]
                
                if w <= 0 or h <= 0 or d_size == 0:
                    f.seek(d_size, 1)
                    continue
                
                raw_data = f.read(d_size)
                indices = decompress_rle(raw_data, w, h)
                
                # Criar imagem indexada (Modo P)
                img = Image.new('P', (w, h))
                img.putpalette(palette_rgb)
                img.putdata(indices)
                
                # Converter para RGBA para transparência real
                img_rgba = img.convert('RGBA')
                pixel_data = list(img_rgba.getdata())
                
                # O índice 0 no Ragnarok é SEMPRE transparente
                # Vamos forçar apenas o índice 0 a ser transparente
                new_pixels = []
                for idx, pixel in enumerate(pixel_data):
                    if indices[idx] == 0: # Se o índice original for 0
                        new_pixels.append((0, 0, 0, 0))
                    else:
                        new_pixels.append(pixel)
                
                img_rgba.putdata(new_pixels)
                
                filename = os.path.basename(filepath).replace(".spr", ".png").replace(".SPR", ".png")
                img_rgba.save(os.path.join(output_folder, filename))
                print(f"✅ Corrigido: {filename}")
                break 
    except Exception as e:
        print(f"❌ Erro em {os.path.basename(filepath)}: {e}")

def main():
    current_dir = os.getcwd()
    output_dir = os.path.join(current_dir, "extraidos")
    if not os.path.exists(output_dir): os.makedirs(output_dir)
    files = [f for f in os.listdir(current_dir) if f.lower().endswith('.spr')]
    print(f"🔎 Analisando {len(files)} arquivos...")
    for f in files:
        extract_first_frame(f, output_dir)
    print(f"\n🏁 Finalizado! Verifique se as cores em 'extraidos' estão corretas.")

if __name__ == "__main__":
    main()