-- Migration: extend seg_funds with the full RBC Lipper column set
-- Source: https://lipper.rbcinsurance.com/rbc/list (tabs: Fund Details, Short Term,
--         Long Term, Calendar Year, Quartile Rankings, Buy Guide) + the email-gateway
--         CSV rbc_gif_funds_2026-08-17.csv.
-- Run on the stockmarket-app DB host (local MySQL is not running on the dev box).
-- One-time; review before re-running (MySQL ALTER has no IF NOT EXISTS per column
-- prior to 8.0.29 — for 5.7 guard each ADD with a pre-check if re-running).
--
-- Design note: calendar-year returns (2016-2025, and future years) are stored in a
-- normalized child table seg_fund_calendar_returns rather than 10 fixed columns, so
-- new years need no further ALTER. All other values are per-fund scalars on seg_funds.

ALTER TABLE `seg_funds`
    ADD COLUMN `fund_code`          VARCHAR(32)  NULL DEFAULT NULL,
    ADD COLUMN `currency`           VARCHAR(8)   NULL DEFAULT NULL,   -- e.g. CAD
    ADD COLUMN `asset_type`         VARCHAR(64)  NULL DEFAULT NULL,   -- e.g. Mixed Assets
    ADD COLUMN `asset_class`        VARCHAR(64)  NULL DEFAULT NULL,   -- e.g. Canadian Neutral Balanced
    ADD COLUMN `launch_date`        DATE          NULL DEFAULT NULL,
    ADD COLUMN `aum_millions`       DECIMAL(12,2) NULL DEFAULT NULL,

    -- Short Term tab
    ADD COLUMN `nav`                DECIMAL(10,4) NULL DEFAULT NULL,
    ADD COLUMN `day_change_dollars` DECIMAL(10,4) NULL DEFAULT NULL,
    ADD COLUMN `day_change_pct`     DECIMAL(8,4)  NULL DEFAULT NULL,
    ADD COLUMN `week_pct`           DECIMAL(8,4)  NULL DEFAULT NULL,   -- 1 Week %
    ADD COLUMN `mtd_pct`            DECIMAL(8,4)  NULL DEFAULT NULL,   -- MTD %
    ADD COLUMN `return_30day_pct`   DECIMAL(8,4)  NULL DEFAULT NULL,   -- 30 Day %
    ADD COLUMN `ytd_pct`            DECIMAL(8,4)  NULL DEFAULT NULL,   -- YTD %

    -- Extra trailing windows present in the CSV export
    ADD COLUMN `return_1mo`         DECIMAL(8,4)  NULL DEFAULT NULL,
    ADD COLUMN `return_3mo`         DECIMAL(8,4)  NULL DEFAULT NULL,

    -- Long Term tab extras (1/3/5/10yr already exist)
    ADD COLUMN `return_15yr`        DECIMAL(8,4)  NULL DEFAULT NULL,
    ADD COLUMN `return_inception`   DECIMAL(8,4)  NULL DEFAULT NULL,

    -- Buy Guide tab
    ADD COLUMN `std_dev`            DECIMAL(8,4)  NULL DEFAULT NULL,
    ADD COLUMN `mer_pct`            DECIMAL(6,3)  NULL DEFAULT NULL,   -- full MER (existing `mer` stores mgmt fee)
    ADD COLUMN `load_type`          VARCHAR(8)    NULL DEFAULT NULL,   -- OPT / F / etc.
    ADD COLUMN `min_initial_investment` DECIMAL(12,2) NULL DEFAULT NULL,
    ADD COLUMN `subsequent_investment`  DECIMAL(12,2) NULL DEFAULT NULL,
    ADD COLUMN `rrsp_eligible`      TINYINT(1)    NULL DEFAULT NULL,

    -- Fundamentals (CSV)
    ADD COLUMN `num_securities`     INT           NULL DEFAULT NULL,
    ADD COLUMN `pe`                 DECIMAL(10,2) NULL DEFAULT NULL,
    ADD COLUMN `pb`                 DECIMAL(10,2) NULL DEFAULT NULL,
    ADD COLUMN `eps_growth`         DECIMAL(10,2) NULL DEFAULT NULL,
    ADD COLUMN `div_yield`          DECIMAL(8,4)  NULL DEFAULT NULL,
    ADD COLUMN `volatility`         DECIMAL(8,4)  NULL DEFAULT NULL,

    -- Quartile Rankings tab (1/2/3, NULL when not applicable)
    ADD COLUMN `quartile_ytd`       TINYINT       NULL DEFAULT NULL,
    ADD COLUMN `quartile_1yr`       TINYINT       NULL DEFAULT NULL,
    ADD COLUMN `quartile_3yr`       TINYINT       NULL DEFAULT NULL,
    ADD COLUMN `quartile_5yr`       TINYINT       NULL DEFAULT NULL,
    ADD COLUMN `quartile_10yr`      TINYINT       NULL DEFAULT NULL,
    ADD COLUMN `quartile_15yr`      TINYINT       NULL DEFAULT NULL,

    -- Fund facts PDF / buy guide hosted locally (path set by the refresh job)
    ADD COLUMN `pdf_path`           VARCHAR(255)  NULL DEFAULT NULL;

CREATE TABLE IF NOT EXISTS `seg_fund_calendar_returns` (
    `id`         INT          NOT NULL AUTO_INCREMENT,
    `fund_id`    INT          NOT NULL,
    `cal_year`   INT          NOT NULL,
    `return_pct` DECIMAL(8,4) NULL DEFAULT NULL,
    PRIMARY KEY (`id`),
    UNIQUE KEY `uq_fund_year` (`fund_id`, `cal_year`),
    CONSTRAINT `fk_cal_return_fund` FOREIGN KEY (`fund_id`)
        REFERENCES `seg_funds` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
