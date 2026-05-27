
#!/bin/sh

#for x in *-UN.*.csv; do echo $x; SYM=$(cut -f 1 -d '.' <<<"${x}") ; EXCH="TO"; DATE=$(cut -f 2 -d '.' <<<"${x}"); ./loadcsv2stockprices.sh $SYM $DATE "." $EXCH ; done
#for x in *-UN.*.csv; do echo $x; SYM=$(cut -f 1 -d '.' <<<"${x}") ; EXCH="TO"; DATE=$(cut -f 2 -d '.' <<<"${x}"); echo $SYM $DATE; ./loadcsv2stockprices.sh $SYM $DATE "." $EXCH ; done
#for x in *-UN.*.csv; do echo $x; SYM=$(cut -f 1 -d '.' <<<"${x}") ; EXCH="TO"; DATE=$(cut -f 2 -d '.' <<<"${x}"); echo $SYM $DATE; ./loadcsv2stockprices.sh $SYM $DATE "." $EXCH ; done
#for x in *.*.csv; do echo $x; SYM=$(cut -f 1 -d '.' <<<"${x}") ; EXCH="NYSE"; DATE=$(cut -f 2 -d '.' <<<"${x}"); echo $SYM $DATE; ./loadcsv2stockprices.sh $SYM $DATE "." $EXCH ; done


#BMO.TO.2011119-20131016.csv
SYMBOL=$1
DATE=$2
FILEEXCHANGE=$3
EXCHANGE=$4
#DATE="2011119-20131016"

SQL="LOAD DATA LOCAL INFILE '$SYMBOL$FILEEXCHANGE$DATE.csv' INTO TABLE stockprices FIELDS TERMINATED BY ',' LINES TERMINATED BY '\n'  (@col1,@col2,@col3,@col4,@col5,@col6,@col7) set symbol='$SYMBOL', date=@col1, day_open=@col2, day_high=@col3, day_low=@col4, day_close=@col5, volume=@col6, adjustedclose=@col7, stockexchange='$EXCHANGE' ;"

#Date,Open,High,Low,Close,Volume,Adj Close

echo $SQL
echo $SQL|mysql -pm1l1ce finance && mv $SYMBOL$FILEEXCHANGE$DATE.csv loaded2stockprices/
