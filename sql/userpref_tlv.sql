DROP TABLE IF EXISTS `userpref_tlv`;
CREATE TABLE `userpref_tlv` (
`iduserpref_tlv` INT(11)   NULL auto_increment default '' comment 'index',
`pref` VARCHAR(11)   NULL  default '' comment 'Preference Name',
`type` VARCHAR(11)   NULL  default '' comment 'Preference Data Type',
`length` INT(11)   NULL  default '' comment 'Data Length',
`defaultvalue` VARCHAR(11)   NULL  default '' comment 'Default Value',
`minvalue` VARCHAR(11)   NULL  default '' comment 'Minimum Value',
`maxvalue` VARCHAR(11)   NULL  default '' comment 'Maximum Value', PRIMARY KEY (`iduserpref_tlv`)) ENGINE=InnoDB;
