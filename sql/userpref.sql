DROP TABLE IF EXISTS `userpref`;
CREATE TABLE `userpref` (
`iduserpref` INT(11)   NULL auto_increment default '' comment 'index',
`idusers` INT(11)   NULL  default '' comment 'User',
`iduserpref_tlv` INT(11)   NULL  default '' comment 'Preference',
`value` VARCHAR(11)   NULL  default '' comment '', PRIMARY KEY (`iduserpref`)) ENGINE=InnoDB;
