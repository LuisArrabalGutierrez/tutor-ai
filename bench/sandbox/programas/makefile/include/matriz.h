#ifndef MATRIZ_H
#define MATRIZ_H
class Matriz {
    int filas, cols;
    double* datos;
public:
    Matriz(int f, int c);
    Matriz(const Matriz& otra);
    ~Matriz();
    double& en(int f, int c);
    double en(int f, int c) const;
    Matriz por(const Matriz& otra) const;
    double traza() const;
};
#endif
