DROP TABLE IF EXISTS `userprefs`;
CREATE TABLE `userprefs` (
`iduserprefs` INTEGER() unsigned  NULL auto_increment default '' comment '',
`prefname` VARCHAR(45)   NULL  default '' comment '',
`prefvalue` VARCHAR(45)   NULL  default '' comment '',
`idusers` INTEGER() unsigned  NULL  default '' comment '', PRIMARY KEY (`iduserprefs`)) ENGINE=InnoDB;
