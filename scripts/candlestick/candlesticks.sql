#insert ignore into  technicalanalysis ( symbol, date, candlestick ) select a.symbol, a.date, '' 
#from stockprices a, stockprices b, stockprices c, stockprices d
#where
# 	a.symbol = b.symbol
#        AND a.symbol = c.symbol
#        AND a.symbol = d.symbol
#        AND a.date = (select date from stockprices where symbol = a.symbol order by date desc limit 1,1)
#        AND b.date = (select date from stockprices where symbol = a.symbol and date < a.date order by date desc limit 2,1)
#        AND c.date = (select date from stockprices where symbol = a.symbol and date < a.date order by date desc limit 3,1)
#        AND d.date = (select date from stockprices where symbol = a.symbol and date < a.date order by date desc limit 4,1)

#use finance;

insert into scriptlog (scriptname, scriptstep) values ('candlesticks.sql', 'SCRIPT START' );
insert into scriptlog (scriptname, scriptstep) values ('candlesticks.sql', 'tradedates start' );
insert ignore into tradedates (tradedates) select date from stockprices;
insert into scriptlog (scriptname, scriptstep) values ('candlesticks.sql', 'tradedates stop' );


insert into scriptlog (scriptname, scriptstep) values ('candlesticks.sql', 'Date determination start' );
set @adate = 'select tradedates from tradedates order by tradedates desc limit 0,1';
set @bdate = 'select tradedates from tradedates order by tradedates desc limit 1,1';
set @cdate = 'select tradedates from tradedates order by tradedates desc limit 2,1';
insert into scriptlog (scriptname, scriptstep) values ('candlesticks.sql', concat_ws( '::', 'Date determination: ', @adate, @bdate, @cdate ) );
insert into scriptlog (scriptname, scriptstep) values ('candlesticks.sql', 'Date determination stop' );



insert into scriptlog (scriptname, scriptstep) values ('candlesticks.sql', 'Doji start' );
insert ignore into  technicalanalysis ( symbol, date, candlestick ) select symbol, date, 'Doji' from stockprices where day_open = day_close and date = (select max(tradedates) from tradedates);
insert into scriptlog (scriptname, scriptstep) values ('candlesticks.sql', 'Doji stop' );

insert into scriptlog (scriptname, scriptstep) values ('candlesticks.sql', 'Hammer start' );
insert ignore into  technicalanalysis ( symbol, date, candlestick ) select symbol, date, 'Hammer' from stockprices where day_open = day_close and date = (select max(tradedates) from tradedates)
AND (day_high - day_low) > 3 * ( day_open - day_close )
AND( ( (day_close- day_low) / (.001 + day_high - day_low) ) > 0.6 )
AND( ( (day_open-day_low) /(.001 + day_high-day_low) ) >0.6 )
;
insert into scriptlog (scriptname, scriptstep) values ('candlesticks.sql', 'Hammer stop' );

insert into scriptlog (scriptname, scriptstep) values ('candlesticks.sql', 'Hanging Man start' );
insert ignore into  technicalanalysis ( symbol, date, candlestick ) select symbol, date, 'Hanging_Man' from stockprices where day_open = day_close and date = (select max(tradedates) from tradedates)
AND ( (day_high - day_low) > 4 * (day_open - day_close) )
AND ( ( (day_close - day_low) / (.001 +day_high- day_low) ) >= 0.75 )
AND ( ( (day_open - day_low) / (.001 +day_high- day_low) ) >= .075 )
;
insert into scriptlog (scriptname, scriptstep) values ('candlesticks.sql', 'Hanging Man stop' );

insert into scriptlog (scriptname, scriptstep) values ('candlesticks.sql', 'Shooting Star start' );
insert ignore into  technicalanalysis ( symbol, date, candlestick ) select a.symbol, a.date, 'Shooting_Star' from stockprices a
where
        a.date = (@adate)
 AND ( (a.day_high - a.day_low) > 4 * (a.day_open - a.day_close) )
 AND ( ( (a.day_high - a.day_close) / (.001 +a.day_high - a.day_low) ) >= 0.75 )
 AND ( ( (a.day_high - a.day_open)  / (.001 +a.day_high - a.day_low) ) >= 0.75 )
;
insert into scriptlog (scriptname, scriptstep) values ('candlesticks.sql', 'Shooting Star stop' );

insert ignore into  technicalanalysis ( symbol, date, candlestick ) select a.symbol, a.date, 'Inverted_Hammer' from stockprices a
where
        a.date = (@adate)
AND (   (a.day_high - a.day_low)  > 3 * (a.day_open - a.day_close) )
AND ( ( (a.day_high - a.day_close) / (.001 +a.day_high- a.day_low) ) > 0.6 )
AND ( ( (a.day_high - a.day_open)  / (.001 +a.day_high- a.day_low) ) > 0.6 )
;


insert into scriptlog (scriptname, scriptstep) values ('candlesticks.sql', 'Bullish Engulfing start' );
insert ignore into  technicalanalysis ( symbol, date, candlestick ) select a.symbol, a.date, 'Bullish_Engulfing' from stockprices a, stockprices b
where
 	a.symbol = b.symbol
        AND a.date = (@adate)
        AND b.date = (@bdate)
	AND b.day_open > b.day_close
	AND a.day_close > a.day_open
	AND a.day_close >= b.day_open
	AND b.day_close >= a.day_open
	AND ( a.day_close - a.day_open ) > (b.day_open - b.day_close)
;
insert into scriptlog (scriptname, scriptstep) values ('candlesticks.sql', 'Bullish Engulfing stop' );

insert into scriptlog (scriptname, scriptstep) values ('candlesticks.sql', 'Piercing Line start' );
insert ignore into  technicalanalysis ( symbol, date, candlestick ) select a.symbol, a.date, 'Piercing_Line' from stockprices a, stockprices b
where
 	a.symbol = b.symbol
        AND a.date = (@adate)
        AND b.date = (@bdate)
AND ( 	(b.day_close < b.day_open) 
	AND ( ( (b.day_open + b.day_close) / 2 ) < a.day_close ) 
	AND (a.day_open < a.day_close) 
	AND (a.day_open < b.day_close) 
	AND (a.day_close < b.day_open) 
	AND ((a.day_close - a.day_open) / (.001 + (a.day_high - a.day_low)) > 0.6)
)
;
insert into scriptlog (scriptname, scriptstep) values ('candlesticks.sql', 'Piercing Line stop' );

insert into scriptlog (scriptname, scriptstep) values ('candlesticks.sql', 'Bullish Hamari start' );
insert ignore into  technicalanalysis ( symbol, date, candlestick ) select a.symbol, a.date, 'Bullish_Harami' from stockprices a, stockprices b
where
 	a.symbol = b.symbol
        AND a.date = (@adate)
        AND b.date = (@bdate)
AND ((b.day_open > b.day_close) AND (a.day_close > a.day_open) AND (a.day_close <= b.day_open) AND (b.day_close <= a.day_open) AND ((a.day_close - a.day_open) < (b.day_open - b.day_close)))
;
insert into scriptlog (scriptname, scriptstep) values ('candlesticks.sql', 'Bullish Hamari stop' );


insert into scriptlog (scriptname, scriptstep) values ('candlesticks.sql', 'Bearish Hamari start' );
insert ignore into  technicalanalysis ( symbol, date, candlestick ) select a.symbol, a.date, 'Bearish_Harami' from stockprices a, stockprices b
where
 	a.symbol = b.symbol
        AND a.date = (@adate)
        AND b.date = (@bdate)
AND ((b.day_close > b.day_open) AND (a.day_open > a.day_close) AND (a.day_open <= b.day_close) AND (b.day_open <= a.day_close) AND ((a.day_open - a.day_close) < (b.day_close - b.day_open)))
;
insert into scriptlog (scriptname, scriptstep) values ('candlesticks.sql', 'Bearish Hamari stop' );

insert into scriptlog (scriptname, scriptstep) values ('candlesticks.sql', 'Bullish Kicker start' );
insert ignore into  technicalanalysis ( symbol, date, candlestick ) select a.symbol, a.date, 'Bullish_Kicker' from stockprices a, stockprices b
where
 	a.symbol = b.symbol
        AND a.date = (@adate)
        AND b.date = (@bdate)
AND (b.day_open > b.day_close) AND (a.day_open >= b.day_open) AND (a.day_close > a.day_open)
;
insert into scriptlog (scriptname, scriptstep) values ('candlesticks.sql', 'Bullish Kicker stop' );

insert into scriptlog (scriptname, scriptstep) values ('candlesticks.sql', 'Bearish Kicker start' );
insert ignore into  technicalanalysis ( symbol, date, candlestick ) select a.symbol, a.date, 'Bearish_Kicker' from stockprices a, stockprices b
where
 	a.symbol = b.symbol
        AND a.date = (@adate)
        AND b.date = (@bdate)
AND (b.day_open < b.day_close) AND (a.day_open <= b.day_open) AND (a.day_close <= a.day_open)
;
insert into scriptlog (scriptname, scriptstep) values ('candlesticks.sql', 'Bearish Kicker stop' );

insert into scriptlog (scriptname, scriptstep) values ('candlesticks.sql', 'Dark Cloud start' );
insert ignore into  technicalanalysis ( symbol, date, candlestick ) select a.symbol, a.date, 'Dark_Cloud' from stockprices a, stockprices b
where
 	a.symbol = b.symbol
        AND a.date = (@adate)
        AND b.date = (@bdate)
AND ((b.day_close > b.day_open) AND (((b.day_close + b.day_open) / 2) > a.day_close) AND (a.day_open > a.day_close) AND (a.day_open > b.day_close) AND (a.day_close > b.day_open) AND ((a.day_open - a.day_close) / (.001 + (a.day_high - a.day_low)) > .6)) 
;
insert into scriptlog (scriptname, scriptstep) values ('candlesticks.sql', 'Dark Cloud stop' );

insert into scriptlog (scriptname, scriptstep) values ('candlesticks.sql', 'Morning Star start' );
insert ignore into  technicalanalysis ( symbol, date, candlestick ) select a.symbol, a.date, 'Morning_Star' from stockprices a, stockprices b, stockprices c
where
 	a.symbol = b.symbol
        AND a.symbol = c.symbol
        AND a.date = (@adate)
        AND b.date = (@bdate)
        AND c.date = (@cdate)
AND ((c.day_open>c.day_close)AND((c.day_open-c.day_close)/(.001+c.day_high-c.day_low)>.6)AND(c.day_close>b.day_open)AND(b.day_open>b.day_close)AND((b.day_high-b.day_low)>( 3 * (b.day_close-b.day_open)))AND(a.day_close>a.day_open)AND(a.day_open>b.day_open))
;
insert into scriptlog (scriptname, scriptstep) values ('candlesticks.sql', 'Morning Star stop' );

insert into scriptlog (scriptname, scriptstep) values ('candlesticks.sql', 'Evening Star start' );
insert ignore into  technicalanalysis ( symbol, date, candlestick ) select a.symbol, a.date, 'Evening_Star' from stockprices a, stockprices b, stockprices c
where
 	a.symbol = b.symbol
        AND a.symbol = c.symbol
        AND a.date = (@adate)
        AND b.date = (@bdate)
        AND c.date = (@cdate)
AND ((c.day_close > c.day_open) AND ((c.day_close - c.day_open) / (.001 + c.day_high - c.day_low) > .6) AND (c.day_close < b.day_open) AND (b.day_close > b.day_open) AND ((b.day_high - b.day_low) > (3 * (b.day_close - b.day_open))) AND (a.day_open > a.day_close) AND (a.day_open < b.day_open))
;
insert into scriptlog (scriptname, scriptstep) values ('candlesticks.sql', 'Evening Star stop' );

insert into scriptlog (scriptname, scriptstep) values ('candlesticks.sql', 'SCRIPT STOP' );
