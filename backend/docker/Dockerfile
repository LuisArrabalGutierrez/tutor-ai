FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=Europe/Madrid

#Forzar a que TODO vaya por IPv4
RUN echo 'Acquire::ForceIPv4 "true";' > /etc/apt/apt.conf.d/99force-ipv4

#SERVIDORES ESPAÑOLES
RUN sed -i 's/archive.ubuntu.com/es.archive.ubuntu.com/g' /etc/apt/sources.list.d/ubuntu.sources || \
    sed -i 's/archive.ubuntu.com/es.archive.ubuntu.com/g' /etc/apt/sources.list

#INSTALACIÓN
RUN apt-get update && \
    apt-get install -y \
    build-essential \
    gcc \
    g++ \
    make \
    nano \
    vim \
    python3 \
    python3-pip \
    curl \
    && rm -rf /var/lib/apt/lists/*

# CONFIGURACIÓN DEL USUARIO
RUN useradd -ms /bin/bash alumno
WORKDIR /home/alumno
USER alumno

CMD ["/bin/bash"]