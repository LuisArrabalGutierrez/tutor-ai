#include <iostream>
#include <vector>
// Criba de Eratostenes hasta 20 millones: unos segundos de CPU pura
int main() {
    const int N = 20000000;
    std::vector<bool> primo(N + 1, true);
    long cuenta = 0;
    for (long i = 2; i <= N; ++i) {
        if (!primo[i]) continue;
        ++cuenta;
        for (long j = i * i; j <= N; j += i) primo[j] = false;
    }
    std::cout << cuenta << std::endl;
    return 0;
}
