DROP TABLE IF EXISTS `roletask`;
CREATE TABLE `roletask` (
`idroletask` integer(8)   NOT NULL  default '0' comment 'Index',
`roles_id` integer(8)   NOT NULL  default '' comment 'Role',
`idtasks` integer(8)   NOT NULL  default '' comment 'Task', PRIMARY KEY (`idroletask`)) ENGINE=InnoDB;
