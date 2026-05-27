DROP TABLE IF EXISTS `stateflowrole`;
CREATE TABLE `stateflowrole` (
`idstateflowrole` int(8)   NOT NULL  default '0' comment 'Workflow-Role ID',
`roles_id` int(8)   NOT NULL  default '0' comment 'Role ID',
`workflow_id` int(8)   NOT NULL  default '0' comment 'Workflow ID', PRIMARY KEY (`idstateflowrole`)) ENGINE=InnoDB;
