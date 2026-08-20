# Privacidad

Este prototipo, cuando tenga reconocimiento, tratará **datos biométricos sensibles**.

En Colombia aplica la Ley 1581 de 2012: autorización previa, expresa, informada y diferenciada; finalidad concreta; alternativa no biométrica; supresión.

El software no sustituye el cumplimiento legal.

## Reglas del prototipo

- Preferir datos ficticios (`DEMO_MODE=true`).
- Si participan personas reales, debe existir consentimiento escrito y voluntario.
- No subir a GitHub fotos, embeddings, bases SQLite ni listas reales.
- El `.gitignore` ya excluye esos archivos.
- Logs sin vectores faciales ni recortes de imagen.
- Procesamiento local. No hay APIs cloud de reconocimiento.

## Qué existe en la Fase 5

- Kiosco en `127.0.0.1` (no se publica en la red por defecto).
- El vídeo MJPEG y el JSON de estado se quedan en el PC.
- Miniaturas solo si el ID coincide con un archivo en `data/photos/`.
- Sigue sin archivo de fotos originales ni asistencia.
- El celular **no lee el disco del PC**. Si quieres ver esas miniaturas en el teléfono, el kiosco las envía a Netlify (función `gallery`, clave = código de clase) o a **Supabase Storage** (fotos/vídeos; Postgres solo metadatos). Eso no se sube a GitHub. Es un canal opcional del prototipo.

Esto es un sistema de **verificación de identidad y prueba de vivacidad**, no un sistema infalible ni un archivo fotográfico.
