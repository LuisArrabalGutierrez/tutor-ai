// Ocho hilos en bucle infinito: intenta acaparar todos los núcleos.
#include <thread>
#include <vector>
int main() {
    std::vector<std::thread> hilos;
    for (int i = 0; i < 8; ++i)
        hilos.emplace_back([] { volatile unsigned long x = 0; while (true) ++x; });
    for (auto& h : hilos) h.join();
    return 0;
}
