#!/bin/bash
# Dispara el DAG, espera a que termine y muestra el estado de cada tarea.
DAG=agroprecio_semanal
RUN="manual_$(date +%Y%m%d_%H%M%S)"
AIRFLOW="docker compose exec -T airflow airflow"

$AIRFLOW dags unpause "$DAG" >/dev/null 2>&1
if ! $AIRFLOW dags trigger "$DAG" -r "$RUN" >/dev/null 2>&1; then
    echo "Airflow no está listo. Corre: make airflow"
    exit 1
fi
echo "Corrida $RUN"

STATE=""
for _ in $(seq 1 120); do
    STATE=$($AIRFLOW dags list-runs "$DAG" -o plain 2>/dev/null | grep "$RUN" | grep -oE 'success|failed' | head -1)
    [ -n "$STATE" ] && break
    sleep 5
done

$AIRFLOW tasks states-for-dag-run "$DAG" "$RUN" -o plain 2>/dev/null | grep "^$DAG" | awk '{print "  " $0}'
echo "Resultado: ${STATE:-sin terminar}"
[ "$STATE" = success ]
