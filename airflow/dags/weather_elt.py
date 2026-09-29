"""ELT погоды: приём среза → dbt → тесты → публикация витрины.

Срез задаётся явно (params.slice), не датой запуска DAG.
При ежедневном расписании обрабатывался бы календарный день data_interval_end
минус один день — но здесь учебный ручной запуск на фиксированные 2024-06-01..03.

max_active_runs=1 сериализует запуски: параллельные копии не дерутся за TRUNCATE.
"""

from datetime import datetime

from airflow import DAG
from airflow.models.param import Param
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator
from airflow.utils.trigger_rule import TriggerRule

PROJECT = "/opt/project"


def publish_if_tests_passed(**context):
    """Копирует кандидата в published только если предыдущие задачи успешны.

    Вызывается после dbt_test с trigger_rule=all_success: при падении теста
    эта функция не запускается, и потребитель продолжает видеть старую витрину.
    Сами таблицы dbt при этом уже пересчитаны — откатывать их не нужно.
    """
    import os

    import psycopg2

    conn = psycopg2.connect(
        host=os.environ["WAREHOUSE_HOST"],
        port=os.environ["WAREHOUSE_PORT"],
        dbname=os.environ["WAREHOUSE_DB"],
        user=os.environ["WAREHOUSE_USER"],
        password=os.environ["WAREHOUSE_PASSWORD"],
    )
    with conn:
        with conn.cursor() as cursor:
            cursor.execute("truncate published.weather_daily")
            cursor.execute(
                """
                insert into published.weather_daily (
                    city_id, city_name, federal_district, observed_date,
                    n_hours, avg_temp_c, min_temp_c, max_temp_c,
                    amplitude_c, precip_sum_mm, published_at
                )
                select
                    city_id, city_name, federal_district, observed_date,
                    n_hours, avg_temp_c, min_temp_c, max_temp_c,
                    amplitude_c, precip_sum_mm, now()
                from marts.weather_daily_candidate
                """
            )
            cursor.execute("select count(*) from published.weather_daily")
            n = cursor.fetchone()[0]
    conn.close()
    print(f"published.weather_daily rows = {n}")


with DAG(
    dag_id="weather_elt",
    description="ELT: Open-Meteo hourly → Postgres/dbt → published daily mart",
    start_date=datetime(2024, 6, 1),
    schedule=None,
    catchup=False,
    max_active_runs=1,
    params={
        "slice": Param(
            default="control",
            description="Каталог внутри data/: control или cases/case4_bad_temperature",
        ),
    },
    tags=["hw02", "weather", "dwh"],
) as dag:
    load_raw = BashOperator(
        task_id="load_raw",
        bash_command=(
            "python3 /opt/project/loader/load_raw.py '{{ params.slice }}'"
        ),
    )

    dbt_run = BashOperator(
        task_id="dbt_run",
        bash_command=(
            "cd /opt/project/dbt && dbt run --profiles-dir /opt/project/dbt --project-dir /opt/project/dbt"
        ),
    )

    dbt_test = BashOperator(
        task_id="dbt_test",
        bash_command=(
            "cd /opt/project/dbt && dbt test --profiles-dir /opt/project/dbt --project-dir /opt/project/dbt"
        ),
    )

    publish = PythonOperator(
        task_id="publish",
        python_callable=publish_if_tests_passed,
        trigger_rule=TriggerRule.ALL_SUCCESS,
    )

    load_raw >> dbt_run >> dbt_test >> publish
