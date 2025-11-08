import cv2
import numpy as np
import time
import json
import sys

# --- 1. MÓDULO DE CALIBRACIÓN (crear_mascara_pista) ---

def crear_mascara_pista(imagen_bgr):
    """
    Toma una imagen BGR y devuelve la máscara de pista final limpia.
    Los valores de los filtros fueron determinados mediante CalibradorHSV.py y morphCloseBar.py
    """
    # Convertir a HSV
    hsv = cv2.cvtColor(imagen_bgr, cv2.COLOR_BGR2HSV)

    # --- 1. PARÁMETROS DE CALIBRACIÓN FIJOS ---
    lim_inf_pista = np.array([0, 0, 33])
    lim_sup_pista = np.array([180, 52, 124])
    kernel_erosion_size = 4  # (Se convertirá en 5)
    kernel_cierre_size = 10 # (Se convertirá en 11)
    
    # --- 2. Creación de la Máscara Inicial ---
    mascara_inicial = cv2.inRange(hsv, lim_inf_pista, lim_sup_pista)

    # --- 3. Limpieza (EROSIÓN) ---
    # Aunque ahora los valores sean definitivos, en caso de que cambiasen y pusiesemos un valor par,
    # nos aseguramos de que esto no ocurre. Por eso esta rama.
    if kernel_erosion_size % 2 == 0 and kernel_erosion_size > 0: kernel_erosion_size += 1 
    if kernel_erosion_size > 1:
        kernel_erosion = np.ones((kernel_erosion_size, kernel_erosion_size), np.uint8)
        mascara_erosionada = cv2.erode(mascara_inicial, kernel_erosion, iterations=1)
    else:
        mascara_erosionada = mascara_inicial
        
    # --- 4. Limpieza (CIERRE) ---
    # Aunque ahora los valores sean definitivos, en caso de que cambiasen y pusiesemos un valor par,
    # nos aseguramos de que esto no ocurre. Por eso esta rama.
    if kernel_cierre_size % 2 == 0 and kernel_cierre_size > 0: kernel_cierre_size += 1
    if kernel_cierre_size > 1:
        kernel_cierre = np.ones((kernel_cierre_size, kernel_cierre_size), np.uint8)
        mascara_final_limpia = cv2.morphologyEx(mascara_erosionada, cv2.MORPH_CLOSE, kernel_cierre, iterations=1)
    else:
        mascara_final_limpia = mascara_erosionada

    return mascara_final_limpia


# --- FUNCIÓN DE REESCALADO ---
def reescalar_frame(frame, ancho_fijo=600):
    """
    Reescala el frame a un ancho fijo (ancho_fijo), manteniendo la proporción.
    Esto asegura que todos los frames tengan las mismas dimensiones de entrada.
    """
    altura, anchura = frame.shape[:2]
    
    # Calcular la escala necesaria para alcanzar el ancho_fijo (600px)
    escala = ancho_fijo / anchura
    dim = (ancho_fijo, int(altura * escala))
    
    # Usamos interpolación INTER_AREA para reducir, e INTER_LINEAR para aumentar
    inter = cv2.INTER_AREA if escala < 1 else cv2.INTER_LINEAR
    
    return cv2.resize(frame, dim, interpolation=inter)


# --- 2. MÓDULO DE PROCESAMIENTO DE UN SOLO FRAME (analizar_frame) ---

def analizar_frame(frame_actual, fondo_vacio, mascara_pista, UMBRAL_BG_SUB, UMBRAL_RUIDO_COCHE, UMBRAL_SALIDA, mascara_pista_bgr):
    """Procesa un solo frame y devuelve los resultados de visualización y detección."""
    
    frame_display = frame_actual.copy()
    
    # --- Detectar el Coche (LÓGICA SIMPLE) ---
    diff = cv2.absdiff(fondo_vacio, frame_actual)
    gray_diff = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)
    
    _, mascara_coche = cv2.threshold(gray_diff, UMBRAL_BG_SUB, 255, cv2.THRESH_BINARY)
    
    kernel_coche = np.ones((5, 5), np.uint8)
    mascara_coche = cv2.morphologyEx(mascara_coche, cv2.MORPH_CLOSE, kernel_coche, iterations=2)
    
    # --- Lógica de Decisión ---
    total_pixeles_coche = cv2.countNonZero(mascara_coche)
    visualizacion_combinada = mascara_pista_bgr.copy()
    
    porcentaje_en_pista = 0.0
    infraccion_detectada = False
    
    if total_pixeles_coche < UMBRAL_RUIDO_COCHE:
        # No hay coche o es ruido. Devolvemos None.
        return None
        
    # Si detectamos coche:
    
    # Lo dibujamos en verde sobre la máscara.
    visualizacion_combinada[mascara_coche > 0] = [0, 255, 0] # Color VERDE BGR
    
    # Comparamos la máscara del coche con la máscara de la pista
    coche_en_pista = cv2.bitwise_and(mascara_pista, mascara_coche)
    total_pixeles_coche_en_pista = cv2.countNonZero(coche_en_pista)
    porcentaje_en_pista = (total_pixeles_coche_en_pista / total_pixeles_coche) * 100

    # --- Lógica de Alerta ---
    
    if porcentaje_en_pista < UMBRAL_SALIDA:
        infraccion_detectada = True
        visualizacion_combinada[mascara_coche > 0] = [0, 0, 255] # Dibujar coche en ROJO

    # Dibujar texto en el frame real
    estado = "¡¡¡SALIDA DE PISTA!!!" if infraccion_detectada else "En Pista"
    color_texto = (0, 0, 255) if infraccion_detectada else (0, 255, 0)
    
    # cv2.putText(frame_display, estado, (50, 50), cv2.FONT_HERSHEY_SIMPLEX,
    #             1, (255,255,255), 3, cv2.LINE_AA)
    # cv2.putText(frame_display, estado, (50, 50), cv2.FONT_HERSHEY_SIMPLEX,
    #             1, color_texto, 2, cv2.LINE_AA)

    # cv2.putText(frame_display, f"En Pista: {porcentaje_en_pista:.1f}%", (50, 100),
    #             cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2, cv2.LINE_AA)
                    
    return {
        'frame_real': frame_display,
        'frame_mascara': visualizacion_combinada,
        'infraccion_detectada': infraccion_detectada,
        'porcentaje_en_pista': porcentaje_en_pista
    }

# --- 3. CLASE GESTORA DEL DETECTOR (Para la Interfaz) ---

class DetectorDeVideo:
    
    # AJUSTE: Se reintroduce ancho_ventana
    def __init__(self, video_path, ancho_ventana=600, ruta_config='config.json'):
        # 1. Cargar datos del archivo
        try:
            with open(ruta_config, 'r') as f:
                config_data = json.load(f)
        except FileNotFoundError:
            print(f"Error: Archivo de configuración '{ruta_config}' no encontrado.")
            sys.exit(1)

        # --- CONFIGURACIÓN ---
        self.ANCHO_VENTANA = ancho_ventana
        self.UMBRAL_SALIDA = config_data.get("UMBRAL_SALIDA")
        self.UMBRAL_BG_SUB = config_data.get("UMBRAL_BG_SUB")
        self.UMBRAL_RUIDO_COCHE = config_data.get("UMBRAL_RUIDO_COCHE")
        
        # --- Inicialización de Video ---
        self.video_path = video_path
        self.cap = cv2.VideoCapture(video_path)
        if not self.cap.isOpened():
            raise FileNotFoundError(f"Error: No se pudo abrir el vídeo en {video_path}")

        self.fps = self.cap.get(cv2.CAP_PROP_FPS)
        if self.fps == 0: self.fps = 30
        self.delay_ms = int(1000 / self.fps) # Tiempo de espera para el after()

        # --- Variables de Estado ---
        ret, fondo_vacio = self.cap.read()
        if not ret: raise Exception("No se pudo leer el primer frame del vídeo.")
            
        # AJUSTE: Reescalamos el fondo al ancho fijo
        self.fondo_vacio = reescalar_frame(fondo_vacio, self.ANCHO_VENTANA)
        self.mascara_pista = crear_mascara_pista(self.fondo_vacio)
        self.mascara_pista_bgr = cv2.cvtColor(self.mascara_pista, cv2.COLOR_GRAY2BGR)
        
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0) # Reiniciamos el cursor de vídeo
        self.frame_count = 0

    def get_next_frame_data(self):
        """Lee un frame, lo procesa y devuelve los frames y resultados."""
        
        ret, frame = self.cap.read()

        if not ret:
            # Si termina el vídeo, reiniciamos (Bucle)
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            self.frame_count = 0
            ret, frame = self.cap.read()
            if not ret: return None
        
        self.frame_count += 1
        
        # AJUSTE: Reescalamos el frame actual al mismo ancho fijo
        frame_actual = reescalar_frame(frame, self.ANCHO_VENTANA)
        
        results = analizar_frame(frame_actual, self.fondo_vacio, self.mascara_pista, self.UMBRAL_BG_SUB, self.UMBRAL_RUIDO_COCHE, self.UMBRAL_SALIDA, self.mascara_pista_bgr)

        # Añadir tiempo de vídeo
        current_time_seconds = self.frame_count / self.fps
        minutes = int(current_time_seconds // 60)
        seconds = current_time_seconds % 60
        time_str = f"{minutes:02d}:{seconds:04.1f}s"
        
        if results:
            results['video_time'] = time_str
        else:
            # Devuelve un placeholder si no detecta coche, pero es necesario para la GUI
            results = {
                'frame_real': frame_actual,
                'frame_mascara': self.mascara_pista_bgr,
                'infraccion_detectada': False,
                'video_time': time_str,
                'porcentaje_en_pista': 100.0
            }
        
        return results