# Enrolar personas (tú solo pones nombre + fotos)

Ya hay carpetas listas: `persona_01` … `persona_10`.

En cada una:

1. El nombre completo: en `nombre.txt`, o en un `.txt` con el nombre (`Giovanny.txt`, `anuar.txt`, …).
2. Copia 3 fotos: frente, izquierda, derecha. Opcional: un `.mp4` o `.mov` (mejor calidad para la ficha en el celular vía Supabase).
3. La foto de la ficha del kiosco es la que empieza por `1_` (ejemplo: `1_IMG_1531.JPG`).

No hace falta crear carpetas ni tener la lista de clase. El sistema pone un ID temporal (`TMP-0001`).

Cuando termines:

```powershell
python -m attendance_system.students.enroll_files
```

No uses `data/photos/` para estas fotos. No las subas a Git.
