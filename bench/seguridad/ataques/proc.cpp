// Mira qué enseña /proc: procesos visibles y datos de la máquina anfitriona.
#include <cctype>
#include <dirent.h>
#include <fstream>
#include <iostream>
#include <string>
#include <thread>
int main() {
    int pids = 0;
    if (DIR* d = opendir("/proc")) {
        while (dirent* e = readdir(d)) if (isdigit(e->d_name[0])) ++pids;
        closedir(d);
    }
    std::cout << "PIDS_VISIBLES=" << pids << "\n";
    std::ifstream m("/proc/meminfo");
    std::string clave; long kb;
    if (m >> clave >> kb) std::cout << "MEMTOTAL_KB=" << kb << "\n";
    std::cout << "NUCLEOS=" << std::thread::hardware_concurrency() << "\n";
    std::ifstream cmd("/proc/1/cmdline");
    std::string c1; std::getline(cmd, c1, '\0');
    std::cout << "PID1=" << c1 << "\n";
    std::ifstream v("/proc/version");
    std::string ver; std::getline(v, ver);
    std::cout << "KERNEL=" << ver.substr(0, 60) << "\n";
    return 0;
}
