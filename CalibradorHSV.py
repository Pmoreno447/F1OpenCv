import cv2
import numpy as np

"""
Carga una imagen y nos permite determinar los valores
del filtro de colorr HSV y el valor del erode.
"""

# --- Función de 'callback' ---
def nada(x):
    pass

# --- Configuración Inicial ---
ruta_imagen = 'Imagenes/rb_ring16.jpg'
ancho_max_ventana = 800  # Para reescalar la imagen si es muy grande

# Cargar la imagen
imagen = cv2.imread(ruta_imagen)
if imagen is None:
    print(f"Error: No se pudo cargar la imagen en {ruta_imagen}")
    exit()

# Reescalar la imagen para que quepa en la pantalla
altura, anchura = imagen.shape[:2]
if anchura > ancho_max_ventana:
    escala = ancho_max_ventana / anchura
    dim = (ancho_max_ventana, int(altura * escala))
    imagen = cv2.resize(imagen, dim, interpolation=cv2.INTER_AREA)

# Convertir a HSV
hsv = cv2.cvtColor(imagen, cv2.COLOR_BGR2HSV)

# Crear la ventana para los controles (trackbars)
cv2.namedWindow('Controles HSV')
cv2.resizeWindow('Controles HSV', 600, 350) # Aumentamos el tamaño para el nuevo trackbar

# --- Crear los 6 Trackbars HSV ---
cv2.createTrackbar('H Min', 'Controles HSV', 0, 180, nada)
cv2.createTrackbar('H Max', 'Controles HSV', 180, 180, nada)
cv2.createTrackbar('S Min', 'Controles HSV', 0, 255, nada)
cv2.createTrackbar('S Max', 'Controles HSV', 255, 255, nada)
cv2.createTrackbar('V Min', 'Controles HSV', 0, 255, nada)
cv2.createTrackbar('V Max', 'Controles HSV', 255, 255, nada)

# --- Crear el trackbar para determinar el erode ---
cv2.createTrackbar('Kernel Erosion', 'Controles HSV', 1, 15, nada)


print("\n--- Calibrador HSV con Erosión ---")
print("Ajusta los deslizadores HSV para aislar el color.")
print("Luego ajusta 'Kernel Erosion' para limpiar el ruido.")
print("Presiona 'ESC' para salir.")

# --- Bucle Principal ---
while True:
    # 1. Leer la posición actual de los 6 trackbars HSV
    h_min = cv2.getTrackbarPos('H Min', 'Controles HSV')
    h_max = cv2.getTrackbarPos('H Max', 'Controles HSV')
    s_min = cv2.getTrackbarPos('S Min', 'Controles HSV')
    s_max = cv2.getTrackbarPos('S Max', 'Controles HSV')
    v_min = cv2.getTrackbarPos('V Min', 'Controles HSV')
    v_max = cv2.getTrackbarPos('V Max', 'Controles HSV')

    # 2. Leer la posición del trackbar de Erosión
    kernel_erosion_size = cv2.getTrackbarPos('Kernel Erosion', 'Controles HSV')
    
    # Kernel debe ser impar.
    if kernel_erosion_size % 2 == 0:
        kernel_erosion_size += 1
    if kernel_erosion_size == 0:
        kernel_erosion_size = 1


    # 3. Crear los arrays de límites HSV
    limite_inferior = np.array([h_min, s_min, v_min])
    limite_superior = np.array([h_max, s_max, v_max])

    # 4. Crear la máscara con cv2.inRange()
    mascara = cv2.inRange(hsv, limite_inferior, limite_superior)

    # 5. Aplicar Erosión si el tamaño del kernel es mayor a 1
    if kernel_erosion_size > 1:
        kernel = np.ones((kernel_erosion_size, kernel_erosion_size), np.uint8)
        mascara_limpia = cv2.erode(mascara, kernel, iterations=1)
    else:
        mascara_limpia = mascara # Si el kernel es 1, no aplicamos erosión (o aplicamos con un kernel 1x1 sin efecto)


    # 6. Mostrar las imágenes
    cv2.imshow('Imagen Original', imagen)
    cv2.imshow('Mascara HSV (con Erosion)', mascara_limpia) # Mostramos la máscara limpia

    # 7. Esperar por una tecla (1ms) y comprobar si es 'ESC'
    k = cv2.waitKey(1) & 0xFF
    if k == 27:  # 27 es el código ASCII para la tecla 'Esc'
        break

# Limpiar y cerrar todo
cv2.destroyAllWindows()