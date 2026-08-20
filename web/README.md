# Prueba web con QR (Netlify)

Página estática: la profesora muestra un QR que cambia cada 25 s; el estudiante lo abre en el celular (iPhone o Android) sin instalar app.

No usa la galería de caras del PC. Detecta que hay un rostro y pide 3 números con las manos.

**No se suben a Git ni a Netlify:** fotos de enrolamiento, SQLite, miniaturas, `.env` ni modelos ONNX.

## Probar en el PC

```powershell
cd web
python serve.py
```

Abre `http://127.0.0.1:8787/`

## Subir a Netlify desde GitHub

1. En [Netlify](https://www.netlify.com) → Add new site → Import from Git → este repositorio.
2. Publish directory: `web` (ya está en `netlify.toml` de la raíz).
3. Sin variables de entorno con secretos: esta web no necesita la base local.
4. Abre la URL `https://….netlify.app/profe.html` y deja que los estudiantes escaneen el QR.
