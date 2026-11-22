#include "matriz.h"
Matriz::Matriz(int f, int c) : filas(f), cols(c), datos(new double[f * c]()) {}
Matriz::Matriz(const Matriz& o) : filas(o.filas), cols(o.cols), datos(new double[o.filas * o.cols]) {
    for (int i = 0; i < filas * cols; ++i) datos[i] = o.datos[i];
}
Matriz::~Matriz() { delete[] datos; }
double& Matriz::en(int f, int c) { return datos[f * cols + c]; }
double Matriz::en(int f, int c) const { return datos[f * cols + c]; }
Matriz Matriz::por(const Matriz& o) const {
    Matriz r(filas, o.cols);
    for (int i = 0; i < filas; ++i)
        for (int j = 0; j < o.cols; ++j)
            for (int k = 0; k < cols; ++k) r.en(i, j) += en(i, k) * o.en(k, j);
    return r;
}
double Matriz::traza() const {
    double t = 0;
    for (int i = 0; i < filas && i < cols; ++i) t += en(i, i);
    return t;
}
