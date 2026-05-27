<?php

/*This is a metadata file.  Metadata is data that describes other data.  We will use this metadata to create classes when programming new code.

This file will be used to define the basic sql statements to start the tables to hold the metadata.
*/

/*
-- we'll have one row in this table for every object type
-- and thus for every new SQL table that gets defined; an
-- object type and its database table name are the same;
-- We limit a table_name to 21 characters so that we can
-- have some freedom to create schema objects whose names
-- are prefixed with an object type

-- a "pretty name" is a synonym used when presenting pages
-- to users; the prettiness could be as simple as replacing
-- underscores with spaces or spelling out abbreviations;
-- e.g., for an object type of "airplane_design", the pretty
-- form might be "airplane design", and pretty_plural
-- "airplane designs"
*/

$DBNAME="codemeta";
$qdb = "create database if not exists $DBNAME";
$quse = "use $DBNAME";
$qtable1 = "create table if not exists metadata_object_types  (
        table_name              varchar(21) primary key,
        pretty_name             varchar(100) not null,
        pretty_plural           varchar(100)
)";

/*
-- here is the table for elements that are unique to an object type
-- (the housekeeping elements can be defined implicitly in the source
-- code for the application generator); there will be one row in
-- the metadata table per element
*/

$qtable2 = "create table if not exists metadata_elements (
        metadata_id              integer primary key auto_increment,
        table_name               varchar(30) not null, -- references metadata_object_types,
        column_name              varchar(30) not null, -- comment known as field in mysql,
        pretty_name              varchar(100) not null,
        abstract_data_type       varchar(30) not null, -- ie. text or shorttext or boolean or user
          -- this one is not null except when abstract_data_type is user
        db_data_type         varchar(30) not null, -- varchar(4000) -- type in mysql
	  field_toupper	     varchar (3) not null default 'YES', --yes or no do we upper case the entry
	  field_null		varchar(3) not null, -- YES or NO
	  field_key		varchar(3) not null, -- PRI, YES, blank
        -- e.g., check foobar in ('christof', 'patrick'), autoincrement
        extra_sql                varchar(4000) not null,
        -- values are 'text', 'textarea', 'select', 'radio',
          -- 'selectmultiple', 'checkbox', 'checkboxmultiple', 'selectsql'
        html_form_type        varchar(100) not null,
        -- e.g., for textarea, this would be rows=6 cols=60, for select, Tcl list,
        -- for selectsql, an SQL query that returns N district values
        -- for email addresses mailto:
        html_form_options      varchar(4000) not null,
        -- pretty_name is going to be the short prompt,
           -- e.g., for an update page, but we also need something
           -- longer if we have to walk the user through a long form
        html_form_explanation         varchar(4000) not null,
           -- if they click for yet more help
	  validation_proc		varchar(4000) not null, --data entry validation procedure name
        help_text                  varchar(4000) not null,
        -- note that this does NOT translate into a not null constraint in Oracle
        -- if we did this, it would preclude an interface in which users create rows incrementally
         mandatory_p                char(1) not null,
         -- ordering in Oracle table creation, 0 would be on top, 1 underneath, etc.
         sort_key                    integer not null,
         -- ordering within a form, lower number = higher on page
         form_sort_key               integer not null,
         -- if there are N forms, starting with 0, to define this object,
            -- on which does this go? (relevant for very complex objects where
            -- you need more than one page to submit)
         form_number                  integer not null,
         -- for full text index
         -- include_in_ctx_index_p char(1) check (include_in_ctx_index_p in ('t','f')),
	 --
         -- add forms should be prefilled with the default value
         default_value                 varchar(200) not null,
           -- check ((abstract_data_type not in ('user') and oracle_data_type is not null)
                  -- or
                -- (abstract_data_type in ('user'))),
         unique(table_name,column_name)
)";


//This following table is to hold the internal variables that aren't in the database.  For example returnmsg, db, ...

$qtable3 = "create table if not exists metadata_variables  (
        table_name              varchar(21) primary key,
        var_name             varchar(100) not null,
        var_pretty           varchar(100),
	abstract_data_type       varchar(30) not null, -- ie. text or shorttext or boolean or user
          -- this one is not null except when abstract_data_type is user
	html_form_type        varchar(100) not null,
        -- e.g., for textarea, this would be rows=6 cols=60, for select, Tcl list,
        -- for selectsql, an SQL query that returns N district values
        -- for email addresses mailto:
        html_form_options      varchar(4000) not null,
        -- pretty_name is going to be the short prompt,
           -- e.g., for an update page, but we also need something
           -- longer if we have to walk the user through a long form
        html_form_explanation         varchar(4000) not null,
           -- if they click for yet more help
)";


require_once 'db.php';
$SERVER="localhost";
$USER="webcal";
$PASS="webcal";
$thisdb = new my_db($SERVER, $USER, $PASS, $DBNAME);
$thisdb->SetQuery($qdb);
$thisdb->Query();
$thisdb->SetQuery($quse);
$thisdb->Query();
$thisdb->SetQuery($qtable1);
$thisdb->Query();
$thisdb->SetQuery($qtable2);
$thisdb->Query();
$thisdb->SetQuery($qtable3);
$thisdb->Query();

echo "Please check that a new db and 3 tables exist<br />";





?>
