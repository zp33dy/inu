FROM postgres:latest
ENV POSTGRES_DB=inu_db
ENV POSTGRES_PASSWORD=secr33t
ENV POSTGRES_USER=inu
ENV APP_DB_USER=inu
ENV APP_DB_PASS=secr33t
ENV APP_DB_NAME=inu_db
VOLUME [ "./../psql" ]
# COPY  - ./dependencies/postgres/01-init.sh /docker-entrypoint-initdb.d/01-init.sh
# COPY 01-init.sh /docker-entrypoint-initdb.d/01-init.sh
