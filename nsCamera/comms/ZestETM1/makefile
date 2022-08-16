lib_NAME = libZestETM1.so

# minor edits made for use in nsCamera

all: $(lib_NAME)

CC = gcc

ARCH := $(shell getconf LONG_BIT)

CPP_FLAGS_32 := -m32
CPP_FLAGS_64 := -m64

CFLAGS = -g -fPIC $(CPP_FLAGS_$(ARCH)) -Wall -I../../../Inc
lib_OBJS = Main.o Data.o Error.o UPnP.o

$(lib_NAME): $(lib_OBJS)
	#ar -crs $(lib_NAME) $(lib_OBJS)
	gcc -shared -o $(ARCH)/$(lib_NAME) $(lib_OBJS)

Data.o: Data.c ZestETM1.h Private.h
Error.o: Error.c ZestETM1.h Private.h
UPnP.o: UPnP.c ZestETM1.h Private.h
Main.o: Main.c ZestETM1.h Private.h

clean:
	rm -f *.o *.a *~

