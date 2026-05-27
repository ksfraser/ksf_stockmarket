#include <iostream>
#include "time.h"
#include "turtledata.cpp"
#include <stdio.h>
using namespace std;

int main( int argc, char** argv )
{
	int iarraycount, i;
	turtledata* turtledata1, turtledataarray[10];
	iarraycount = 0;
	i = 0;

	time_t t = time(0);
	tm time = *localtime(&t);
	cout << "Date is " << time.tm_year << '/' time.tm_month << '/' << time.tm_mday << "\n";

/*
  time_t rawtime;
  struct tm * timeinfo;

  time ( &rawtime );
  timeinfo = localtime ( &rawtime );
  printf ( "Current local time and date: %s", asctime (timeinfo) );
*/
/*
  time_t rawtime;

  time ( &rawtime );
  printf ( "The current local time is: %s", ctime (&rawtime) );
*/



/*
	turtledata1 = new turtledata( "IBM", time.tm_year + "-" time.tm_month + "-" time.tm_mday );
	turtledataarray[iarraycount] = turtledata1;
	cout << "Made turtledata 1\n";
	iarraycount++;

	turtledata1 = new turtledata( "CPR", date( "Ymd" ) );
	turtledataarray[iarraycount] = turtledata1;
	iarraycount++;
	cout << "Made turtledata 2\n";
	
	turtledata1 = new turtledata( "SU", date( "Ymd" ) );
	turtledataarray[iarraycount] = turtledata1;
	iarraycount++;
	cout << "Made turtledata 3\n";

	for( i=0; i <= iarraycount; i++ )
	{
		cout << "Symbol: " << turtledataarray[i]->Getsymbol() << "\n";
	}
*/

	exit(0);
}
