#If a library depends on other libraries, put the dependant library before its depencies or there will be a reference error

LIB=-lta_lib -lmysqlclient -lm -lksf_sql -lksf_prog_param -lksf_log -lksf_time -lksf_memory -lksf_cdl
LIBDIR=-L/usr/lib/mysql -Lsrc/lib
DFLAGS=-Wall
#COMPFLAGS=-g -c -ggdb -fmem-report -ftest-coverage -pedantic
COMPFLAGS=-g -c -ggdb -ftest-coverage -pedantic
LINKFLAGS=-I./src/ -I. -lgcov
SRCS=ta-lib.example.c

all: ta-lib.example 

ta-lib.example: ta-lib.example.o 
	$(CC) -o ta-lib.example ta-lib.example.o $(LIBDIR) $(LINKFLAGS) $(LIB)

ta-lib.example.o: ta-lib.example.c
	$(CC) $(COMPFLAGS) ta-lib.example.c $(DFLAGS)

splint:
	#splint $(INCLUDEDIRS) $(SRCS) -redef
	#splint $(INCLUDEDIRS) $(SRCS) -weak
	splint $(INCLUDEDIRS) $(SRCS) +charintliteral +trytorecover -predboolint -realcompare
	#splint $(INCLUDEDIRS) $(SRCS) +charintliteral +export-header



beta-dir:
	$(MAKE) -C beta

clean:
	rm -f *.o
	rm -f ta-lib.example
	$(MAKE) -C beta clean


