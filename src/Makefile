MYSQLCFLAGS=`mysql_config --cflags`
MYSQLLIBS=`mysql_config --libs`


clean:
	rm -f datafoxclient

example: example.c
	gcc $(mysql_config --cflags) example.c $(mysql_config --libs) -o example
