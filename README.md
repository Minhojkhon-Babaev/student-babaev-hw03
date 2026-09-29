# ДЗ 2. Погода Open-Meteo → DWH

Потребитель — аналитик климата. Ему нужна таблица «город × день»: средняя, мин, макс температура и суточная амплитуда.

Вопрос: в какие дни 1–3 июня 2024 у Москвы, Сочи и Якутска амплитуда день–ночь была наибольшей, и чем приморский Сочи отличается от континентального Якутска. Считается `max(temp) − min(temp)` по часам UTC.

Одна строка факта — один час UTC в одном городе.

## Источник и срез

[Open-Meteo Historical Weather](https://open-meteo.com/en/docs/historical-weather-api), ERA5, CC BY 4.0. Время UTC. Температура °C, осадки мм.

Контрольный срез: Москва, Сочи, Якутск; `2024-06-01`…`2024-06-03`; 216 часов. Лежит в `data/control/`. Перескачать: `python3 scripts/fetch_source.py`.

## Схема

```
raw.weather_hourly ──► ods.stg_weather_hourly ──► dds.fact_weather_hourly ──► marts.weather_daily_candidate
raw.city_reference ──► ods.stg_city           ──► dds.dim_city ─────────────┘         │
                                              ──► dds.dim_date                       ▼
                                                                         published.weather_daily
```

- факт `fact_weather_hourly`: ключ `(city_id, observed_at)`, связь N:1 с `dim_city` (по версии на дату) и `dim_date`
- измерения: город (SCD2), календарный день
- витрина: одна строка = город × день

История атрибутов города нужна для случая «сменился округ»: старые дни остаются на старой версии. В Open-Meteo истории округа нет — для случая 3 кладётся явно помеченный синтетический `city.csv` (`is_synthetic=true`). Это не промышленный SCD2.

Размерная модель подходит, потому что отчёт режет факт по городу и дате. Для произвольных ad-hoc срезов по сырым часам хватило бы одной широкой таблицы.

## Запуск

Версии: Postgres 16, Airflow 2.9.3, dbt-core 1.8.2, dbt-postgres 1.8.2. Docker, порты `127.0.0.1:5433` и `127.0.0.1:8080`. UI Airflow: `student` / `student`.

```bash
cd student-babaev-hw02
docker compose build
docker compose up -d
# подождать, пока http://127.0.0.1:8080 откроется

docker compose exec -T airflow bash -lc \
  'export PATH=/home/airflow/.local/bin:$PATH; airflow dags trigger weather_elt --conf "{\"slice\": \"control\"}"'
```

Или `bash scripts/trigger_dag.sh control`.

Срез задаётся параметром `slice`, не датой запуска DAG. При ежедневном расписании обрабатывался бы календарный день события, не `logical_date`.

Параллельные запуски выключены: `max_active_runs=1`.

Четыре случая (после зелёного `control`):

```bash
bash scripts/trigger_dag.sh control                      # 1. повтор
bash scripts/trigger_dag.sh cases/case2_new_day          # 2. +день Москвы
bash scripts/trigger_dag.sh cases/case3_city_history     # 3. SCD2 округа
bash scripts/trigger_dag.sh cases/case4_bad_temperature  # 4. 999 °C, публикация стоп
```

Витрина: `docker compose exec -T postgres psql -U warehouse -d warehouse -f /dev/stdin < queries.sql`

Независимый контроль: `python3 scripts/independent_check.py data/control/weather.csv`

## Если DAG красный

`cannot drop table raw.weather_hourly because other objects depend on it` — старая версия загрузчика. В текущем коде raw чистится `TRUNCATE`.

`dbt test` падает на `assert_temperature_physical` — в срезе есть температура вне −90…60 °C. Публикация не выполняется, `published.weather_daily` не меняется.

## Среда evidence

macOS, Docker 29.5.2 в colima, 6 CPU / 12 ГиБ. Запуски 2026-09-29.
