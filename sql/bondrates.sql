DROP TABLE IF EXISTS `bondrates`;
CREATE TABLE `bondrates` (
`idbondrate` integer(11)   NOT NULL  default '' comment 'Index',
`calendaryear` date(19)   NOT NULL  default '' comment 'Calendar Year',
`bondrate` integer(11)   NOT NULL  default '3' comment 'Bond Rate', PRIMARY KEY (`idbondrate`)) ENGINE=InnoDB;
