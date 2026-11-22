FROM apache/airflow:3.3.2
# El pipeline va en su propio entorno: así sus versiones no chocan con las de Airflow
COPY requirements.txt /tmp/requirements.txt
RUN python -m venv /home/airflow/pipeline \
    && /home/airflow/pipeline/bin/pip install --no-cache-dir -r /tmp/requirements.txt
# Base de datos de Airflow; el volumen hereda estos permisos
RUN mkdir -p /opt/airflow/estado && chmod 775 /opt/airflow/estado
