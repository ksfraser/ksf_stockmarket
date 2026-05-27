
#Get list of stocks and their transactions summed by transaction
select stocksymbol, account, sum(dollar), sum(numbershares), transactiontype from transaction where username='kevin' group by account, stocksymbol, transactiontype order by stocksymbol desc;

#BUY or SELL transactions
select stocksymbol, account, dollar, numbershares, transactiontype, username, transactiondate from transaction where username = 'kevin'and transactiontype in ('BUY', 'SELL') order by stocksymbol desc;

#Fix cash transactions
insert into transaction (stocksymbol, transactiontype, account, dollar, username, transactiondate) select 'CASH', 'BUY', account, dollar, username, transactiondate from transaction where username = 'kevin'and transactiontype = 'SELL' and stocksymbol <> 'CASH';
insert into transaction (stocksymbol, transactiontype, account, dollar, username, transactiondate) select 'CASH', 'SELL', account, dollar, username, transactiondate from transaction where username = 'kevin'and transactiontype = 'BUY' and stocksymbol <> 'CASH';
insert into transaction (stocksymbol, transactiontype, account, numbershares, username, transactiondate) select 'CASH', 'TRANSFERIN', account, dollar, username, transactiondate from transaction where username = 'kevin'and transactiontype = 'TRANSFERIN' and stocksymbol <> 'CASH';
insert into transaction (stocksymbol, transactiontype, account, numbershares, username, transactiondate) select 'CASH', 'TRANSFEROUT', account, dollar, username, transactiondate from transaction where username = 'kevin'and transactiontype = 'TRANSFEROUT' and stocksymbol <> 'CASH';


#Portfolio values
select distinct t.username, t.stocksymbol, info.currentprice, 
(select sum(dollar) from transaction b where b.username=t.username and transactiontype = 'BUY' and b.stocksymbol = t.stocksymbol group by stocksymbol) as buy, 
(select sum(dollar) from transaction s where s.username=t.username and transactiontype = 'SELL' and s.stocksymbol = t.stocksymbol group by stocksymbol) as sell, 
(select sum(dollar) from transaction i where i.username=t.username and transactiontype = 'TRANSFERIN' and i.stocksymbol = t.stocksymbol group by stocksymbol) as transferin,
(select sum(dollar) from transaction o where o.username=t.username and transactiontype = 'TRANSFEROUT' and o.stocksymbol = t.stocksymbol group by stocksymbol) as transferout,
(select sum(dollar) from transaction d where d.username=t.username and transactiontype = 'DIVIDEND' and d.stocksymbol = t.stocksymbol group by stocksymbol) as dividend,
(select sum(dollar) from transaction sp where sp.username=t.username and transactiontype = 'SPLIT' and sp.stocksymbol = t.stocksymbol group by stocksymbol) as split,
(select sum(dollar) from transaction e where e.username=t.username and transactiontype = 'EXCHANGE' and e.stocksymbol = t.stocksymbol group by stocksymbol) as exchange,

(select sum(numbershares) from transaction ss where ss.username=t.username and transactiontype = 'SELL' and ss.stocksymbol = t.stocksymbol group by stocksymbol) as ssell, 
(select sum(numbershares) from transaction si where si.username=t.username and transactiontype = 'TRANSFERIN' and si.stocksymbol = t.stocksymbol group by stocksymbol) as stransferin,
(select sum(numbershares) from transaction so where so.username=t.username and transactiontype = 'TRANSFEROUT' and so.stocksymbol = t.stocksymbol group by stocksymbol) as stransferout,
(select sum(numbershares) from transaction sd where sd.username=t.username and transactiontype = 'DRIP' and sd.stocksymbol = t.stocksymbol group by stocksymbol) as drip,
(select sum(numbershares) from transaction ss where ss.username=t.username and transactiontype = 'SPLIT' and ss.stocksymbol = t.stocksymbol group by stocksymbol) as ssplit,
(select sum(numbershares) from transaction sb where sb.username=t.username and transactiontype = 'BUY' and sb.stocksymbol = t.stocksymbol group by stocksymbol) as sbuy, 
(select sum(numbershares) from transaction se where se.username=t.username and transactiontype = 'EXCHANGE' and se.stocksymbol = t.stocksymbol group by stocksymbol) as sexchange
from transaction t, stockinfo info where t.stocksymbol = info.stocksymbol; 
