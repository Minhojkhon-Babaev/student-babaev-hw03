#!/bin/bash
set -euo pipefail
NAME="${PATRONI_NAME:?}"
CONNECT="${PATRONI_CONNECT_ADDRESS:?}"
chmod 700 /var/lib/postgresql/data
cat > /tmp/patroni.yml <<EOF
scope: weatherhw03
namespace: /hse/
name: ${NAME}

restapi:
  listen: 0.0.0.0:8008
  connect_address: ${CONNECT%:*}:8008

etcd3:
  hosts: etcd:2379

bootstrap:
  dcs:
    ttl: 30
    loop_wait: 10
    retry_timeout: 10
    maximum_lag_on_failover: 1048576
    postgresql:
      use_pg_rewind: true
      parameters:
        wal_level: replica
        hot_standby: "on"
        max_connections: 100
        shared_buffers: 128MB
        max_wal_senders: 10
        wal_keep_size: 128MB
        hot_standby_feedback: "on"
        timezone: UTC
  initdb:
    - encoding: UTF8
    - locale: C.UTF-8
    - data-checksums
  pg_hba:
    - host replication replicator 0.0.0.0/0 md5
    - host all all 0.0.0.0/0 md5

postgresql:
  listen: 0.0.0.0:5432
  connect_address: ${CONNECT}
  data_dir: /var/lib/postgresql/data
  bin_dir: /usr/lib/postgresql/16/bin
  authentication:
    superuser:
      username: postgres
      password: postgres
    replication:
      username: replicator
      password: replicator
  parameters:
    unix_socket_directories: /tmp

tags:
  nofailover: false
  noloadbalance: false
EOF
exec patroni /tmp/patroni.yml
