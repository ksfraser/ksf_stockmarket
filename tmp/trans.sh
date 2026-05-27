#!/bin/sh

for year in 2009
do
	for month in 09 10 11 12
	do
		echo "INSERT ignore INTO \`transaction\` (account, currency, foreigncurrency, transactiondate, createduser, createddate, reviseduser, reviseddate, username, stocksymbol, numbershares, transactiontype, dollar) VALUES ('RRSP', 'CAD', 'CAD', '"$year"-"$month"-15', 'kevin', '2009-12-22', 'kevin', '2009-12-22', 'kevin', 'BR-UN', '0', ' DIVIDEND', '18.00')" >> insert.sql
		echo "INSERT ignore INTO \`transaction\` (account, currency, foreigncurrency, transactiondate, createduser, createddate, reviseduser, reviseddate, username, stocksymbol, numbershares, transactiontype, dollar) VALUES ('RRSP', 'CAD', 'CAD', '"$year"-"$month"-15', 'kevin', '2009-12-22', 'kevin', '2009-12-22', 'kevin', 'INN-UN', '0', ' DIVIDEND', '31.25')" >> insert.sql
		echo "INSERT ignore INTO \`transaction\` (account, currency, foreigncurrency, transactiondate, createduser, createddate, reviseduser, reviseddate, username, stocksymbol, numbershares, transactiontype, dollar) VALUES ('RRSP', 'CAD', 'CAD', '"$year"-"$month"-20', 'kevin', '2009-12-22', 'kevin', '2009-12-22', 'kevin', 'WJX-UN', '0', ' DIVIDEND', '37.50')" >> insert.sql
		echo "INSERT ignore INTO \`transaction\` (account, currency, foreigncurrency, transactiondate, createduser, createddate, reviseduser, reviseddate, username, stocksymbol, numbershares, transactiontype, dollar) VALUES ('RRSP', 'CAD', 'CAD', '"$year"-"$month"-30', 'kevin', '2009-12-22', 'kevin', '2009-12-22', 'kevin', 'BPF-UN', '0', ' DIVIDEND', '115.00')" >> insert.sql
		echo "INSERT ignore INTO \`transaction\` (account, currency, foreigncurrency, transactiondate, createduser, createddate, reviseduser, reviseddate, username, stocksymbol, numbershares, transactiontype, dollar) VALUES ('RRSP', 'CAD', 'CAD', '"$year"-"$month"-30', 'kevin', '2009-12-22', 'kevin', '2009-12-22', 'kevin', 'KEG-UN', '0', ' DIVIDEND', '47.93')" >> insert.sql
		echo "INSERT ignore INTO \`transaction\` (account, currency, foreigncurrency, transactiondate, createduser, createddate, reviseduser, reviseddate, username, stocksymbol, numbershares, transactiontype, dollar) VALUES ('RRSP', 'CAD', 'CAD', '"$year"-"$month"-30', 'kevin', '2009-12-22', 'kevin', '2009-12-22', 'kevin', 'PDM-UN', '0', ' DIVIDEND', '50.00')" >> insert.sql
	echo "" >> insert.sql
	done
done
