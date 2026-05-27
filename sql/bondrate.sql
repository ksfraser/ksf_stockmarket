DROP TABLE IF EXISTS `bondrate`;
CREATE TABLE `bondrate` (
`updateddate` timestamp(32)   NOT NULL  default '' comment 'Last Updated',
`idbondrate` integer(11)   NOT NULL  default '' comment 'Index',
`calendaryear` date(19)   NOT NULL  default '' comment 'Calendar Year',
`bondrate` integer(11)   NOT NULL  default '3' comment 'Bond Rate', PRIMARY KEY (`idbondrate`)) ENGINE=InnoDB;
