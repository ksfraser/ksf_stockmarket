DROP TABLE IF EXISTS `turtledates`;
CREATE TABLE `turtledates` (
`turtledates` date(20)   NULL  default '' comment 'The dates for which turtledata values have been calculated', PRIMARY KEY (`turtledates`)) ENGINE=InnoDB;
