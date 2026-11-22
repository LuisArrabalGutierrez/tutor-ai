// Reserva y toca memoria en bloques de 16 MB hasta que el sistema lo impida.
#include <cstdio>
#include <cstdlib>
#include <cstring>
int main() {
    const size_t BLOQUE = 16 * 1024 * 1024;
    for (int mb = 16; mb <= 8192; mb += 16) {
        char* p = (char*)malloc(BLOQUE);
        if (!p) { printf("MALLOC_FALLA\n"); return 1; }
        memset(p, 1, BLOQUE);
        printf("MB=%d\n", mb);
        fflush(stdout);
    }
    printf("SIN_LIMITE\n");
    return 0;
}
