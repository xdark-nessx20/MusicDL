# Music Downloader API

Una API en Python para descargar música de YouTube en formato MP3 o M4A, usando `yt-dlp` y FFmpeg. Diseñada para integrarse con una app móvil en MIT App Inventor, permite a usuarios descargar audio de forma sencilla. Ideal para proyectos personales con bajo tráfico.

## Características
- Descarga audio de YouTube en MP3 o M4A.
- Soporta diferentes calidades: normal (128 kbps), alta (320 kbps), máxima (mejor disponible).
- Límite de duración (1 hora) para asegurar que solo se descargue música.
- Deployada en Railway (free trial o Hobby plan) para acceso vía HTTPS.
- Conexión fácil con MIT App Inventor (componente Web).

## Requisitos
- Python 3.9+
- Dependencias: `yt-dlp`, `flask`, `uvicorn`, `FFmpeg`
- Cuenta en Railway para deploy (free trial con $5 crédito)
- (Opcional) MIT App Inventor para la app móvil