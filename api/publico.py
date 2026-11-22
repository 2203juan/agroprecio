"""La página y la API en un solo servicio, para desplegar un único contenedor.

En local nginx sirve la página y reenvía /api; aquí lo hace la misma aplicación.
"""
import os

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from api.main import app as api

app = FastAPI(title="AgroPrecio", docs_url=None, redoc_url=None, openapi_url=None)
app.mount("/api", api)
app.mount("/", StaticFiles(directory=os.getenv("AGRO_WEB", "web"), html=True), name="web")
