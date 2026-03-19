# processing_logic.py

import os
import shutil
import time
import subprocess
import traceback
from datetime import datetime

# DEFINICIONES GLOBALES
VALID_EXTENSIONS = ('.jpg', '.jpeg', '.png', '.webp', '.bmp')

def escribir_log(mensaje):
    """Escribe errores y eventos en debug_log.txt para diagnóstico."""
    try:
        ruta_log = os.path.join(os.path.dirname(os.path.abspath(__file__)), "debug_log.txt")
        with open(ruta_log, "a", encoding="utf-8") as f:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            f.write(f"[{timestamp}] {mensaje}\n")
    except:
        pass # Si falla el log, seguimos igual.

def buscar_ffmpeg():
    """Busca ffmpeg.exe de forma robusta (local o sistema)."""
    # 1. Buscar en la carpeta donde está este script (prioridad absoluta)
    carpeta_del_script = os.path.dirname(os.path.abspath(__file__))
    ffmpeg_local = os.path.join(carpeta_del_script, "ffmpeg.exe")
    
    if os.path.exists(ffmpeg_local):
        escribir_log(f"FFmpeg encontrado (LOCAL): {ffmpeg_local}")
        return ffmpeg_local
    
    # 2. Buscar en el sistema (PATH)
    ffmpeg_sistema = shutil.which("ffmpeg")
    if ffmpeg_sistema:
        escribir_log(f"FFmpeg encontrado (SISTEMA): {ffmpeg_sistema}")
        return ffmpeg_sistema
    
    escribir_log("ERROR CRÍTICO: FFmpeg no encontrado.")
    return None

def procesar_imagenes(ruta_input, ruta_output, redimensionar, ancho, alto, anchor_bottom_center, progress_queue):
    escribir_log("--- INICIO PROCESO DE IMÁGENES ---")
    
    # IMPORTACIÓN TARDÍA (Para evitar crash al inicio)
    try:
        from rembg import remove
        from PIL import Image
    except ImportError as e:
        msg = f"Error Crítico: Faltan librerías (rembg/PIL).\n{e}"
        escribir_log(msg)
        progress_queue.put((0, 0, msg))
        return

    try:
        # Validaciones
        if not os.path.exists(ruta_input):
            progress_queue.put((0, 0, "Error: La carpeta de entrada no existe."))
            return
        
        if not os.path.exists(ruta_output): 
            os.makedirs(ruta_output)

        todos_archivos = os.listdir(ruta_input)
        archivos_validos = [f for f in todos_archivos if f.lower().endswith(VALID_EXTENSIONS)]
        total_files = len(archivos_validos)
        
        escribir_log(f"Archivos encontrados: {total_files}")

        if total_files == 0:
            progress_queue.put((0, 0, "Error: No hay imágenes válidas."))
            return

        progress_queue.put((0, total_files, "Cargando motor IA..."))

        # Bucle principal
        for i, filename in enumerate(archivos_validos):
            try:
                # Notificar progreso
                progress_queue.put((i, total_files, f"Procesando: {filename}"))
                
                ruta_completa_in = os.path.join(ruta_input, filename)
                nombre_base = os.path.splitext(filename)[0]
                ruta_completa_out = os.path.join(ruta_output, f"{nombre_base}.png")

                # 1. Leer archivo
                with open(ruta_completa_in, 'rb') as file_in:
                    input_data = file_in.read()
                
                # 2. Quitar fondo
                subject = remove(input_data)

                # 3. Guardar / Transformar
                if redimensionar or anchor_bottom_center:
                    from io import BytesIO
                    img = Image.open(BytesIO(subject))
                    img_final = _aplicar_transformacion_pil(img, redimensionar, int(ancho), int(alto), anchor_bottom_center)
                    img_final.save(ruta_completa_out)
                else:
                    with open(ruta_completa_out, 'wb') as file_out:
                        file_out.write(subject)

            except Exception as e:
                escribir_log(f"Fallo en archivo {filename}: {e}")
                print(f"Error en {filename}: {e}")
                continue

        progress_queue.put((total_files, total_files, "¡Proceso Completado!"))
        escribir_log("Fin exitoso de imágenes.")

    except Exception as e:
        escribir_log(f"Error Fatal Imágenes: {e}")
        escribir_log(traceback.format_exc())
        progress_queue.put((0, 0, f"Error: {str(e)}"))

def _aplicar_transformacion_pil(img_original, redimensionar, target_w, target_h, anchor_bottom):
    """Lógica auxiliar de recorte y redimensión"""
    from PIL import Image
    try:
        bbox = img_original.getbbox()
        if not bbox: return img_original
        
        character_img = img_original.crop(bbox)
        
        if anchor_bottom:
            canvas_w, canvas_h = target_w, target_h
            final_canvas = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
            
            scale_ratio = min(canvas_w / character_img.width, canvas_h / character_img.height)
            new_char_w = int(character_img.width * scale_ratio)
            new_char_h = int(character_img.height * scale_ratio)
            
            character_img_resized = character_img.resize((new_char_w, new_char_h), Image.Resampling.LANCZOS)
            
            x_offset = (canvas_w - new_char_w) // 2
            y_offset = canvas_h - new_char_h
            
            final_canvas.paste(character_img_resized, (x_offset, y_offset), character_img_resized)
            return final_canvas

        elif redimensionar:
            return character_img.resize((target_w, target_h), Image.Resampling.LANCZOS)
        
        return character_img
    except Exception as e:
        escribir_log(f"Error transformación PIL: {e}")
        return img_original

def procesar_video(ruta_video, ruta_salida_frames, fps, quitar_fondo, redimensionar, ancho, alto, anchor_bottom_center, progress_queue):
    escribir_log("--- INICIO PROCESO DE VIDEO ---")
    
    # 1. Buscar FFmpeg
    ruta_ffmpeg = buscar_ffmpeg()
    
    if not ruta_ffmpeg:
        msg = "ERROR: No se encontró ffmpeg.exe.\nAsegurate de que 'ffmpeg.exe' esté en la misma carpeta que el programa."
        escribir_log(msg)
        progress_queue.put((0, 0, msg))
        time.sleep(5) # Pausa para que el usuario lea
        return

    # 2. Importación tardía de librerías de imagen
    try:
        from rembg import remove
        from PIL import Image
    except ImportError:
        if quitar_fondo:
            msg = "Error: Faltan librerías rembg/PIL para quitar fondo."
            escribir_log(msg)
            progress_queue.put((0, 0, msg))
            return

    try:
        os.makedirs(ruta_salida_frames, exist_ok=True)
        progress_queue.put((0, 100, "Extrayendo frames con FFmpeg..."))
        
        temp_dir = os.path.join(ruta_salida_frames, "temp_raw_frames")
        if os.path.exists(temp_dir): shutil.rmtree(temp_dir)
        os.makedirs(temp_dir)

        escribir_log(f"Ejecutando: {ruta_ffmpeg} en {ruta_video}")

        # 3. EJECUCIÓN DE FFMPEG
        # Usamos creationflags para evitar la ventana negra en Windows
        subprocess.run([
            ruta_ffmpeg, '-i', ruta_video, '-vf', f'fps={fps}', 
            os.path.join(temp_dir, 'frame_%06d.png')
        ], check=True, creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)

        frames = sorted(os.listdir(temp_dir))
        total_frames = len(frames)
        escribir_log(f"Frames extraídos: {total_frames}")

        if total_frames == 0:
             progress_queue.put((0, 0, "Error: FFmpeg no generó frames."))
             return

        # 4. Procesamiento
        if not quitar_fondo:
            # Solo mover archivos
            for f in frames:
                shutil.move(os.path.join(temp_dir, f), os.path.join(ruta_salida_frames, f))
            shutil.rmtree(temp_dir)
            progress_queue.put((100, 100, "¡Listo (Solo extracción)!"))
            escribir_log("Extracción finalizada.")
            return

        # Con IA
        progress_queue.put((10, 100, "Iniciando eliminación de fondo..."))
        
        for i, frame in enumerate(frames):
            ruta_in = os.path.join(temp_dir, frame)
            ruta_out = os.path.join(ruta_salida_frames, frame)
            
            with open(ruta_in, 'rb') as f_in:
                data = f_in.read()
                out_data = remove(data)
            
            if redimensionar or anchor_bottom_center:
                from io import BytesIO
                img = Image.open(BytesIO(out_data))
                img_final = _aplicar_transformacion_pil(img, redimensionar, int(ancho), int(alto), anchor_bottom_center)
                img_final.save(ruta_out)
            else:
                with open(ruta_out, 'wb') as f_out:
                    f_out.write(out_data)

            # Actualizar barra cada 5 frames
            if i % 5 == 0:
                porcentaje = 10 + int((i / total_frames) * 90)
                progress_queue.put((porcentaje, 100, f"Frame {i}/{total_frames}"))

        shutil.rmtree(temp_dir)
        progress_queue.put((100, 100, "¡Video completado!"))
        escribir_log("Proceso de video finalizado con éxito.")

    except subprocess.CalledProcessError as e:
        escribir_log(f"Error de FFmpeg: {e}")
        progress_queue.put((0, 0, "Error: Falló FFmpeg al procesar el video."))
    except Exception as e:
        escribir_log(f"Error Video General: {e}")
        escribir_log(traceback.format_exc())
        progress_queue.put((0, 0, f"Error: {str(e)}"))


def procesar_imagen_web(input_bytes, redimensionar=False, ancho=512, alto=512, anchor_bottom_center=False):
    """
    Función exclusiva para la API web. 
    Procesa una imagen en memoria (RAM) sin tocar el disco rígido.
    """
    try:
        from rembg import remove
        from PIL import Image
        from io import BytesIO
        
        # 1. Quitar fondo directamente de los bytes
        subject_bytes = remove(input_bytes)
        
        # 2. Si hay que redimensionar, usamos tu lógica existente
        if redimensionar or anchor_bottom_center:
            img = Image.open(BytesIO(subject_bytes))
            img_final = _aplicar_transformacion_pil(
                img_original=img, 
                redimensionar=redimensionar, 
                target_w=int(ancho), 
                target_h=int(alto), 
                anchor_bottom=anchor_bottom_center
            )
            
            # Volver a convertir a bytes para mandar por la red
            salida_bytes = BytesIO()
            img_final.save(salida_bytes, format="PNG")
            return salida_bytes.getvalue()
        
        # Si no hay transformación, devolvemos el recorte limpio
        return subject_bytes
        
    except Exception as e:
        escribir_log(f"Error en procesar_imagen_web: {e}")
        raise e # FastAPI ataja este error y le avisa al frontend