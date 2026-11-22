"""Se corre dentro de la imagen de Airflow (no con pytest): el DAG carga y respeta el orden."""
import sys

from airflow.dag_processing.dagbag import DagBag

bag = DagBag(dag_folder="/opt/airflow/dags")
if bag.import_errors:
    sys.exit(f"Errores al importar: {bag.import_errors}")
dag = bag.dags["agroprecio_semanal"]
order = [t.task_id for t in dag.topological_sort()]
expected = ["descargar", "silver", "gold", "calidad", "modelo", "prediccion", "boletin"]
if order != expected:
    sys.exit(f"Orden inesperado: {order}")
print("DAG correcto:", " -> ".join(order))
