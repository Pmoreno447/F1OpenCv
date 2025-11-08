import customtkinter as ctk
from tkinter import Toplevel, messagebox
from PIL import Image, ImageTk, ImageDraw, ImageFont # Importar ImageDraw y ImageFont
import cv2
import numpy as np # Necesario para la conversión de imagen
import time
from Detector import DetectorDeVideo # Importa la clase gestora del otro archivo

# --- CONFIGURACIÓN DE APARIENCIA (Placeholder) ---
PLACEHOLDER_COLOR = "gray40" 


try:
    # Intenta usar una fuente común de Windows
    DEFAULT_FONT = ImageFont.truetype("arial.ttf", 18)
except IOError:
    # Fuente de reserva si no se encuentra arial.ttf
    DEFAULT_FONT = ImageFont.load_default() 

# --- CONSTANTE: Color de fondo oscuro de Customtkinter ---
CTK_BACKGROUND_HEX = "#212121" 

class DetectorGUI(ctk.CTk):
    
    def __init__(self, detector):
        super().__init__()
        self.title("Detector de Salida de Pista F1")
        self.geometry("1200x700")
        self.grid_columnconfigure((0, 1), weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.detector = detector # Instancia del detector de vídeo
        
        # Variables de estado
        self.modo_visualizacion = ctk.StringVar(value="Pista con Coche") 
        self.infracciones_registradas = []

        # --- NUEVAS VARIABLES PARA AGRUPAR FRAMES DE UNA INFRACCIÓN ---
        self.infraccion_activa = False
        self.infraccion_frames = []
        self.infraccion_inicio_t = None
        self.infraccion_window_s = 1.0  # duración de agrupación en segundos
        
        # --- Configuración de Widgets ---
        self._setup_widgets()
        
        # Iniciar el bucle de vídeo
        self._start_video_loop()

    
    def _setup_widgets(self):
        
        # --- COLUMNA 0 (IZQUIERDA: VISUALIZACIÓN) ---
        viz_frame = ctk.CTkFrame(self)
        viz_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        viz_frame.grid_rowconfigure(0, weight=1, uniform="a")
        viz_frame.grid_rowconfigure(1, weight=1, uniform="a")
        viz_frame.grid_columnconfigure(0, weight=1)
        
        # Panel superior: Vídeo Real (Cámara Principal)
        self.lbl_video_real = ctk.CTkLabel(viz_frame, text="CÁMARA REAL", 
                                           fg_color=PLACEHOLDER_COLOR, corner_radius=5)
        self.lbl_video_real.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        
        # Panel inferior: Máscara/Vista seleccionada
        self.lbl_vista_seleccionada = ctk.CTkLabel(viz_frame, text="VISTA SELECCIONADA: Pista con Coche", 
                                                    fg_color=PLACEHOLDER_COLOR, corner_radius=5)
        self.lbl_vista_seleccionada.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        
        # --- COLUMNA 1 (DERECHA: CONTROLES Y ALERTAS) ---
        control_frame = ctk.CTkFrame(self)
        control_frame.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        control_frame.grid_columnconfigure(0, weight=1)
        
        # 1. Botones de Modo de Vista (Ahora es la sección 1)
        ctk.CTkLabel(control_frame, text="1. Modo de Visualización:", font=("Arial", 14, "bold")).grid(row=0, column=0, padx=10, pady=(10, 0), sticky="w")
        
        btn_frame = ctk.CTkFrame(control_frame, fg_color="transparent")
        btn_frame.grid(row=1, column=0, padx=10, pady=5, sticky="ew")
        btn_frame.grid_columnconfigure((0, 1), weight=1) 
        
        ctk.CTkButton(btn_frame, text="Solo Pista", command=lambda: self._set_view_mode("Solo Pista")).grid(row=0, column=0, padx=5, sticky="ew")
        ctk.CTkButton(btn_frame, text="Pista con Coche", command=lambda: self._set_view_mode("Pista con Coche")).grid(row=0, column=1, padx=5, sticky="ew")
        
        # 2. Alertas de Salida de Pista (Ahora es la sección 2)
        ctk.CTkLabel(control_frame, text="2. Avisos de Salida de Pista:", font=("Arial", 14, "bold")).grid(row=2, column=0, padx=10, pady=(10, 2), sticky="w")

        # El marco desplazable que contendrá los botones/alertas
        self.scroll_frame_alertas = ctk.CTkScrollableFrame(control_frame, label_text="Eventos", height=200)
        self.scroll_frame_alertas.grid(row=3, column=0, padx=10, pady=(0, 10), sticky="nsew")
        self.scroll_frame_alertas.grid_columnconfigure(0, weight=1)
        
        # Damos peso a la fila del scroll_frame para que ocupe el espacio restante
        control_frame.grid_rowconfigure(3, weight=1)


        # Contador de botones para la lista
        self.alert_button_count = 0

    def _add_alert_button(self, time_str, frame_img):
        """Añade un botón de alerta al scroll_frame_alertas (método legacy)."""
        
        button_text = f"⚠️ INF: Salida en {time_str}"
        
        btn = ctk.CTkButton(self.scroll_frame_alertas, 
                            text=button_text, 
                            fg_color="#CC0000", # Rojo oscuro para la alerta
                            hover_color="#AA0000",
                            command=lambda t=time_str, f=frame_img: self._open_alert_window(t, f))
        
        btn.grid(row=self.alert_button_count, column=0, padx=5, pady=3, sticky="ew")
        self.alert_button_count += 1
        
        self.infracciones_registradas.append({'time': time_str, 'frame_img': frame_img})


    def _add_alert_button_grouped(self, time_str, frames):
        """Añade una única notificación que representa múltiples frames capturados
        durante un periodo de infracción."""
        button_text = f"⚠️ INF: Salida en {time_str} (x{len(frames)} frames)"

        btn = ctk.CTkButton(self.scroll_frame_alertas,
                            text=button_text,
                            fg_color="#CC0000",
                            hover_color="#AA0000",
                            command=lambda t=time_str, f=frames: self._open_alert_window_grouped(t, f))

        btn.grid(row=self.alert_button_count, column=0, padx=5, pady=3, sticky="ew")
        self.alert_button_count += 1

        # Guardamos la infracción agrupada (time, frames)
        self.infracciones_registradas.append({'time': time_str, 'frames': frames})


    def _set_view_mode(self, mode):
        """Cambia el modo de visualización en el panel inferior."""
        self.modo_visualizacion.set(mode)
        # El texto del label se actualizará en _process_video_frame

    def _on_alert_click(self, event):
        """Este método ya no es necesario ya que el botón llama a _add_alert_button directamente."""
        pass

    def _open_alert_window(self, time_str, frame_img):
        """Muestra el frame de la infracción en una ventana Toplevel."""
        if hasattr(self, 'alert_window') and self.alert_window.winfo_exists():
             self.alert_window.destroy()

        self.alert_window = ctk.CTkToplevel(self) # <-- CORRECCIÓN a CTkToplevel
        self.alert_window.configure(fg_color="#000000") # <-- CORRECCIÓN color negro
        self.alert_window.title(f"DETALLE DE INFRACCIÓN: {time_str}")
        self.alert_window.geometry("800x500")
        
        # Convertir el frame de OpenCV a PhotoImage para Tkinter
        img_rgb = cv2.cvtColor(frame_img, cv2.COLOR_BGR2RGB)
        img_pil = Image.fromarray(img_rgb)
        
        # Redimensionar la imagen si es necesario para que quepa en la ventana de alerta
        w, h = img_pil.size
        ratio = min(780 / w, 480 / h)
        img_pil = img_pil.resize((int(w * ratio), int(h * ratio)), Image.Resampling.LANCZOS)
        
        photo = ImageTk.PhotoImage(image=img_pil)
        
        lbl = ctk.CTkLabel(self.alert_window, text="", image=photo)
        lbl.image = photo # Referencia necesaria para evitar que Python borre la imagen
        lbl.pack(fill="both", expand=True, padx=10, pady=10)
        
        ctk.CTkLabel(self.alert_window, text=f"*** SALIDA DETECTADA EN {time_str} ***").pack(pady=5)
        
        self.alert_window.grab_set()

    def _open_alert_window_grouped(self, time_str, frames):
        """Abre UNA ventana con controles para navegar entre los frames capturados
        durante la infracción agrupada."""
        # Si hay una ventana abierta, destruirla (queremos solo UNA ventana)
        if hasattr(self, 'alert_window') and self.alert_window.winfo_exists():
            self.alert_window.destroy()

        # --- CORRECCIONES CLAVE ---
        self.alert_window = ctk.CTkToplevel(self) # <-- 1. Usar CTkToplevel
        self.alert_window.configure(fg_color="#000000") # <-- 2. Poner fondo negro
        # ---
        
        self.alert_window.title(f"DETALLE DE INFRACCIÓN: {time_str}")
        self.alert_window.geometry("900x650")

        # Variables del grupo
        self.group_frames = frames
        self.group_index = 0

        # Label donde se mostrará la imagen
        # 3. Asegurarse de que el label de la imagen también tenga fondo negro
        self.group_img_label = ctk.CTkLabel(self.alert_window, text="", fg_color="#000000")
        self.group_img_label.pack(fill="both", expand=True, padx=10, pady=10)

        # Marco de controles
        control_frame = ctk.CTkFrame(self.alert_window, fg_color="transparent") # Transparente sobre negro
        control_frame.pack(pady=6)

        btn_prev = ctk.CTkButton(control_frame, text="⟵ Anterior", command=self._group_prev)
        btn_prev.grid(row=0, column=0, padx=10)

        btn_next = ctk.CTkButton(control_frame, text="Siguiente ⟶", command=self._group_next)
        btn_next.grid(row=0, column=1, padx=10)

        # Botón para cerrar
        btn_close = ctk.CTkButton(control_frame, text="Cerrar", command=self.alert_window.destroy)
        btn_close.grid(row=0, column=2, padx=10)

        # Texto indicador
        self.group_info_label = ctk.CTkLabel(self.alert_window, text="")
        self.group_info_label.pack(pady=(4,10))

        self._group_show_image()

        self.alert_window.grab_set()

    def _group_show_image(self):
        """Muestra la imagen actual del grupo en la ventana de alerta."""
        if not hasattr(self, 'group_frames') or len(self.group_frames) == 0:
            return

        frame = self.group_frames[self.group_index]
        img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img_pil = Image.fromarray(img_rgb)

        # Ajustar la imagen al tamaño disponible (dejamos margen)
        w, h = img_pil.size
        max_w, max_h = 860, 480
        ratio = min(max_w / w, max_h / h, 1.0)
        img_pil = img_pil.resize((int(w * ratio), int(h * ratio)), Image.Resampling.LANCZOS)

        self.group_photo = ImageTk.PhotoImage(img_pil)
        self.group_img_label.configure(image=self.group_photo, text="")
        self.group_img_label.image = self.group_photo

        # Actualizar info
        self.group_info_label.configure(text=f"Imagen {self.group_index+1}/{len(self.group_frames)}")

    def _group_prev(self):
        if self.group_index > 0:
            self.group_index -= 1
            self._group_show_image()

    def _group_next(self):
        if self.group_index < len(self.group_frames) - 1:
            self.group_index += 1
            self._group_show_image()

    def _start_video_loop(self):
        """Inicia el bucle de procesamiento de vídeo frame a frame."""
        self._process_video_frame()

    def _process_video_frame(self):
        """Lee un frame, lo procesa y actualiza la GUI."""
        start = time.time()

        results = self.detector.get_next_frame_data()
        if results is None:
            return self.after(1, self._process_video_frame)

        # --- Actualizar ambas ventanas ---
        frame_real_bgr = results['frame_real']
        frame_mascara_bgr = results['frame_mascara']

        self._update_label_image(self.lbl_video_real, frame_real_bgr, 
                                 "CÁMARA REAL")

        vista_actual = self.modo_visualizacion.get()
        if vista_actual == "Solo Pista":
            self._update_label_image(self.lbl_vista_seleccionada,
                                     self.detector.mascara_pista,
                                     "VISTA SELECCIONADA: Solo Pista")
        else:
            self._update_label_image(self.lbl_vista_seleccionada,
                                     frame_mascara_bgr,
                                     f"VISTA SELECCIONADA: Pista con Coche | En Pista: {results['porcentaje_en_pista']:.1f}%")

        # --- GESTIÓN AGRUPADA DE ALERTAS ---
        if results['infraccion_detectada']:
            # Si no hay una infracción activa iniciamos la ventana de agrupación
            if not self.infraccion_activa:
                self.infraccion_activa = True
                self.infraccion_inicio_t = time.time()
                self.infraccion_frames = []

            # Guardamos el frame detectado
            self.infraccion_frames.append(frame_real_bgr.copy())

            # Si excede el umbral temporal creamos la notificación agrupada
            if time.time() - self.infraccion_inicio_t >= self.infraccion_window_s:
                # Generar notificación agrupada
                alerta_time = results['video_time']
                self._add_alert_button_grouped(alerta_time, self.infraccion_frames.copy())

                # Resetear variables de agrupación
                self.infraccion_activa = False
                self.infraccion_frames = []
                self.infraccion_inicio_t = None

        else:
            # Si no hay detección, y estábamos en una infracción activa pero no se llegó
            # al tiempo mínimo, cerramos el periodo y creamos una notificación si hay frames
            if self.infraccion_activa:
                elapsed = time.time() - self.infraccion_inicio_t
                if elapsed > 0 and len(self.infraccion_frames) > 0:
                    alerta_time = results['video_time']
                    self._add_alert_button_grouped(alerta_time, self.infraccion_frames.copy())

                # Resetear
                self.infraccion_activa = False
                self.infraccion_frames = []
                self.infraccion_inicio_t = None

        # --- Sincronización precisa ---
        process_time = (time.time() - start) * 1000   # ms
        delay = max(1, int(self.detector.delay_ms - process_time))

        self.after(delay, self._process_video_frame)


    def _update_label_image(self, label, frame_bgr, text):
        """
        Convierte el frame de OpenCV a PhotoImage, lo REDIMENSIONA (ESTIRA) para que
        ocupe todo el Label y añade el texto en una banda inferior.
        """
        
        label.update_idletasks()
        label_width = label.winfo_width()
        label_height = label.winfo_height()
        
        if label_width < 10 or label_height < 10:
            return

        # 1. Convertir a RGB y PIL Image
        is_grayscale = len(frame_bgr.shape) == 2
        
        if not is_grayscale:
            img_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        else:
            img_rgb = frame_bgr
            
        img_pil = Image.fromarray(img_rgb)

        # 2. Calcular área de dibujo y banda de texto
        band_height = 30
        
        # El área de dibujo de la imagen será la altura total menos la banda de texto
        draw_height = label_height - band_height
        
        # 3. Crear el lienzo final del tamaño exacto del Label (incluyendo la banda de texto)
        final_canvas = Image.new('RGB', (label_width, label_height), color=CTK_BACKGROUND_HEX)
        
        # Convertir y redimensionar la imagen del vídeo/máscara
        if is_grayscale:
            img_pil = img_pil.convert('L').convert('RGB')
        
        # --- AJUSTE CLAVE (STRETCH) ---
        # Redimensionamos la imagen para que llene el área de dibujo EXACTAMENTE
        # Esto estirará la imagen si es necesario, pero ambos paneles serán idénticos.
        img_pil = img_pil.resize((label_width, draw_height), Image.Resampling.LANCZOS)
        
        # 4. Pegar la imagen en la esquina superior del lienzo
        # Ya no se necesita centrar, pues la imagen tiene el tamaño exacto
        final_canvas.paste(img_pil, (0, 0)) 
        
        # 5. Dibujar la banda de texto en la parte inferior
        draw = ImageDraw.Draw(final_canvas)
        text_bbox = draw.textbbox((0, 0), text, font=DEFAULT_FONT)
        text_w = text_bbox[2] - text_bbox[0]
        
        # Dibujar fondo de banda negra (para contraste)
        draw.rectangle([0, label_height - band_height, label_width, label_height], fill="#333333")
        
        # Dibujar texto centrado en la banda
        text_x = (label_width - text_w) // 2
        text_y = label_height - band_height + (band_height - (text_bbox[3] - text_bbox[1])) // 2 - 3 # Ajuste fino

        draw.text((text_x, text_y), text, fill="white", font=DEFAULT_FONT)


        # 6. Convertir a PhotoImage y actualizar
        photo = ImageTk.PhotoImage(image=final_canvas)
        label.configure(image=photo, text="", fg_color="transparent") # El texto ya está en la imagen
        label.image = photo 

# --- 5. FUNCIÓN MAIN ---

def main():
    # --- CONFIGURACIÓN GLOBAL ---
    # CORRECCIÓN DE SYNTAX WARNING: Usamos 'r' para la raw string

    VIDEO_PATH = r'Imagenes\Suzuka.mp4'
    #VIDEO_PATH = r'Imagenes\RbRingT10b.mp4'

    try:
        # 1. Inicializar el Detector (toda la lógica de OpenCV)
        # AJUSTE: Se reintroduce ancho_ventana
        detector = DetectorDeVideo(VIDEO_PATH, ancho_ventana=600) 
        
        # 2. Inicializar la Interfaz Gráfica
        app = DetectorGUI(detector)
        app.mainloop()
        
    except FileNotFoundError as e:
        messagebox.showerror("Error de Archivo", f"Error: {e}\nAsegúrate de que la ruta al vídeo es correcta y que el archivo existe.")
    except Exception as e:
        messagebox.showerror("Error General", f"Ocurrió un error inesperado: {e}")
        print(f"Error fatal: {e}")

if __name__ == "__main__":
    main()