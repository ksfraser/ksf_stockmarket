DROP TABLE IF EXISTS `tasks`;
CREATE TABLE `tasks` (
`idtasks` integer(8)   NOT NULL  default '0' comment 'Task Index',
`tasktype` varchar(45)   NULL  default 'TASK' comment 'Task Type',
`taskdescription` varchar(45)   NOT NULL  default '' comment 'Task Description',
`tasklink` varchar(45)   NOT NULL  default '' comment 'Link for Task/Menu',
`taskparent` varchar(45)   NOT NULL  default '' comment 'Parent Menu Item', PRIMARY KEY (`idtasks`)) ENGINE=InnoDB;
