FROM gcc:11

ENV TZ=Europe/Madrid
ENV DEBIAN_FRONTEND=noninteractive

# Forzar IPv4 para evitar timeouts en GCP
RUN echo 'Acquire::ForceIPv4 "true";' > /etc/apt/apt.conf.d/99force-ipv4

# Instalar paquetes base
RUN apt-get update && \
    apt-get install -y nano vim python3 python3-pip curl && \
    rm -rf /var/lib/apt/lists/*

# Crear usuario sin privilegios
RUN useradd -ms /bin/bash alumno
WORKDIR /home/alumno
USER alumno

CMD ["/bin/bash"]