# Modo demo

`DEMO_MODE=true` está activo por defecto.

## Fase 8

```powershell
python -m attendance_system.kiosk.app
```

Qué mostrar:

1. Ponte al frente hasta que salga tu nombre.
2. El kiosco pide un número al azar (1/3). Muéstralo con los dedos.
3. Baja las manos. Pide el segundo. Luego el tercero.
4. Una foto fija no sirve: hay que cambiar el gesto tres veces.
5. **Aún no** guarda asistencia.

```powershell
python -m attendance_system.kiosk.app
```

Qué mostrar:

1. Palmas a la cámara.
2. 3 dedos de una mano → número **3**.
3. Una mano abierta + 2 dedos de la otra → **7**.
4. El recuadro grande a la derecha muestra el dígito.
5. **Aún no** pide un número secreto ni guarda asistencia.

## Fase 6

El esqueleto de manos quedó integrado; ahora también se lee el número (Fase 7).

## Fase 4

```powershell
python -m attendance_system.face.recognize
```

Qué mostrar:

1. Un enrolado basta (p. ej. `20260001`).
2. Tu cara → `IDENTIFICADO` y el nombre de demo.
3. Si la similitud no llega al umbral → `NO IDENTIFICADO` (sin decir quién “casi” eres).
4. Dos caras → `VARIOS ROSTROS`, no identifica.
5. No registra asistencia.

## Fase 3

```powershell
python scripts/create_demo_data.py
python -m attendance_system.students.enroll --id 20260001
```

Qué mostrar:

1. Un solo rostro → `LISTO PARA ENROLAR`.
2. **E** tres veces (frente, izquierda, derecha). No aparece “tú eres Ana” en cámara continua.
3. Miniatura en `data/photos/` (no Git).

## Fase 2

```powershell
python -m attendance_system.face.demo
```

Qué mostrar:

1. Al alejarte: `ESPERANDO ROSTRO`.
2. Al acercarte: caja verde y `ROSTRO DETECTADO`.
3. Si hay dos personas: `VARIOS ROSTROS` y cajas naranjas.
4. No aparece ningún nombre.

## Fase 1

La demo de cámara:

```powershell
python -m attendance_system.camera.demo
```

Qué mostrar en una revisión:

1. La webcam se ve.
2. FPS y resolución están en pantalla.
3. Q cierra limpio.
4. Si no hay cámara, el mensaje es claro (no un stack trace como única salida).

Datos ficticios: `scripts/create_demo_data.py`.
