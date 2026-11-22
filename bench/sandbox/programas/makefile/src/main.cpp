#include <iostream>
#include "matriz.h"
#include "util.h"
int main() {
    Matriz a(40, 40), b(40, 40);
    for (int i = 0; i < 40; ++i)
        for (int j = 0; j < 40; ++j) {
            a.en(i, j) = (i + j) % 7;
            b.en(i, j) = (i * j) % 5;
        }
    std::cout << formatea(a.por(b).traza()) << std::endl;
    return 0;
}
