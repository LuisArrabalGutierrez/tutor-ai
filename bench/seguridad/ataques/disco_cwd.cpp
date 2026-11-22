// Escribe en disco hasta 1 GiB o hasta que el sistema lo impida.
#include <cerrno>
#include <cstdio>
#include <cstring>
#include <fcntl.h>
#include <unistd.h>
int main() {
    static char bloque[1 << 20];
    memset(bloque, 7, sizeof bloque);
    int fd = open("relleno.bin", O_WRONLY | O_CREAT | O_TRUNC, 0600);
    if (fd < 0) { printf("OPEN_FALLA errno=%d\n", errno); return 0; }
    for (int mb = 1; mb <= 1024; ++mb) {
        if (write(fd, bloque, sizeof bloque) != (ssize_t)sizeof bloque) {
            printf("WRITE_FALLA_EN_MB=%d errno=%d (%s)\n", mb, errno, strerror(errno));
            return 0;
        }
        if (mb % 64 == 0) { fsync(fd); printf("MB=%d\n", mb); fflush(stdout); }
    }
    printf("SIN_LIMITE\n");
    return 0;
}
