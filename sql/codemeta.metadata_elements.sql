DROP TABLE IF EXISTS `codemeta.metadata_elements`;
CREATE TABLE `codemeta.metadata_elements` (
`field_key` char(3)   NULL  default '' comment '',
`sort_key` int(11)   NULL  default '' comment '',
`form_sort_key` int(11)   NULL  default '' comment '',
`prikey` char(1)   NULL  default '' comment '',
`foreign_key` varchar(45)   NULL  default '' comment '',
`KEY` `table_name`()   NOT NULL  default '' comment '', PRIMARY KEY ()) ENGINE=InnoDB;
