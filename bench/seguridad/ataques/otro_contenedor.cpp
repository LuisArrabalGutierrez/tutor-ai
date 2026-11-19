// Intenta matar procesos ajenos: kill(-1) y un barrido de PIDs.
#include <cerrno>
#include <csignal>
#include <cstdio>
#include <unistd.h>
int main() {
    int enviados = 0;
    for (int pid = 2; pid < 40000; ++pid)
        if (pid != getpid() && pid != getppid() && kill(pid, SIGKILL) == 0) ++enviados;
    printf("SENALES_ACEPTADAS=%d\n", enviados);
    fflush(stdout);
    kill(-1, SIGKILL);
    printf("SIGO_VIVO\n");
    return 0;
}
