DROP TABLE IF EXISTS `statetoken`;
CREATE TABLE `statetoken` (
`token_status` varchar(1)   NOT NULL  default '' comment 'Token Status',
`statetoken_id` int(8)   NOT NULL  default '' comment 'Table Key',
`workflow_id` int(8)   NOT NULL  default '' comment 'Workflow ID',
`place_id` int(8)   NOT NULL  default '' comment 'Place ID',
`context` int(32)   NOT NULL  default '' comment 'Context',
`status` char(1)   NOT NULL  default 'A' comment 'Status Flag', PRIMARY KEY (`statetoken_id`)) ENGINE=InnoDB;
