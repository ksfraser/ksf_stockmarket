DROP TABLE IF EXISTS `jobspool`;
CREATE TABLE `jobspool` (
`idjobspool` INT(11)   NULL  default '' comment 'Job Index',
`objectname` VARCHAR(32)   NULL  default '' comment 'Program',
`parameter` VARCHAR(32)   NULL  default '' comment 'Command Line Parameters',
`scheduletype` INT(11)   NULL  default '' comment 'Minutes between runs',
`active` INT(1)   NULL  default '' comment 'Schedule Active',
`nextrun` DATETIME(20)   NULL  default '' comment 'Next Run date and time',
`lastrun` DATETIME(20)   NULL  default '' comment 'Last run date and time',
`createuser` INT(11)   NULL  default '' comment 'Created By',
`createdtime` DATETIME(20)   NULL  default '' comment 'Created Date and Time',
`updateuser` INT()   NULL  default '' comment 'Updated By',
`updatedtime` DATETIME(20)   NULL  default '' comment 'Updated Date and Time',
`shell` varchar(45)   NOT NULL  default '' comment 'Shell to run script',
`runstatus` varchar(1)   NOT NULL  default 'N' comment 'Job run status',
`clonedfrom` integer(11)   NOT NULL  default '' comment 'Job cloned from', PRIMARY KEY (`idjobspool`)) ENGINE=InnoDB;
