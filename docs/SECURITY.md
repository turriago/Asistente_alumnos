# Seguridad

## Alcance actual (Fase 1)

La demo de cámara corre en local. No hay red, usuarios ni base de datos todavía.

Riesgos de esta fase:

- Otra aplicación puede estar usando la webcam.
- El PC debe estar físico y visible: quien vea la pantalla ve la cámara.

## Principios para fases posteriores

- Sin envío de biometría a internet.
- SQLite solo en el PC de la profesora.
- Acceso restringido a la carpeta del proyecto.
- BitLocker recomendado en el disco del PC.
- Cifrado de plantillas: se evaluará cuando existan embeddings.
- No secretos en el repositorio.

## Reportar un problema

Si encuentras que el código guarda una imagen de rostro o imprime un embedding, trátalo como defecto de privacidad y corrígelo antes de seguir.
