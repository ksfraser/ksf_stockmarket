DROP TABLE IF EXISTS `taxstatus`;
CREATE TABLE `taxstatus` (
`idtaxstatus` INT(11)   NULL auto_increment default '' comment 'Index',
`taxstatus` VARCHAR(11)   NULL  default '' comment 'Tax Status',
`notes` VARCHAR(11)   NULL  default '' comment 'Notes',
`createduser` INT(11)   NULL  default '' comment 'Created By User',
`createddate` DATETIME(11)   NULL  default '' comment 'Created Date',
`updateduser` VARCHAR(11)   NULL  default '' comment 'Updated by User',
`updateddate` TIMESTAMP(11)   NULL  default '' comment 'Updated by User', PRIMARY KEY ()) ENGINE=InnoDB;
