#!/bin/sh

#/usr/lib/news/bin/ctlinnd newgroup finance.control
/usr/lib/news/bin/ctlinnd newgroup finance.application.tables
#/usr/lib/news/bin/ctlinnd newgroup finance.stocks
#/usr/lib/news/bin/ctlinnd newgroup finance.stocks.discussion
/usr/lib/news/bin/ctlinnd newgroup finance.stocks.alerts
#/usr/lib/news/bin/ctlinnd newgroup finance.currencies
#/usr/lib/news/bin/ctlinnd newgroup finance.currencies.discussion
/usr/lib/news/bin/ctlinnd newgroup finance.currencies.alerts
/usr/lib/news/bin/ctlinnd newgroup finance.reports
/usr/lib/news/bin/ctlinnd newgroup finance.reports.discussion


/usr/lib/news/bin/ctlinnd changegroup finance.stocks m
/usr/lib/news/bin/ctlinnd changegroup finance.currencies m
