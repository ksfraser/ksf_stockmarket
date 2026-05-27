DROP TABLE IF EXISTS `statearc`;
CREATE TABLE `statearc` (
`workflow_id` smallint(5) unsigned  NULL  default '' comment 'Workflow Process',
`transition_id` smallint(5) unsigned  NULL  default '' comment 'Transition that this Arc connects to',
`place_id` smallint(5) unsigned  NULL  default '' comment 'Place that this Arc connects to',
`direction` char(3)   NULL  default '' comment 'Direction of Arc (Into/Out of) Transition',
`arc_type` varchar(10)   NULL  default 'auto' comment 'Arc Type (auto or manual)',
`pre_condition` text(255)   NOT NULL  default 'none' comment 'Precondition',
`created_date` datetime(17)   NULL  default '' comment 'Created by User',
`created_user` varchar(16)   NOT NULL  default '' comment 'Created Date',
`revised_date` datetime(17)   NOT NULL  default '' comment 'Revised by User',
`revised_user` varchar(16)   NOT NULL  default '' comment 'Revision Date', PRIMARY KEY (`workflow_id`, 'workflow_id', 'transition_id', 'place_id')) ENGINE=InnoDB;
