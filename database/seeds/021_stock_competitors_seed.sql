-- Seed data for stock_competitors
-- Competitor/peer mappings for the portfolio + watchlist symbols.

INSERT IGNORE INTO stock_competitors (symbol, competitor, is_primary, notes) VALUES

-- MX (Methanex) — Basic Materials / Chemicals — methanol producer
('MX','CE',1,'Celanese — global acetyl/chain extender & specialty chemicals, closest public peer in chemicals manufacturing'),
('MX','LYB',1,'LyondellBasell — polymers & chemicals, large-cap chem peer'),
('MX','DOW',1,'Dow Inc — diversified chemicals, US-based global peer'),
('MX','BASFY',0,'BASF (ADR) — German chemical giant, global benchmark'),
('MX','SNP',0,'Sinopec — China petchem giant, relevant for Asian methanol demand context')
;

INSERT IGNORE INTO stock_competitors (symbol, competitor, is_primary, notes) VALUES

-- CNR (Canadian National Railway) — Industrials / Railroads
('CNR','CP',1,'Canadian Pacific Kansas City — direct Canadian rail duopoly competitor'),
('CNR','UNP',1,'Union Pacific — largest US western railroad, NA rail benchmark'),
('CNR','NSC',1,'Norfolk Southern — eastern US rail, NA rail comparator'),
('CNR','CSX',1,'CSX — eastern US rail, NA rail comparator')
;

INSERT IGNORE INTO stock_competitors (symbol, competitor, is_primary, notes) VALUES

-- RUS (Russel Metals) — Industrials / Industrial Distribution — metals distribution
('RUS','FTT',1,'Finning International — Caterpillar dealer, largest Canadian industrial distributor peer'),
('RUS','TIH',1,'Toromont Industries — CAT/GenSet dealer, Canadian industrial distribution peer'),
('RUS','RCH',1,'Richelieu Hardware — Canadian industrial/hardware distributor, distribution peer'),
('RUS','DBM',1,'Doman Building Materials — Canadian building products distributor')
;

INSERT IGNORE INTO stock_competitors (symbol, competitor, is_primary, notes) VALUES

-- MTY (MTY Food Group) — Consumer Cyclical / Restaurants — multi-brand QSR franchisor
('MTY','QSR',1,'Restaurant Brands International — owns Burger King, Tim Hortons, Popeyes (direct QSR franchise peer)'),
('MTY','DPZ',1,'Domino''s — global QSR pizza delivery, pizza segment peer'),
('MTY','YUM',1,'Yum! Brands — KFC/Pizza Hut/Taco Bell, global QSR franchise model peer'),
('MTY','SBUX',0,'Starbucks — food service/restaurant peer, different model but sector comparator'),
('MTY','MCD',0,'McDonald''s — global QSR benchmark')
;

INSERT IGNORE INTO stock_competitors (symbol, competitor, is_primary, notes) VALUES

-- WJX (Wajax) — Industrials / Industrial Distribution — equipment & parts distributor
('WJX','FTT',1,'Finning International — Caterpillar dealer, Canadian industrial equipment distribution peer'),
('WJX','TIH',1,'Toromont Industries — CAT/GenSet dealer, Canadian equipment distribution peer')
;

INSERT IGNORE INTO stock_competitors (symbol, competitor, is_primary, notes) VALUES

-- SRV.UN (SIR Royalty Income Fund) — Consumer Cyclical / Restaurants — restaurant royalty trust
('SRV.UN','BPF.UN',1,'Boston Pizza Royalties — Canadian restaurant royalty trust, direct model peer'),
('SRV.UN','PZA',0,'Pizza Pizza Royalty — Canadian restaurant royalty trust, royalty model comparator')
;

INSERT IGNORE INTO stock_competitors (symbol, competitor, is_primary, notes) VALUES

-- PZA (Pizza Pizza Royalty) — Consumer Cyclical / Restaurants — pizza QSR royalty
('PZA','QSR',1,'Restaurant Brands International — Tim Hortons/Burger King/Popeyes, Canadian QSR royalty context'),
('PZA','DPZ',1,'Domino''s — global pizza QSR, pizza segment direct competitor'),
('PZA','MTY',0,'MTY Food Group — multi-brand QSR franchisor, Canadian food service peer'),
('PZA','BPF.UN',0,'Boston Pizza Royalties — Canadian restaurant royalty trust, royalty model peer')
;

INSERT IGNORE INTO stock_competitors (symbol, competitor, is_primary, notes) VALUES

-- BPF.UN (Boston Pizza Royalties) — Consumer Cyclical / Restaurants — restaurant royalty
('BPF.UN','PZA',1,'Pizza Pizza Royalty — Canadian restaurant royalty trust, direct royalty model peer'),
('BPF.UN','SRV.UN',1,'SIR Royalty Income Fund — Canadian restaurant royalty trust, royalty model peer'),
('BPF.UN','QSR',0,'Restaurant Brands International — Canadian QSR context (Tim Hortons owner)'),
('BPF.UN','MTY',0,'MTY Food Group — Canadian multi-brand restaurant franchisor')
;

INSERT IGNORE INTO stock_competitors (symbol, competitor, is_primary, notes) VALUES

-- IEV / FEZ / SPEU — Europe Stock ETFs (region/asset exposure, not company competitors)
('IEV','SPY',1,'SPDR S&P 500 ETF — US large-cap benchmark, compare developed-market region exposure'),
('IEV','QQQ',0,'Invesco QQQ — tech-heavy US ETF, growth benchmark contrast'),
('FEZ','SPY',1,'SPDR S&P 500 ETF — US benchmark vs Euro STOXX 50 exposure'),
('FEZ','IEV',0,'iShares Europe ETF — overlapping European developed-market exposure'),
('SPEU','SPY',1,'SPDR S&P 500 ETF — US benchmark vs S&P Europe exposure'),
('SPEU','IEV',0,'iShares Europe ETF — overlapping European developed exposure'),
('SPEU','FEZ',0,'SPDR Euro STOXX 50 — overlapping Eurozone large-cap exposure')
;

INSERT IGNORE INTO stock_competitors (symbol, competitor, is_primary, notes) VALUES

-- PMDIY — Health Services (palladium mining/streaming ETF)
('PMDIY','PALL',1,'ETFS Palladium Trust — direct palladium ETF peer (other side of same market)'),
('PMDIY','STL',1,'Sibanye-Stillwater — palladium/platinum miner, underlying commodity exposure peer'),
('PMDIY','PLG',1,'Anglo American Platinum — major PGE producer, commodity exposure peer'),
('PMDIY','IMPUY',0,'Impala Platinum (ADR) — South African PGE miner, palladium exposure peer')
;

INSERT IGNORE INTO stock_competitors (symbol, competitor, is_primary, notes) VALUES

-- VET.TO (Vermilion Energy) — Energy / Oil & Gas E&P
('VET.TO','ARX',1,'ARC Resources — Canadian E&P, natural gas/liquids peer'),
('VET.TO','TOU',1,'Tourmaline Oil — Canadian natural gas E&P, peer in Canadian energy'),
('VET.TO','WCP',1,'Whitecap Resources — Canadian E&P, oil-weighted Canadian peer'),
('VET.TO','PXT',0,'Pembina Pipeline — Canadian energy infrastructure, energy sector comparator')
;

INSERT IGNORE INTO stock_competitors (symbol, competitor, is_primary, notes) VALUES

-- GLD — Commodities Focused / Gold ETF
('GLD','IAU',1,'iShares Gold Trust — direct gold ETF peer, lower-fee alternative'),
('GLD','GLDM',1,'SPDR Gold MiniShares — gold ETF peer, expense-ratio comparison'),
('GLD','PHYS',0,'Sprott Physical Gold Trust — physical gold trust, different structure but same exposure'),
('GLD','SGOL',0,'abrdn Physical Gold ETF — physical gold, European custody alternative')
;

INSERT IGNORE INTO stock_competitors (symbol, competitor, is_primary, notes) VALUES

-- RGLD (Royal Gold) — Basic Materials / Gold — gold royalty & streaming
('RGLD','FNV',1,'Franco-Nevada — largest gold royalty/streaming company, direct peer in royalty model'),
('RGLD','WPM',1,'Wheaton Precious Metals — gold & silver streaming, direct royalty peer'),
('RGLD','SA',1,'Sandstorm Gold — gold royalty/streaming, smaller royalty peer'),
('RGLD','GOLD',0,'Barrick Gold — major gold miner, underlying commodity producer contrast to royalty model'),
('RGLD','ABX',0,'AngloGold Ashanti — gold miner, commodity producer contrast')
;
