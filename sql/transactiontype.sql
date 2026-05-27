DROP TABLE IF EXISTS `transactiontype`;
CREATE TABLE `transactiontype` (
`AddSub` tinyint(2)   NOT NULL  default '1' comment 'Add or Subtract transaction',
`transactiontype` varchar(45)   NOT NULL  default '' comment 'Transaction Type', PRIMARY KEY ()) ENGINE=InnoDB;
