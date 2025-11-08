# 🏎️ F1OpenCv — Detector de Límites de Pista

Aplicación de escritorio que utiliza **OpenCV** para determinar limites de pista en un circuito utilizando visión por computador. Cuenta con una interfaz gráfica construida con **CustomTkinter**.

Actualmente el sistema trabaja con vídeos de prueba, aunque puede adaptarse fácilmente para usar una cámara fija (requisito esencial: **la cámara debe permanecer completamente estática**).
<img width="1195" height="727" alt="image" src="https://github.com/user-attachments/assets/519eb1ac-6af9-47c8-a1ec-bd4ffd4197b3" />

<img width="892" height="679" alt="image" src="https://github.com/user-attachments/assets/e7edb03e-af5f-48bf-89cd-751a816a8a07" />

---

## ⭐ Principales Características

- **Doble Visualización:**  
  Muestra la cámara del vídeo original y una vista a elegir entre:
  - la máscara estática de la pista, o  
  - la máscara dinámica en tiempo real donde aparecen los coches.

- **Detección de Infracciones:**  
  Si el objeto sale de la zona válida y no es ruido, se detecta como **salida de pista**.

- **Panel de Alertas:**  
  El lateral derecho registra cada infracción indicando el minuto y segundo exacto.

- **Revisión de Incidentes:**  
  Al hacer clic en una alerta, se abre una ventana que muestra los frames exactos.  
  Para evitar saturación, los frames consecutivos de una misma infracción **se agrupan en una sola alerta**.

- **Configuración Externa:**  
  Parámetros como sensibilidad, umbrales y porcentaje de salida se ajustan desde el archivo `config.json`.

---

## ¿Cómo Funciona? (Visión General)

El sistema se divide en dos fases: **calibración inicial** y **detección continua**.

---

## 1️. Calibración y Creación de la Máscara

1. **Frame de Referencia**  
   Se toma el primer frame del vídeo como pista vacía.

2. **Filtro HSV**  
   Se transforma el frame a espacio **HSV**, más adecuado para segmentar colores bajo distintas iluminaciones.

3. **Máscara de Pista**  
   Con los valores calibrados se genera una **máscara binaria**:  
   - Blanco → asfalto / zona válida  
   - Negro → zona no válida

4. **Limpieza Morfológica**  
   Se aplican:  
   - **Erosión:** elimina ruido  
   - **Cierre:** rellena huecos  
   Resultado: una máscara final limpia y estable.

---

## 2️. Detección en Tiempo Real

1. **Sustracción de Fondo**  
   Cada nuevo frame se resta del frame de referencia para aislar objetos en movimiento (coches).

2. **Cálculo de Posición**  
   La máscara del coche se superpone sobre la máscara de la pista.

3. **Veredicto**  
   Se calcula el **porcentaje de píxeles del coche dentro de pista**.

4. **Alerta**  
   Si dicho porcentaje cae por debajo de un umbral (ej. 5%):  
   - Se marca como **infracción**  
   - El coche se colorea de rojo  
   - Se registra el evento en el panel lateral

---

## 🚀 Cómo Ejecutar el Proyecto

1. Clona o descarga el repositorio.  
2. (Opcional) Crea y activa un entorno virtual.  
3. Instala las dependencias ejecutando:
```bash
pip install -r requirements.txt
```
4. Asegúrate de que la ruta al vídeo (`VIDEO_PATH`) en el **main** de `GUI.py` apunta a tu archivo.  
5. Ejecuta la interfaz principal con:
```bash
   python GUI.py
```

---

## 🛠️ Herramientas de Calibración Incluidas

Si vas a usar vídeos propios, seguramente necesitarás recalibrar los filtros. El repositorio incluye dos utilidades:

- **CalibradorHSV.py**  
  Permite ajustar los sliders de H, S y V para que la máscara detecte correctamente el asfalto.

- **morphCloseBar.py**  
  Permite modificar el tamaño del kernel de **Cierre Morfológico** para rellenar huecos de la máscara sin deformarla.
