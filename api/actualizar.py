"""Corre el pipeline desde la API: con el botón del dashboard o solo, cada semana."""
import subprocess
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

LOG = Path("logs/actualizacion.log")
state = {"corriendo": False, "inicio": None, "fin": None, "codigo": None}
_lock = threading.Lock()


def _run():
    LOG.parent.mkdir(exist_ok=True)
    with open(LOG, "w", encoding="utf-8") as out:
        code = subprocess.call([sys.executable, "main.py"], stdout=out, stderr=subprocess.STDOUT)
    state.update(corriendo=False, fin=datetime.now().isoformat(timespec="seconds"), codigo=code)


def start():
    """Arranca el pipeline en segundo plano. Devuelve False si ya estaba corriendo."""
    with _lock:
        if state["corriendo"]:
            return False
        state.update(corriendo=True, inicio=datetime.now().isoformat(timespec="seconds"),
                     fin=None, codigo=None)
    threading.Thread(target=_run, daemon=True).start()
    return True


def status(lines=8):
    tail = LOG.read_text(encoding="utf-8").splitlines()[-lines:] if LOG.exists() else []
    return {**state, "ultimas_lineas": tail}


def schedule(weekday, hour, last_run):
    """Revisa cada 10 minutos y corre el pipeline el día y la hora indicados,
    salvo que ya haya corrido ese día. last_run() devuelve la fecha 'AAAA-MM-DD'."""
    def loop():
        while True:
            now = datetime.now()
            if now.weekday() == weekday and now.hour >= hour and last_run() != str(now.date()):
                start()
            time.sleep(600)
    threading.Thread(target=loop, daemon=True).start()
