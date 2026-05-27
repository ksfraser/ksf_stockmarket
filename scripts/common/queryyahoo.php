<?php

function QueryYahoo( $stock, $stockexchange = "" )
{
/* 20130904 KF this looks like it returns 1 line of data
     What happens if the CSV has multiple lines?
*/

//$query = "http://finance.yahoo.com/d/quotes.csv?s=CP.TO&f=sl1d1t1c1ohgva2pm3m4bb6aa5&e=.csv";
//$query = "http://finance.yahoo.com/d/quotes.csv?s=CNR.TO&f=sl1d1t1c1ohgva2pm3m4bb6aa5&e=.csv";

if( strlen($stockexchange) > 0)
{
        $symbol = $stock . "." . $stockexchange;
}
else
{
        $symbol = $stock;
}

$query = "http://finance.yahoo.com/d/quotes.csv?s=" . $symbol . "&f=sl1d1t1c1ohgva2pm3m4bb6aa5&e=.csv";
//echo $query . "\n";

$text = webpage2txt( $query );
//echo $text;
$fp = fopen( "../currentdata/" . $symbol . ".html", "w" );
fwrite( $fp, $text );
fclose ( $fp );
$fields = parse_line( $text );
//var_dump( $fields );

/* Yahoo CSV format:
*
*       Symbol,
*       last trade,
*       trade date,
*       trade time,
*       change,
*       open,
*       high,
*       low,
*       volume,
*       average volume,
*       prev close,
*       after hours price,
*       unknown,
*       bid,
*       bidsize,
*       ask,
*       asksize
*
*/
/*A dictionary of fields, and their relationship to YAHOO queries*/
/*
$toolfields = array ('stocksymbol',  //stockinfo
              'corporatename',  //stockinfo
              'Last Trade (With Time)',
              'Last Trade (Price Only)',
              'asofdate',  //stockinfo
              'Last Trade Time',
              'Last Trade Size',
              'Change and Percent Change',
              'Change',
              'Change in Percent',
              'Ticker Trend',
              'averagevolume',  //stockinfo
              'dailyvolume', //stockinfo
              'More Info',
              'Trade Links',
              'Bid',
              'Bid Size',
              'currentprice',   //stockinfo
              'Ask Size',
              'Previous Close',
              'Open',
              "Day's Range",
              '52-week Range',
              'Change From 52-wk Low',
              'Pct Chg From 52-wk Low',
              'Change From 52-wk High',
              'Pct Chg From 52-wk High',
              'EPS',    //stockinfo
              'P/E Ratio',
              'Short Ratio',
              'Dividend Pay Date',
              'Ex-Dividend Date',
              'Dividend/Share',
              'dividendyield',  //portfolio
              'Float Shares',
              'Market Capitalization',
              '1yr Target Price',
              'EPS Est. Current Yr',
              'EPS Est. Next Year',
              'EPS Est. Next Quarter',
              'Price/EPS Est. Current Yr',
              'Price/EPS Est. Next Yr',
              'PEG Ratio',
              'Book Value',
              'Price/Book',
              'Price/Sales',
              'EBITDA',
              '50-day Moving Avg',
              'Change From 50-day Moving Avg',
              'Pct Chg From 50-day Moving Avg',
              '200-day Moving Avg',
              'Change From 200-day Moving Avg',
              'Pct Chg From 200-day Moving Avg',
              'Shares Owned',
              'Price Paid',
              'Commission',
              'Holdings Value',
 	       "Day's Value Change",
              'Holdings Gain Percent',
              'Holdings Gain',
              'Trade Date',
              'Annualized Gain',
              'High Limit',
              'Low Limit',
              'Notes',
              'Last Trade (Real-time) with Time',
              'Bid (Real-time)',
              'Ask (Real-time)',
              'Change Percent (Real-time)',
              'Change (Real-time)',
              'Holdings Value (Real-time)',
              "Day's Value Change (Real-time)",
              'Holdings Gain Pct (Real-time)',
              'Holdings Gain (Real-time)',
              "Day's Range (Real-time)",
              'marketcap',      //stockinfo
              'peratio',        //stockinfo
              'After Hours Change (Real-time)',
              'Order Book (Real-time)',
              'Stock Exchange'
             );

$yahoofields = array ('Symbol'
              'Name'
              'Last Trade (With Time)'
              'Last Trade (Price Only)'
              'Last Trade Date'
              'Last Trade Time'
              'Last Trade Size'
              'Change and Percent Change'
              'Change'
              'Change in Percent'
              'Ticker Trend'
              'Volume'
              'Average Daily Volume'
              'More Info'
              'Trade Links'
              'Bid'
              'Bid Size'
              'Ask'
              'Ask Size'
              'Previous Close'
              'Open'
              "Day's Range"
              '52-week Range'
              'Change From 52-wk Low'
              'Pct Chg From 52-wk Low'
              'Change From 52-wk High'
              'Pct Chg From 52-wk High'
              'Earnings/Share'
              'P/E Ratio'
              'Short Ratio'
              'Dividend Pay Date'
              'Ex-Dividend Date'
              'Dividend/Share'
              'Dividend Yield'
              'Float Shares'
              'Market Capitalization'
              '1yr Target Price'
              'EPS Est. Current Yr'
              'EPS Est. Next Year'
              'EPS Est. Next Quarter'
              'Price/EPS Est. Current Yr'
              'Price/EPS Est. Next Yr'
              'PEG Ratio'
              'Book Value'
              'Price/Book'
              'Price/Sales'
              'EBITDA'
              '50-day Moving Avg'
              'Change From 50-day Moving Avg'
              'Pct Chg From 50-day Moving Avg'
              '200-day Moving Avg'
              'Change From 200-day Moving Avg'
              'Pct Chg From 200-day Moving Avg'
              'Shares Owned'
              'Price Paid'
              'Commission'
              'Holdings Value'
              "Day's Value Change"
              'Holdings Gain Percent'
              'Holdings Gain'
              'Trade Date'
              'Annualized Gain'
              'High Limit'
              'Low Limit'
              'Notes'
              'Last Trade (Real-time) with Time'
              'Bid (Real-time)'
              'Ask (Real-time)'
              'Change Percent (Real-time)'
              'Change (Real-time)'
              'Holdings Value (Real-time)'
              "Day's Value Change (Real-time)"
              'Holdings Gain Pct (Real-time)
              'Holdings Gain (Real-time)'
              "Day's Range (Real-time)"
              'Market Cap (Real-time)'
              'P/E (Real-time)'
              'After Hours Change (Real-time)'
              'Order Book (Real-time)'
              'Stock Exchange'
             );

array yahoogetfields = ('Symbol'                                =>  's',        # old default
              'Name'                            =>  'n',        # old default
              'Last Trade (With Time)'          =>  'l',
              'Last Trade (Price Only)'         =>  'l1',       # old default
              'Last Trade Date'                 =>  'd1',       # old default
              'Last Trade Time'                 =>  't1',       # old default
              'Last Trade Size'                 =>  'k3',
              'Change and Percent Change'       =>  'c',
              'Change'                          =>  'c1',       # old default
              'Change in Percent'               =>  'p2',       # old default
              'Ticker Trend'                    =>  't7',
              'Volume'                          =>  'v',        # old default
              'Average Daily Volume'            =>  'a2',       # old default
              'More Info'                       =>  'i',
              'Trade Links'                     =>  't6',
              'Bid'                             =>  'b',        # old default
              'Bid Size'                        =>  'b6',
              'Ask'                             =>  'a',        # old default
              'Ask Size'                        =>  'a5',
              'Previous Close'                  =>  'p',        # old default
              'Open'                            =>  'o',        # old default
              "Day's Range"                     =>  'm',        # old default
              '52-week Range'                   =>  'w',        # old default
              'Change From 52-wk Low'           =>  'j5',
              'Pct Chg From 52-wk Low'          =>  'j6',
              'Change From 52-wk High'          =>  'k4',
              'Pct Chg From 52-wk High'         =>  'k5',
              'Earnings/Share'                  =>  'e',        # old default
              'P/E Ratio'                       =>  'r',        # old default
              'Short Ratio'                     =>  's7',
              'Dividend Pay Date'               =>  'r1',       # old default
              'Ex-Dividend Date'                =>  'q',
              'Dividend/Share'                  =>  'd',        # old default
              'Dividend Yield'                  =>  'y',        # old default
              'Float Shares'                    =>  'f6',
              'Market Capitalization'           =>  'j1',       # old default
              '1yr Target Price'                =>  't8',
              'EPS Est. Current Yr'             =>  'e7',
              'EPS Est. Next Year'              =>  'e8',
              'EPS Est. Next Quarter'           =>  'e9',
              'Price/EPS Est. Current Yr'       =>  'r6',
              'Price/EPS Est. Next Yr'          =>  'r7',
              'PEG Ratio'                       =>  'r5',
              'Book Value'                      =>  'b4',
              'Price/Book'                      =>  'p6',
              'Price/Sales'                     =>  'p5',
              'EBITDA'                          =>  'j4',
              '50-day Moving Avg'               =>  'm3',
              'Change From 50-day Moving Avg'   =>  'm7',
              'Pct Chg From 50-day Moving Avg'  =>  'm8',
              '200-day Moving Avg'              =>  'm4',
              'Change From 200-day Moving Avg'  =>  'm5',
              'Pct Chg From 200-day Moving Avg' =>  'm6',
              'Shares Owned'                    =>  's1',
              'Price Paid'                      =>  'p1',
              'Commission'                      =>  'c3',
              'Holdings Value'                  =>  'v1',
              "Day's Value Change"              =>  'w1',
             'Holdings Gain Percent'           =>  'g1',
              'Holdings Gain'                   =>  'g4',
              'Trade Date'                      =>  'd2',
              'Annualized Gain'                 =>  'g3',
              'High Limit'                      =>  'l2',
              'Low Limit'                       =>  'l3',
              'Notes'                           =>  'n4',
              'Last Trade (Real-time) with Time'=>  'k1',
              'Bid (Real-time)'                 =>  'b3',
              'Ask (Real-time)'                 =>  'b2',
              'Change Percent (Real-time)'      =>  'k2',
              'Change (Real-time)'              =>  'c6',
              'Holdings Value (Real-time)'      =>  'v7',
              "Day's Value Change (Real-time)"  =>  'w4',
              'Holdings Gain Pct (Real-time)'   =>  'g5',
              'Holdings Gain (Real-time)'       =>  'g6',
              "Day's Range (Real-time)"         =>  'm2',
              'Market Cap (Real-time)'          =>  'j3',
              'P/E (Real-time)'                 =>  'r2',
              'After Hours Change (Real-time)'  =>  'c8',
              'Order Book (Real-time)'          =>  'i5',
		'ask'				=>  'a',
              'Stock Exchange'                  =>  'x'         # old default
             );
*/
//20100824 KF Adding check for $fields being set
if( isset( $fields[0] ))
{
        $stockarray['symbol'] = $fields[0];
        $stockarray['last trade'] = $fields[1];
        $stockarray['trade date'] = $fields[2];
        $stockarray['trade time'] = $fields[3];
        $stockarray['dailychange'] = $fields[4];
        $stockarray['open'] = $fields[5];
        $stockarray['high'] = $fields[6];
        $stockarray['low'] = $fields[7];
        $stockarray['volume'] = $fields[8];
        $stockarray['average volume'] = $fields[9];
        $stockarray['prev close'] = $fields[10];
        $stockarray['after hours price'] = $fields[11];
        $stockarray['oneyeartarget'] = $fields[12];
        $stockarray['bid'] = $fields[13];
        $stockarray['bidsize'] = $fields[14];
        $stockarray['ask'] = $fields[15];
        $stockarray['asksize'] = $fields[16];
}
else
{
        echo "No data parsed for stock" . $stock . "\n";
        return NULL;
}
//20100824 !fields check


//var_dump( $stockarray );
return $stockarray;

}

?>
