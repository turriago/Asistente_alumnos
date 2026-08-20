Los archivos `.onnx` y `.task` de esta carpeta se descargan en el PC y **no se suben a Git**.

- YuNet: detección de rostros (~230 KB)
- SFace: embeddings para enrolamiento (~37 MB)
- Hand Landmarker: esqueleto de manos MediaPipe (~7 MB)

```powershell
python scripts/download_models.py
```

Si `face.auto_download` o `hands.auto_download` está en `true`, el kiosco también los baja la primera vez que faltan.
