DROP TABLE IF EXISTS `transaction_close`;
CREATE TABLE `transaction_close` (
`transaction_sequence` int(11)   NULL  default '' comment 'FK',
`username` varchar(11)   NULL  default '' comment '',
`transactiondate` date()   NULL  default '' comment 'Transaction Date',
`idstockinfo` int(11)   NULL  default '' comment 'stockinfo index',
`stocksymbol` varchar(11)   NULL  default '' comment '',
`numbershares` int(11)   NULL  default '' comment '',
`transactiontype` varchar(11)   NULL  default '' comment '',
`dollar` float(11)   NULL  default '' comment '',
`idusers` int(11)   NULL  default '' comment 'User',
`account` varchar(11)   NULL  default '' comment 'Which account is this transaction in (TRADE/RRSP/TFSA) ',
`currency` varchar(11)   NULL  default '' comment 'Home Currency',
`createduser` varchar(11)   NULL  default '' comment '',
`createddate` datetime(11)   NULL  default '' comment '',
`reviseddate` timestamp(11)   NULL  default '' comment '',
`reviseduser` varchar(11)   NULL  default '' comment '',
`closeBreakEven` float(11)   NULL  default '' comment 'Break Even close',
`closeLong` float(11)   NULL  default '' comment 'Close Long',
`closeShort` float(11)   NULL  default '' comment 'Close Short',
`closeTimeLimit` date(11)   NULL  default '' comment 'Close after so many days',
`closePartial` float(11)   NULL  default '' comment 'Target for closing part of the position',
`closeTargetPrice` float(11)   NULL  default '' comment 'Close once a target price is met',
`closeValueAtRisk` float(11)   NULL  default '' comment 'Close once a Value At Risk is hit',
`stopsize` float(11)   NULL  default '' comment 'The Stop Size diff between high price and stop price',
`turtle_long_close` float(11)   NULL  default '' comment 'Turtle Strategy initial Long close price',
`turtle_short_close` float(11)   NULL  default '' comment 'Turtle Strategy initial Short close price',
`CONSTRAINT` `transaction_close_ibfk_1`(11)   NOT NULL  default '' comment '', PRIMARY KEY (`transaction_sequence`)) ENGINE=InnoDB;
