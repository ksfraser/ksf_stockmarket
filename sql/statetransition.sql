DROP TABLE IF EXISTS `statetransition`;
CREATE TABLE `statetransition` (
`workflow_id` integer(11)   NOT NULL  default '' comment 'Workflow',
`transition_desc` varchar(45)   NOT NULL  default '' comment 'Description',
`transition_id` smallint(5) unsigned  NULL  default '' comment 'Index',
`transition_name` varchar(80)   NULL  default '' comment 'Transition Name',
`transition_trigger_type` varchar(4)   NULL  default 'USER' comment 'Type of trigger',
`time_limit` smallint(5) unsigned  NOT NULL  default '0' comment 'Expiry Time Limit (0=none)',
`task_id` varchar(40)   NULL  default '' comment 'Task',
`role_id` varchar(16)   NOT NULL  default '' comment 'Role',
`created_date` datetime(17)   NULL  default '' comment 'Created Date',
`created_user` varchar(16)   NOT NULL  default '' comment 'Created User',
`revised_date` datetime(17)   NOT NULL  default '' comment 'Revision Date',
`revised_user` varchar(16)   NOT NULL  default '' comment 'Revised by User', PRIMARY KEY (`transition_id`)) ENGINE=InnoDB;
