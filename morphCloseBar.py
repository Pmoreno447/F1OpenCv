import cv2
import numpy as np

def nada(x):
    pass

def procesar_imagen_pista(ruta_imagen, ancho_max_ventana=800):
    """
    Carga una imagen con una máscara HSV y erosión aplicada
    con los valores que nosotros prefiramos. (Calibrarlos con CalibradorHSV.py).
    morphCloseBar.py nos servirá para determinar el valor del filtro de Cierre Morfológico.
    """

    # --- 0. Cargar y Preparar la Imagen ---
    imagen_bgr = cv2.imread(ruta_imagen)
    if imagen_bgr is None:
        print(f"Error: No se pudo cargar la imagen en {ruta_imagen}")
        return

    # Reescalar
    altura, anchura = imagen_bgr.shape[:2]
    if anchura > ancho_max_ventana:
        escala = ancho_max_ventana / anchura
        dim = (ancho_max_ventana, int(altura * escala))
        imagen_bgr = cv2.resize(imagen_bgr, dim, interpolation=cv2.INTER_AREA)
    
    # Convertir a HSV
    hsv = cv2.cvtColor(imagen_bgr, cv2.COLOR_BGR2HSV)

    # --- 1. PARÁMETROS DE CALIBRACIÓN  ---
    # Estos valores los hemos definido previamente usando CalibradorHSV.py
    lim_inf_pista = np.array([0, 0, 33])
    lim_sup_pista = np.array([180, 52, 124])

    # Estos valores los hemos definido previamente usando CalibradorHSV.py
    kernel_erosion_size = 4 
    # ---

    # --- 1b. Crear ventana para el nuevo control ---
    cv2.namedWindow('Controles Morfologicos')
    cv2.resizeWindow('Controles Morfologicos', 500, 100)

    # Creamos el nuevo trackbar para el CIERRE
    cv2.createTrackbar('Kernel Cierre', 'Controles Morfologicos', 1, 25, nada)
    cv2.setTrackbarPos('Kernel Cierre', 'Controles Morfologicos', 9) # Empezar con un valor (ej. 9)


    # --- 2. Creación de la Máscara Inicial ---
    mascara_inicial = cv2.inRange(hsv, lim_inf_pista, lim_sup_pista)

    # --- 3. Limpieza (SOLO EROSIÓN) ---
    # El valor de la erosion lo escogimos antes en CalibradorHSV.py
    
    # Aseguramos que sea impar. Es necesario para que determine un pixel central como anclaje.
    if kernel_erosion_size % 2 == 0 and kernel_erosion_size > 0:
         kernel_erosion_size += 1 
         
    if kernel_erosion_size > 1:
        kernel_erosion = np.ones((kernel_erosion_size, kernel_erosion_size), np.uint8)
        mascara_erosionada = cv2.erode(mascara_inicial, kernel_erosion, iterations=1)
    else:
        mascara_erosionada = mascara_inicial # Sin erosión si el kernel es 0 o 1


    # --- 4. Bucle para CIERRE (Morph Close)---
    print("Ajusta el 'Kernel Cierre' para rellenar agujeros. Presiona ESC para salir.")
    
    while True:
        # --- 4a. Leer el trackbar de Cierre ---
        kernel_cierre_size = cv2.getTrackbarPos('Kernel Cierre', 'Controles Morfologicos')
        
        # Asegurar que sea impar
        if kernel_cierre_size % 2 == 0:
             kernel_cierre_size += 1
        if kernel_cierre_size == 0:
             kernel_cierre_size = 1

        # --- 4b. Aplicar Cierre ---
        if kernel_cierre_size > 1:
            kernel_cierre = np.ones((kernel_cierre_size, kernel_cierre_size), np.uint8)
            # Aplicamos el cierre a la MÁSCARA YA EROSIONADA
            mascara_final_limpia = cv2.morphologyEx(mascara_erosionada, cv2.MORPH_CLOSE, kernel_cierre, iterations=1)
        else:
            mascara_final_limpia = mascara_erosionada # Sin cierre si el kernel es 1
        
        # --- 4c. Mostrar Resultados ---
        cv2.imshow('Original', imagen_bgr)
        # cv2.imshow('Mascara HSV (Inicial, con ruido)', mascara_inicial)
        cv2.imshow('Mascara (con Erosion)', mascara_erosionada) # Mostramos la erosionada
        cv2.imshow('Mascara (Erosion + Cierre)', mascara_final_limpia) # Y la final
        
        # --- 4d. Esperar tecla ---
        k = cv2.waitKey(1) & 0xFF
        if k == 27:  # 27 es el código ASCII para la tecla 'Esc'
            # Guardar la máscara final
            # cv2.imwrite('mascara_pista_final_limpia.jpg', mascara_final_limpia)
            print(f"Máscara final guardada con Kernel Cierre = {kernel_cierre_size}")
            break


    # --- 5. Limpiar ---
    cv2.destroyAllWindows()


# --- Ejecutar el script ---
procesar_imagen_pista('Imagenes/rb_ring16.jpg')