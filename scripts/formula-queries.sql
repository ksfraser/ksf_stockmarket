

//Find yesterday and today's price + change for a given currency/foreigncurrency pair
select a.currency, a.foreigncurrency, a.date, a.day_close, b.day_close, (a.day_close - b.day_close) as pchange from fxprices a, fxprices b where a.currency = b.currency and a.foreigncurrency = b.foreigncurrency and a.date = b.date + 1 order by a.date desc limit 10;

//Update the day_change from today and yesterday's close
update fxprices a, fxprices b 
set 
	a.day_change = (a.day_close - b.day_close) 
where 
	a.currency = b.currency 
	and a.foreigncurrency = b.foreigncurrency 
	and a.date = b.date + 1 
;


