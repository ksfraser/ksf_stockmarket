DROP TABLE IF EXISTS `scriptlog`;
CREATE TABLE `scriptlog` (
`idscriptlog` int(11)   NULL auto_increment default '' comment '',
`date` timestamp(11)   NULL  default '' comment '',
`scriptname` varchar(11)   NOT NULL  default '' comment '',
`scriptstep` varchar(11)   NOT NULL  default '' comment '', PRIMARY KEY (`idscriptlog`)) ENGINE=InnoDB;
