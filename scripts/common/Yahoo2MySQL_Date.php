//Yahoo returns dates as MM/DD/YY
//where MySQL expects YYYY-MM-DD

function Yahoo2MySql_Date( $date )
{
	return date( 'Y-m-d', strtotime($date) ) ;
}
