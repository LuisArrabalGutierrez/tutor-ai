// Intenta abrir una conexión TCP saliente (8.8.8.8:53) y resolver un nombre.
#include <arpa/inet.h>
#include <cerrno>
#include <cstdio>
#include <cstring>
#include <netdb.h>
#include <sys/socket.h>
#include <sys/time.h>
#include <unistd.h>
int main() {
    int s = socket(AF_INET, SOCK_STREAM, 0);
    if (s < 0) { printf("SOCKET_FALLA errno=%d\n", errno); return 0; }
    timeval tv{5, 0};
    setsockopt(s, SOL_SOCKET, SO_SNDTIMEO, &tv, sizeof tv);
    sockaddr_in d{};
    d.sin_family = AF_INET;
    d.sin_port = htons(53);
    inet_pton(AF_INET, "8.8.8.8", &d.sin_addr);
    if (connect(s, (sockaddr*)&d, sizeof d) == 0) printf("CONEXION_OK\n");
    else printf("CONEXION_FALLA errno=%d (%s)\n", errno, strerror(errno));
    close(s);
    addrinfo* res = nullptr;
    int rc = getaddrinfo("example.com", "80", nullptr, &res);
    printf(rc == 0 ? "DNS_OK\n" : "DNS_FALLA\n");
    return 0;
}
