#include <algorithm>
#include <iostream>
#include <map>
#include <sstream>
#include <string>
#include <vector>

struct Alumno {
    std::string nombre;
    std::vector<double> notas;
    double media() const {
        double s = 0;
        for (double n : notas) s += n;
        return notas.empty() ? 0 : s / notas.size();
    }
};

class Clase {
    std::vector<Alumno> alumnos;
public:
    void anadir(const std::string& nombre, const std::vector<double>& notas) {
        alumnos.push_back({nombre, notas});
    }
    std::vector<Alumno> ordenados() const {
        std::vector<Alumno> copia = alumnos;
        std::sort(copia.begin(), copia.end(),
                  [](const Alumno& a, const Alumno& b) { return a.media() > b.media(); });
        return copia;
    }
    std::map<char, int> histograma() const {
        std::map<char, int> h;
        for (const auto& a : alumnos) {
            double m = a.media();
            h[m >= 9 ? 'A' : m >= 7 ? 'B' : m >= 5 ? 'C' : 'D']++;
        }
        return h;
    }
};

int main() {
    Clase c;
    const char* nombres[] = {"Ana", "Luis", "Marta", "Pablo", "Sara", "Jorge", "Elena", "Raul"};
    for (int i = 0; i < 200; ++i) {
        std::vector<double> notas;
        for (int j = 0; j < 6; ++j) notas.push_back(((i * 37 + j * 11) % 101) / 10.0);
        std::ostringstream nombre;
        nombre << nombres[i % 8] << i;
        c.anadir(nombre.str(), notas);
    }
    auto top = c.ordenados();
    for (int i = 0; i < 5; ++i) std::cout << top[i].nombre << " " << top[i].media() << "\n";
    for (const auto& par : c.histograma()) std::cout << par.first << ": " << par.second << "\n";
    return 0;
}
