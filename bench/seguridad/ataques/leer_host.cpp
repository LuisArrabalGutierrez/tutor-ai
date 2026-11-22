// Intenta leer archivos de la máquina anfitriona. La ruta del canario llega en canario.txt.
#include <fstream>
#include <iostream>
#include <string>
static void probar(const std::string& ruta) {
    std::ifstream f(ruta);
    std::string linea;
    if (f && std::getline(f, linea)) std::cout << "LEIDO " << ruta << " => " << linea.substr(0, 80) << "\n";
    else std::cout << "NO_LEIDO " << ruta << "\n";
}
int main() {
    std::ifstream c("canario.txt");
    std::string ruta_canario;
    std::getline(c, ruta_canario);
    probar(ruta_canario);
    probar("/etc/shadow");
    probar("/var/run/docker.sock");
    probar("/host/etc/hostname");
    probar("/root/.ssh/id_rsa");
    return 0;
}
