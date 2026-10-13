FROM postgres:16.4-bookworm

USER root
COPY requirements.txt /tmp/requirements.txt
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        python3 \
        python3-pip \
        python3-psycopg2 \
        python3-yaml \
        python3-requests \
        curl \
    && pip3 install --break-system-packages -r /tmp/requirements.txt \
    && rm -rf /var/lib/apt/lists/* \
    && mkdir -p /var/lib/postgresql/data /etc/patroni \
    && chown -R postgres:postgres /var/lib/postgresql /etc/patroni

COPY entrypoint.sh /entrypoint.sh
RUN chmod 755 /entrypoint.sh

USER postgres
ENTRYPOINT ["/entrypoint.sh"]
