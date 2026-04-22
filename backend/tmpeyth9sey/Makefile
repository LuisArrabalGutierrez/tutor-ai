TARGET=$(EJ)main
EJ=./dist/
BUILD=./build/
SRC=./src/
INC=./include/
DOC=./doc/
CFLAGS = -g -I$(INC)
OBJS = $(BUILD)ConjuntoUsuarios.o \
       $(BUILD)Usuario.o \
       main.cpp

all: $(TARGET)

$(TARGET) : $(OBJS)
	mkdir -p $(EJ)
	g++ $(CFLAGS) $(OBJS) -o $(TARGET)

$(BUILD)%.o : $(SRC)%.cpp
	mkdir -p $(BUILD)
	g++ -c $(CFLAGS) $< -o $@

.PHONY: clean doc
clean:
	rm -r $(BUILD) $(EJ) $(DOC)

doc:
	doxygen Doxyfile
