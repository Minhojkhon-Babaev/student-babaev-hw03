FROM apache/airflow:2.9.3-python3.11

USER root
RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq-dev \
    && rm -rf /var/lib/apt/lists/*

USER airflow
RUN pip install --no-cache-dir "dbt-core==1.8.2" "dbt-postgres==1.8.2" "psycopg2-binary==2.9.9"
