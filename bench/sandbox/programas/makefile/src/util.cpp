#include "util.h"
#include <sstream>
std::string formatea(double valor) {
    std::ostringstream s;
    s << "traza=" << valor;
    return s.str();
}
