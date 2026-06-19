FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=Europe/Madrid

# Forzar IPv4 para evitar timeouts de GCP
RUN echo 'Acquire::ForceIPv4 "true";' > /etc/apt/apt.conf.d/99force-ipv4

# Servidores españoles
RUN sed -i 's/archive.ubuntu.com/es.archive.ubuntu.com/g' /etc/apt/sources.list

# Instalación limpia
RUN apt-get update && \
    apt-get install -y build-essential gcc g++ make nano vim python3 python3-pip curl && \
    rm -rf /var/lib/apt/lists/*

# Configuración del usuario aislado
RUN useradd -ms /bin/bash alumno
WORKDIR /home/alumno
USER alumno

CMD ["/bin/bash"]