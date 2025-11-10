import customtkinter as ctk
from tkinter import Toplevel, messagebox
from PIL import Image, ImageTk, ImageDraw, ImageFont
import cv2
import numpy as np
import time
import threading
from Detector import DetectorDeVideo

PLACEHOLDER_COLOR = "gray40"

try:
    DEFAULT_FONT = ImageFont.truetype("arial.ttf", 18)
except IOError:
    DEFAULT_FONT = ImageFont.load_default()

CTK_BACKGROUND_HEX = "#212121"


# ===============================================================
#                     GUI PRINCIPAL (MULTITHREAD)
# ===============================================================

class DetectorGUI(ctk.CTk):

    def __init__(self, detector):
        super().__init__()
        self.title("Detector de Salida de Pista F1")
        self.geometry("1200x700")
        
        # Columna 0 (vídeo): Flexible, tomará todo el espacio extra
        self.grid_columnconfigure(0, weight=1)
        
        # Columna 1 (panel derecha): Fija, con un ancho de 300px
        self.grid_columnconfigure(1, weight=0, minsize=250) 
        
        self.grid_rowconfigure(0, weight=1)

        # Detector (OpenCV)
        self.detector = detector

        # Último resultado del hilo de vídeo
        self.latest_results = None

        # Estado de vista
        self.modo_visualizacion = ctk.StringVar(value="Pista con Coche")
        self.infracciones_registradas = []

        # Agrupación de infracciones
        self.infraccion_activa = False
        self.infraccion_frames = []
        self.infraccion_inicio_t = None
        self.infraccion_window_s = 1.0

        # Widgets de la GUI
        self._setup_widgets()

        # Iniciar hilos
        self._start_threads()


    # ===============================================================
    #                     SETUP DE WIDGETS
    # ===============================================================
    def _setup_widgets(self):

        # Columna izquierda
        viz_frame = ctk.CTkFrame(self)
        viz_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        viz_frame.grid_rowconfigure(0, weight=1)
        viz_frame.grid_rowconfigure(1, weight=1)
        viz_frame.grid_columnconfigure(0, weight=1)

        # Labels principales
        self.lbl_video_real = ctk.CTkLabel(
            viz_frame, text="CÁMARA REAL", fg_color=PLACEHOLDER_COLOR
        )
        self.lbl_video_real.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

        self.lbl_vista_seleccionada = ctk.CTkLabel(
            viz_frame, text="VISTA SELECCIONADA: Pista con Coche",
            fg_color=PLACEHOLDER_COLOR
        )
        self.lbl_vista_seleccionada.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)

        # ✅ Forzar que NO se adapten al contenido
        self.lbl_video_real.grid_propagate(False)
        self.lbl_vista_seleccionada.grid_propagate(False)

        # ✅ Forzar alturas iguales al 50% del contenedor
        # (lo hacemos tras update_idletasks para que Tk calcule tamaños)
        self.update_idletasks()
        total_height = viz_frame.winfo_height()
        half_height = total_height // 2

        self.lbl_video_real.configure(height=half_height)
        self.lbl_vista_seleccionada.configure(height=half_height)

        # -------------------------------------------------------
        # Columna derecha (todo igual que antes)
        # -------------------------------------------------------

        control_frame = ctk.CTkFrame(self)
        control_frame.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        control_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(control_frame, text="1. Modo de Visualización:",
                    font=("Arial", 14, "bold")).grid(row=0, column=0, padx=10, pady=5, sticky="w")

        btn_frame = ctk.CTkFrame(control_frame, fg_color="transparent")
        btn_frame.grid(row=1, column=0, padx=10, pady=5, sticky="ew")
        btn_frame.grid_columnconfigure((0, 1), weight=1)

        ctk.CTkButton(btn_frame, text="Solo Pista",
                    command=lambda: self._set_view_mode("Solo Pista")).grid(row=0, column=0, padx=5, sticky="ew")

        ctk.CTkButton(btn_frame, text="Pista con Coche",
                    command=lambda: self._set_view_mode("Pista con Coche")).grid(row=0, column=1, padx=5, sticky="ew")

        ctk.CTkLabel(control_frame, text="2. Avisos de Salida de Pista:",
                    font=("Arial", 14, "bold")).grid(row=2, column=0, padx=10, pady=5, sticky="w")

        self.scroll_frame_alertas = ctk.CTkScrollableFrame(control_frame, label_text="Eventos", height=250)
        self.scroll_frame_alertas.grid(row=3, column=0, padx=10, pady=10, sticky="nsew")
        control_frame.grid_rowconfigure(3, weight=1)

        self.alert_button_count = 0



    # ===============================================================
    #                 HILO DE VÍDEO
    # ===============================================================

    def _video_thread(self):
        """
        Este hilo se ejecuta a máxima velocidad sin tocar Tkinter.
        Produce frames y solo guarda el último disponible.
        """
        TARGET_FPS = 25
        TARGET_DELAY = 1.0 / TARGET_FPS   # tiempo entre frames

        while True:
            start = time.time()

            results = self.detector.get_next_frame_data()
            if results is not None:
                self.latest_results = results

            elapsed = time.time() - start
            sleep_time = TARGET_DELAY - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)


    # ===============================================================
    #        HILO PRINCIPAL TKINTER (25–30 FPS, fluido y estable)
    # ===============================================================

    def _start_threads(self):
        threading.Thread(target=self._video_thread, daemon=True).start()
        self._tk_loop()


    def _tk_loop(self):
        """
        Se ejecuta ~30 FPS. Pinta los últimos frames procesados.
        """
        if self.latest_results is not None:
            self._render_latest_results(self.latest_results)

        self.after(30, self._tk_loop)   # ~33 FPS estables para Tkinter


    # ===============================================================
    #               RENDER DE FRAME (TKINTER)
    # ===============================================================

    def _render_latest_results(self, results):

        frame_real = results["frame_real"]
        frame_mascara = results["frame_mascara"]

        self._update_label_image(
            self.lbl_video_real, frame_real, "CÁMARA REAL"
        )

        if self.modo_visualizacion.get() == "Solo Pista":
            self._update_label_image(
                self.lbl_vista_seleccionada,
                self.detector.mascara_pista,
                "VISTA SELECCIONADA: Solo Pista"
            )
        else:
            self._update_label_image(
                self.lbl_vista_seleccionada,
                frame_mascara,
                f"VISTA SELECCIONADA: Pista con Coche | En Pista: {results['porcentaje_en_pista']:.1f}%"
            )

        # --------------------------
        # Agrupación de infracciones
        # --------------------------

        if results["infraccion_detectada"]:

            if not self.infraccion_activa:
                self.infraccion_activa = True
                self.infraccion_inicio_t = time.time()
                self.infraccion_frames = []

            self.infraccion_frames.append(frame_real.copy())

            if time.time() - self.infraccion_inicio_t >= self.infraccion_window_s:
                self._add_alert_button_grouped(results["video_time"],
                                               self.infraccion_frames.copy())

                self.infraccion_activa = False
                self.infraccion_frames = []

        else:
            if self.infraccion_activa and self.infraccion_frames:
                self._add_alert_button_grouped(results["video_time"],
                                               self.infraccion_frames.copy())

            self.infraccion_activa = False
            self.infraccion_frames = []


    # ===============================================================
    #                BOTONES DE ALERTAS AGRUPADAS
    # ===============================================================

    def _add_alert_button_grouped(self, time_str, frames):
        text = f"⚠️ INF: Salida en {time_str} (x{len(frames)} frames)"
        btn = ctk.CTkButton(self.scroll_frame_alertas, text=text,
                            fg_color="#CC0000", hover_color="#AA0000",
                            command=lambda t=time_str, f=frames: self._open_alert_window_grouped(t, f))

        btn.grid(row=self.alert_button_count, column=0, padx=5, pady=3, sticky="ew")
        self.alert_button_count += 1


    # ===============================================================
    #                    VENTANA AGRUPADA
    # ===============================================================

    def _close_group_window(self):
        try:
            if hasattr(self, "alert_window") and self.alert_window.winfo_exists():
                self.alert_window.destroy()
        except:
            pass

        self.group_frames = []
        self.group_img_label = None
        self.group_info_label = None


    def _open_alert_window_grouped(self, time_str, frames):

        if hasattr(self, 'alert_window') and self.alert_window.winfo_exists():
            self.alert_window.destroy()

        self.alert_window = ctk.CTkToplevel(self)
        self.alert_window.title(f"Infracción: {time_str}")
        self.alert_window.geometry("900x650")
        self.alert_window.configure(fg_color="black")

        self.group_frames = frames
        self.group_index = 0

        self.group_img_label = ctk.CTkLabel(self.alert_window, text="", fg_color="black")
        self.group_img_label.pack(fill="both", expand=True, padx=10, pady=10)

        ctrl = ctk.CTkFrame(self.alert_window, fg_color="transparent")
        ctrl.pack()

        ctk.CTkButton(ctrl, text="⟵ Anterior",
                      command=self._group_prev).grid(row=0, column=0, padx=10)

        ctk.CTkButton(ctrl, text="Siguiente ⟶",
                      command=self._group_next).grid(row=0, column=1, padx=10)

        ctk.CTkButton(ctrl, text="Cerrar",
                      command=self._close_group_window).grid(row=0, column=2, padx=10)

        self.group_info_label = ctk.CTkLabel(self.alert_window, text="")
        self.group_info_label.pack()

        self._group_show_image()
        self.alert_window.grab_set()


    # ------------------------------------------------------------
    # Navegación ventanas agrupadas
    # ------------------------------------------------------------

    def _group_show_image(self):

        if not self.group_frames or self.group_img_label is None:
            return

        frame = self.group_frames[self.group_index]
        img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img_pil = Image.fromarray(img_rgb)

        w, h = img_pil.size
        ratio = min(860 / w, 480 / h)
        img_pil = img_pil.resize((int(w*ratio), int(h*ratio)), Image.Resampling.LANCZOS)

        self.group_photo = ImageTk.PhotoImage(img_pil)

        self.group_img_label.configure(image=self.group_photo)
        self.group_img_label.image = self.group_photo

        self.group_info_label.configure(
            text=f"Imagen {self.group_index+1}/{len(self.group_frames)}"
        )

    def _group_prev(self):
        if self.group_index > 0:
            self.group_index -= 1
            self._group_show_image()

    def _group_next(self):
        if self.group_index < len(self.group_frames)-1:
            self.group_index += 1
            self._group_show_image()


    # ===============================================================
    #                 ACTUALIZADOR DE IMÁGENES
    # ===============================================================

    def _update_label_image(self, label, frame_bgr, text):

        label.update_idletasks()
        w = label.winfo_width()
        h = label.winfo_height()

        if w < 20 or h < 20:
            return

        img_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        img_pil = Image.fromarray(img_rgb)

        band = 30
        draw_h = h - band

        final = Image.new("RGB", (w, h), color=CTK_BACKGROUND_HEX)

        img_pil = img_pil.resize((w, draw_h), Image.Resampling.LANCZOS)
        final.paste(img_pil, (0, 0))

        draw = ImageDraw.Draw(final)
        draw.rectangle([0, h-band, w, h], fill="#333333")

        bbox = draw.textbbox((0, 0), text, font=DEFAULT_FONT)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]

        draw.text(((w-tw)//2, h-band + (band-th)//2 - 3),
                  text, fill="white", font=DEFAULT_FONT)

        photo = ImageTk.PhotoImage(final)
        label.configure(image=photo, text="")
        label.image = photo


# ===============================================================
# MAIN
# ===============================================================

def main():
    VIDEO_PATH = r"Imagenes\RbRingT10.mp4"
    #VIDEO_PATH = r"Imagenes\RbRingT10b.mp4"
    #VIDEO_PATH = r"Imagenes\Suzuka.mp4"

    try:
        detector = DetectorDeVideo(VIDEO_PATH, ancho_ventana=600)
        app = DetectorGUI(detector)
        app.mainloop()

    except FileNotFoundError as e:
        messagebox.showerror("Error Archivo", f"{e}")

    except Exception as e:
        messagebox.showerror("Error General", str(e))
        print("Error fatal:", e)


if __name__ == "__main__":
    main()