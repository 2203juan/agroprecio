"""DAG semanal de AgroPrecio: una tarea por etapa de main.py.

Cada tarea usa el entorno del pipeline (/home/airflow/pipeline), separado del de Airflow.
Las etapas se pasan los datos por los archivos de data/ y por la base SQLite.
"""
from datetime import timedelta

import pendulum
from airflow.providers.standard.operators.bash import BashOperator
from airflow.sdk import DAG

PROJECT = "/opt/agroprecio"
PYTHON = "/home/airflow/pipeline/bin/python"
STAGES = ["descargar", "silver", "gold", "calidad", "modelo", "prediccion", "boletin"]
# Repetir estas dos no cambia el resultado: si fallan, el problema está en los datos
NO_RETRY = {"calidad", "modelo"}

with DAG(
    dag_id="agroprecio_semanal",
    description="Boletín del DANE -> bronze -> silver -> gold -> modelo -> recomendación",
    # Miércoles y sábado a las 7 a.m.: el DANE publica los viernes, pero a veces con rezago
    schedule="0 7 * * 3,6",
    start_date=pendulum.datetime(2026, 11, 22, tz="America/Bogota"),
    catchup=False,
    max_active_runs=1,
    default_args={"retry_delay": timedelta(minutes=2)},
    tags=["agroprecio", "medallon"],
) as dag:
    previous = None
    for stage in STAGES:
        task = BashOperator(
            task_id=stage,
            bash_command=f"cd {PROJECT} && {PYTHON} main.py --etapa {stage}",
            retries=0 if stage in NO_RETRY else 1,
        )
        if previous:
            previous >> task
        previous = task
