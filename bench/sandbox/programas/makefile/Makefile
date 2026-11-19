# Los .o van a la raíz del proyecto: en la VM el alumno no puede escribir en las subcarpetas
# que copia `docker cp` (hallazgo F-1 de bench/README.md).
CXX = g++
CXXFLAGS = -O1 -Iinclude

main: main.o matriz.o util.o
	$(CXX) -o main main.o matriz.o util.o

%.o: src/%.cpp
	$(CXX) $(CXXFLAGS) -c $< -o $@
