<?php

//20090813 KF
//MACD
//http://stockcharts.com/school/doku.php?id=chart_school:technical_indicators:moving_average_conve

/*
Moving Average Convergence/Divergence (MACD)
Introduction

Developed by Gerald Appel, Moving Average Convergence/Divergence (MACD) is one of the simplest and most reliable indicators available. MACD uses moving averages, which are lagging indicators, to include some trend-following characteristics. These lagging indicators are turned into a momentum oscillator by subtracting the longer moving average from the shorter moving average. The resulting plot forms a line that oscillates above and below zero, without any upper or lower limits. MACD is a centered oscillator and the guidelines for using centered oscillators apply.

MACD Formula

The most popular formula for the "standard" MACD is the difference between a security's 26-day and 12-day Exponential Moving Averages (EMAs). This is the formula that is used in many popular technical analysis programs, including SharpCharts, and quoted in most technical analysis books on the subject. Appel and others have since tinkered with these original settings to come up with a MACD that is better suited for faster or slower securities. Using shorter moving averages will produce a quicker, more responsive indicator, while using longer moving averages will produce a slower indicator, less prone to whipsaws. For our purposes in this article, the traditional 12/26 MACD will be used for explanations. Later in the indicator series, we will address the use of different moving averages in calculating MACD.

Of the two moving averages that make up MACD, the 12-day EMA is the faster and the 26-day EMA is the slower. Closing prices are used to form the moving averages. Usually, a 9-day EMA of MACD is plotted along side to act as a trigger line. A bullish crossover occurs when MACD moves above its 9-day EMA, and a bearish crossover occurs when MACD moves below its 9-day EMA. The Merrill Lynch (MER)[Mer] chart below shows the 12-day EMA (thin blue line) with the 26-day EMA (thin red line) overlaid the price plot. MACD appears in the box below as the thick black line and its 9-day EMA is the thin blue line. The histogram represents the difference between MACD and its 9-day EMA. The histogram is positive when MACD is above its 9-day EMA and negative when MACD is below its 9-day EMA.

Merrill Lynch & Co., Inc. (MER) MACD example chart from StockCharts.com
What Does MACD Do?

MACD measures the difference between two Exponential Moving Averages (EMAs). A positive MACD indicates that the 12-day EMA is trading above the 26-day EMA. A negative MACD indicates that the 12-day EMA is trading below the 26-day EMA. If MACD is positive and rising, then the gap between the 12-day EMA and the 26-day EMA is widening. This indicates that the rate-of-change of the faster moving average is higher than the rate-of-change for the slower moving average. Positive momentum is increasing, indicating a bullish period for the price plot. If MACD is negative and declining further, then the negative gap between the faster moving average (blue) and the slower moving average (red) is expanding. Downward momentum is accelerating, indicating a bearish period of trading. MACD centerline crossovers occur when the faster moving average crosses the slower moving average.

Merrill Lynch &amp; Co., Inc. (MER) MACD example chart from StockCharts.com

This Merrill Lynch (MER)[Mer] chart shows MACD as a solid black line, and its 9-day EMA as the thin blue line. Even though moving averages are lagging indicators, notice that MACD moves faster than the moving averages. In this example, MACD provided a few good trading signals as well:

   1.
      In March and April, MACD turned down ahead of both moving averages, and formed a negative divergence ahead of the price peak.
   2.
      In May and June, MACD began to strengthen and make higher Lows while both moving averages continued to make lower Lows.
   3.
      Finally, MACD formed a positive divergence in October while both moving averages recorded new Lows.

MACD Bullish Signals

MACD generates bullish signals from three main sources:

   1.
      Positive Divergence
   2.
      Bullish Moving Average Crossover
   3.
      Bullish Centerline Crossover

Positive Divergence

Novellus Systems, Inc. (NVLS) MACD example chart from StockCharts.com

A Positive Divergence occurs when MACD begins to advance and the security is still in a downtrend and makes a lower reaction low. MACD can either form as a series of higher Lows or a second Low that is higher than the previous Low. Positive Divergences are probably the least common of the three signals, but are usually the most reliable, and lead to the biggest moves.
Bullish Moving Average Crossover

Novellus Systems, Inc. (NVLS) MACD example chart from StockCharts.com

A Bullish Moving Average Crossover occurs when MACD moves above its 9-day EMA, or trigger line. Bullish Moving Average Crossovers are probably the most common signals and as such are the least reliable. If not used in conjunction with other technical analysis tools, these crossovers can lead to whipsaws and many false signals. Bullish Moving Average Crossovers are used occasionally to confirm a positive divergence. A positive divergence can be considered valid when a Bullish Moving Average Crossover occurs after the MACD Line makes its second "higher Low".

Sometimes it is prudent to apply a price filter to the Bullish Moving Average Crossover to ensure that it will hold. An example of a price filter would be to buy if MACD breaks above the 9-day EMA and remains above for three days. The buy signal would then commence at the end of the third day.
Bullish Centerline Crossover

Apple Computer, Inc. (AAPL) MACD example chart from StockCharts.com

A Bullish Centerline Crossover occurs when MACD moves above the zero line and into positive territory. This is a clear indication that momentum has changed from negative to positive, or from bearish to bullish. After a Positive Divergence and Bullish Centerline Crossover, the Bullish Centerline Crossover can act as a confirmation signal. Of the three signals, moving average crossover are probably the second most common signals.
Using a Combination of Signals

Halliburton Co. (HAL) MACD example chart from StockCharts.com

Even though some traders may use only one of the above signals to form a buy or a sell signal, using a combination can generate more robust signals. In the Halliburton (HAL)[Hal] example, all three bullish signals were present and the stock still advanced another 20%. The stock formed a lower Low at the end of February, but MACD formed a higher Low, thus creating a potential Positive Divergence. MACD then formed a Bullish Moving Average Crossover by moving above its 9-day EMA. And finally, MACD traded above zero to form a Bullish Centerline Crossover. At the time of the Bullish Centerline Crossover, the stock was trading at 32 1/4 and went above 40 immediately after that. In August, the stock traded above 50.

Bearish Signals

MACD generates bearish signals from three main sources. These signals are mirror reflections of the bullish signals:

   1.
      Negative Divergence
   2.
      Bearish Moving Average Crossover
   3.
      Bearish Centerline Crossover

Negative Divergence

A Negative Divergence forms when the security advances or moves sideways, and the MACD declines. The Negative Divergence in MACD can take the form of either a lower High or a straight decline. Negative Divergences are probably the least common of the three signals, but are usually the most reliable, and can warn of an impending peak.

FedEx Corp. (FDX) MACD example chart from StockCharts.com

The FedEx (FDX)[Fdx] chart shows a Negative Divergence when MACD formed a lower High in May, and the stock formed a higher High at the same time. This was a rather blatant Negative Divergence, and signaled that momentum was slowing. A few days later, the stock broke the uptrend line, and the MACD formed a lower Low.

There are two possible means of confirming a Negative Divergence. First, the indicator can form a lower Low. This is traditional peak-and-trough analysis applied to an indicator. With the lower High and subsequent lower Low, the uptrend for MACD has changed from bullish to bearish. Second, a Bearish Moving Average Crossover (which is explained below) can act to confirm a negative divergence. As long as MACD is trading above its 9-day EMA, or trigger line, it has not turned down and the lower High is difficult to confirm. When MACD breaks below its 9-day EMA, it signals that the short-term trend for the indicator is weakening, and a possible interim peak has formed.
Bearish Moving Average Crossover

The most common signal for MACD is the moving average crossover. A Bearish Moving Average Crossover occurs when MACD declines below its 9-day EMA. Not only are these signals the most common, but they also produce the most false signals. As such, moving average crossovers should be confirmed with other signals to avoid whipsaws and false readings.

Merck & Co., Inc. (MRK) MACD example chart from StockCharts.com

Sometimes a stock can be in a strong uptrend, and MACD will remain above its trigger line for a sustained period of time. In this case, it is unlikely that a Negative Divergence will develop. A different signal is needed to identify a potential change in momentum. This was the case with Merck (MRK)[Mrk] in February and March. The stock advanced in a strong uptrend, and MACD remained above its 9-day EMA for 7 weeks. When a Bearish Moving Average Crossover occurred, it signaled that upside momentum was slowing. This slowing momentum should have served as an alert to monitor the technical situation for further clues of weakness. Weakness was soon confirmed when the stock broke its uptrend line and MACD continued its decline and moved below zero.
Bearish Centerline Crossover

A Bearish Centerline Crossover occurs when MACD moves below zero and into negative territory. This is a clear indication that momentum has changed from positive to negative, or from bullish to bearish. The centerline crossover can act as an independent signal, or confirm a prior signal such as a moving average crossover or negative divergence. Once MACD crosses into negative territory, momentum, at least for the short term, has turned bearish.

Unisys Corp. (UIS) MACD example chart from StockCharts.com

The significance of the centerline crossover will depend on the previous movements of MACD as well. If MACD is positive for many weeks, begins to trend down, and then crosses into negative territory, it would be bearish. However, if MACD has been negative for a few months, breaks above zero, and then back below, it might be a correction. In order to judge the significance of a centerline crossover, traditional technical analysis can be applied to see if there has been a change in trend, higher High or lower Low.

The Unisys (UIS)[Uis] chart depicts a Bearish Centerline Crossover that preceded a 25% drop in the stock that occurs just off the right edge of the chart. Although there was little time to act once this signal appeared, there were other warnings signs prior to the dramatic drop:

   1.
      After the drop to trend line support, a Bearish Moving Average Crossover formed.
   2.
      When the stock rebounded from the drop, MACD did not even break above the trigger line, indicating weak upside momentum.
   3.
      The peak of the reaction rally was marked by a shooting star candlestick (blue arrow) and a gap down on increased volume (red arrows).
   4.
      After the gap down, the blue trend line was broken.

In addition to the signals mentioned above, a Bearish Centerline Crossover occurred after MACD had been above zero for almost two months. From 20 Sept on, MACD had been weakening and momentum was slowing. The break below zero acted as the final straw of a long weakening process.
Combining Signals

As with bullish MACD signals, bearish signals can be combined to create more robust signals. In most cases, stocks fall faster than they rise. This was definitely the case with Unisys (UIS), and only two bearish MACD signals were present. Using momentum indicators like MACD, technical analysis can sometimes provide clues to impending weakness. While it may be impossible to predict the length and duration of the decline, being able to spot weakness can enable traders to take a more defensive position.

Intel Corp. (INTC) MACD example chart from StockCharts.com

In 2002, Intel (INTC)[Intc] dropped from above 36 to below 28 in a few months. Yet it would seem that smart money began distributing the stock before the actual decline. Looking at the technical picture, we can spot evidence of this distribution and a serious loss of momentum:

   1.
      In December, a negative divergence formed in MACD.
   2.
      Chaikin Money Flow turned negative on December 21.
   3.
      Also in December, a Bearish Moving Average Crossover occurred in MACD (black arrow).
   4.
      The trend line extending up from October was broken on 20 December.
   5.
      A Bearish Centerline Crossover occurred in MACD on 10 Feb (green arrow).
   6.
      On 15 February, support at 31 1/2 was violated (red arrow).

For those waiting for a recovery in the stock, the continued decline of momentum suggested that selling pressure was increasing, and not about to decrease. Hindsight is 20/20, but with careful study of past situations, we can learn how to better read the present and prepare for the future.

MACD Benefits

One of the primary benefits of MACD is that it incorporates aspects of both momentum and trend in one indicator. As a trend-following indicator, it will not be wrong for very long. The use of moving averages ensures that the indicator will eventually follow the movements of the underlying security. By using Exponential Moving Averages (EMAs), as opposed to Simple Moving Averages (SMAs), some of the lag has been taken out.

As a momentum indicator, MACD has the ability to foreshadow moves in the underlying security. MACD divergences can be key factors in predicting a trend change. A Negative Divergence signals that bullish momentum is waning, and there could be a potential change in trend from bullish to bearish. This can serve as an alert for traders to take some profits in long positions, or for aggressive traders to consider initiating a short position.

MACD can be applied to daily, weekly or monthly charts. MACD represents the convergence and divergence of two moving averages. The standard setting for MACD is the difference between the 12 and 26-period EMA. However, any combination of moving averages can be used. The set of moving averages used in MACD can be tailored for each individual security. For weekly charts, a faster set of moving averages may be appropriate. For volatile stocks, slower moving averages may be needed to help smooth the data. Given that level of flexibility, each individual should adjust the MACD to suit his or her own trading style, objectives and risk tolerance.
MACD Drawbacks

One of the beneficial aspects of the MACD is also one of its drawbacks. Moving averages, be they simple, exponential or weighted, are lagging indicators. Even though MACD represents the difference between two moving averages, there can still be some lag in the indicator itself. This is more likely to be the case with weekly charts than daily charts. One solution to this problem is the use of the MACD-Histogram.

MACD is not particularly good for identifying overbought and oversold levels. Even though it is possible to identify levels that historically represent overbought and oversold levels, MACD does not have any upper or lower limits to bind its movement. MACD can continue to overextend beyond historical extremes.

MACD calculates the absolute difference between two moving averages and not the percentage difference. MACD is calculated by subtracting one moving average from the other. As a security increases in price, the difference (both positive and negative) between the two moving averages is destined to grow. This makes its difficult to compare MACD levels over a long period of time, especially for stocks that have grown exponentially.

Amazon.com, Inc. (AMZN) MACD example chart from StockCharts.com

The Amazon (AMZN)[Amzn] chart demonstrates the difficult in comparing MACD levels over a long period of time. Before 1999, Amazon's MACD is barely recognizable, and appears to trade close to the zero line. MACD was indeed quite volatile at the time, but this volatility has been dwarfed since the stock rose from below 20 to almost 100.

An alternative is to use the Price Oscillator, which shows the percentage difference between two moving averages:

(12 day EMA - 26 day EMA) / (26 day EMA)

(20 - 18) / 18 = .11 or +11%

The resulting percentage difference can be compared over a longer period of time. On the Amazon chart, we can see that the Price Oscillator provides a better means for a long-term comparison. For the short term, MACD and the Price Oscillator are basically the same. The shape of the lines, the divergences, moving average crossovers and centerline crossovers for MACD and the Price Oscillator are virtually identical.
Pros and Cons of the MACD

Since Gerald Appel developed the MACD, there have been hundreds of new indicators introduced to technical analysis. While many indicators have come and gone, the MACD has stood the test of time. The concept behind its use is straightforward, and its construction is simple, yet it remains one of the most reliable indicators around. The effectiveness of the MACD will vary for different securities and markets. The lengths of the moving averages can be adapted for a better fit to a particular security or market. As with all indicators , MACD is not infallible and should be used in conjunction with other technical analysis tools.
MACD-Histogram

In 1986, Thomas Aspray developed the MACD-Histogram. Some of his findings were presented in a series of articles for Technical Analysis of Stocks and Commodities. Aspray noted that MACD's lag would sometimes miss important moves in a security, especially when applied to weekly charts. He first experimented by changing the moving averages and found that shorter moving averages did indeed speed up the signals. However, he was looking for a means to anticipate MACD crossovers. One of the answers he came up with was the MACD-Histogram.

MACD example chart from StockCharts.com
Definition and Construction

The MACD-Histogram represents the difference between the MACD and its trigger line, the 9-day EMA of MACD. The plot of this difference is presented as a histogram, making centerline crossovers and divergences easily identifiable. A centerline crossover for the MACD-Histogram is the same as a moving average crossover for MACD. If you will recall, a moving average crossover occurs when MACD moves above or below the trigger line.

If the value of MACD is larger than the value of its 9-day EMA, then the value on the MACD-Histogram will be positive. Conversely, if the value of MACD is less than its 9-day EMA, then the value on the MACD-Histogram will be negative.

Further increases or decreases in the gap between MACD and its trigger line will be reflected in the MACD-Histogram. Sharp increases in the MACD-Histogram indicate that MACD is rising faster than its 9-day EMA and bullish momentum is strengthening. Sharp declines in the MACD-Histogram indicate that MACD is falling faster than its 9-day EMA and bearish momentum is increasing.

MACD example chart from StockCharts.com

On the chart above, we can see that the MACD-Histogram movements are relatively independent of the actual MACD. Sometimes the MACD is rising while the MACD-Histogram is falling. At other times, the MACD is falling while the MACD-Histogram is rising. The MACD-Histogram does not reflect the absolute value of the MACD, but rather the value of the MACD relative to its 9-day EMA. Usually, but not always, a move in the MACD is preceded by a corresponding divergence in the MACD-Histogram.

   1.
      The first point shows a sharp positive divergence in the MACD-Histogram that preceded a Bullish Moving Average Crossover.
   2.
      On the second point, the MACD continued to new Highs but the MACD-Histogram formed two equal Highs. Although not a textbook case of Positive Divergence, the equal High failed to confirm the strength seen in the MACD.
   3.
      A Positive Divergence formed when the MACD-Histogram formed a higher Low and the MACD continued lower.
   4.
      A Negative Divergence formed when the MACD-Histogram formed a lower High and the MACD continued higher.

Usage

Thomas Aspray designed the MACD-Histogram as a tool to anticipate a moving average crossover in the MACD. Divergences between MACD and the MACD-Histogram are the main tool used to anticipate moving average crossovers. A Positive Divergence in the MACD-Histogram indicates that the MACD is strengthening and could be on the verge of a Bullish Moving Average Crossover. A Negative Divergence in the MACD-Histogram indicates that the MACD is weakening, and it foreshadows a Bearish Moving Average Crossover in the MACD.

In his book, Technical Analysis of the Financial Markets, John Murphy asserts that the best use for the MACD-Histogram is in identifying periods when the gap between the MACD and its 9-day EMA is either widening or shrinking. Broadly speaking, a widening gap indicates strengthening momentum and a shrinking gap indicates weakening momentum. Usually a change in the MACD-Histogram will precede any changes in the MACD.
Signals

The main signal generated by the MACD-Histogram is a divergence followed by a moving average crossover. A bullish signal is generated when a Positive Divergence forms and there is a Bullish Centerline Crossover. A bearish signal is generated when there is a Negative Divergence and a Bearish Centerline Crossover. Keep in mind that a centerline crossover for the MACD-Histogram represents a moving average crossover for the MACD.

Divergences can take many forms and varying degrees. Generally speaking, two types of divergences have been identified: the slant divergence and the peak-trough divergence.

Unisys Corp. (UIS) MACD example chart from StockCharts.com
Slant Divergence

A Slant Divergence forms when there is a continuous and relatively smooth move in one direction (up or down) to form the divergence. Slant Divergences generally cover a shorter time frame than divergences formed with two peaks or two troughs. A Slant Divergence can contain some small bumps (peaks or troughs) along the way. The world of technical analysis is not perfect and there are exceptions to most rules and hybrids for many signals.

General Electric Co. (GE) MACD example chart from StockCharts.com
Peak-Trough Divergence

A peak-trough divergence occurs when at least two peaks or two troughs develop in one direction to form the divergence. A series of two or more rising troughs (higher lows) can form a Positive Divergence and a series of two or more declining peaks (lower highs) can form a Negative Divergence. Peak-trough Divergences usually cover a longer time frame than slant divergences. On a daily chart, a peak-trough divergence can cover a time frame as short as two weeks or as long as several months.

Usually, the longer and sharper the divergence is, the better any ensuing signal will be. Short and shallow divergences can lead to false signals and whipsaws. In addition, it would appear that Peak-trough Divergences are a bit more reliable than Slant Divergences. Peak-trough Divergences tend to be sharper and cover a longer time frame than Slant Divergences.
MACD-Histogram Benefits

The main benefit of the MACD-Histogram is its ability to anticipate MACD signals. Divergences usually appear in the MACD-Histogram before MACD moving average crossovers do. Armed with this knowledge, traders and investors can better prepare for potential trend changes.

The MACD-Histogram can be applied to daily, weekly or monthly charts. (Note: This may require some tinkering with the number of periods used to form the original MACD; shorter or faster moving averages might be necessary for weekly and monthly charts.) Using weekly charts, the broad underlying trend of a stock can be determined. Once the broad trend has been determined, daily charts can be used to time entry and exit strategies. In Technical Analysis of the Financial Markets, John Murphy advocates this type of two-tiered approach to investing in order to avoid making trades against the major trend. The weekly MACD-Histogram can be used to generate a long-term signal in order to establish the tradable trend. Then only short-term signals that agree with the major trend would be considered.

After the trend has been established, MACD-Histogram divergences can be used to signal impending reversals. If the long-term trend was bullish, a negative divergences with bearish centerline crossovers would signal a possible reversal. If the long-term trend was bearish, traders would watch for a positive divergences with bullish centerline crossovers.

International Business Machines (IBM) MACD example chart from StockCharts.com

On the IBM[IBM] weekly chart, the MACD-Histogram generated four signals. Before each moving average crossover in the MACD, a corresponding divergence formed in the MACD-Histogram. To make adjustments for the weekly chart, the moving averages have been shortened to 6 and 12. This MACD is formed by subtracting the 6-week EMA from the 12-week EMA. A 6-week EMA has been used as the trigger. The MACD-Histogram is calculated by taking the difference between MACD (6/12) and the 6-day EMA of MACD (6/12).

   1.
      The first signal was a Bearish Moving Average Crossover in January, 1999. From its peak in late November, 1998, the MACD-Histogram formed a Negative Divergence that preceded the Bearish Moving Average Crossover in the MACD.
   2.
      The second signal was a Bullish Moving Average Crossover in April. From its low in mid-February, the MACD-Histogram formed a Positive Divergence that preceded the Bullish Moving Average Crossover in the MACD.
   3.
      The third signal was a Bearish Moving Average Crossover in late July. From its May peak, the MACD-Histogram formed a Negative Divergence that preceded a Bearish Moving Average Crossover in the MACD.
   4.
      The final signal was a Bullish Moving Average Crossover, which was preceded by a slight Positive Divergence in the MACD-Histogram.

The third signal was based on a Peak-trough Divergence Two readily identifiable and consecutive lower peaks formed to create the divergence. The peaks and troughs on the previous divergences, although identifiable, do not stand out as much.
MACD-Histogram Drawbacks

The MACD-Histogram is an indicator of an indicator or a derivative of a derivative. The MACD is the first derivative of the price action of a security, and the MACD-Histogram is the second derivative of the price action of a security. As the second derivative, the MACD-Histogram is further removed from the actual price action of the underlying security. The further removed an indicator is from the underlying price action, the greater the chances of false signals. Keep in mind that this is an indicator of an indicator. The MACD-Histogram should not be compared directly with the price action of the underlying security.

Because MACD-Histogram was designed to anticipate MACD signals, there is a temptation to jump the gun. The MACD-Histogram should be used in conjunction with other aspects of technical analysis. This will help to alleviate the temptation for early entry. Another means to guard against early entry is to combine weekly signals with daily signals. Of course, there will be more daily signals than weekly signals. However, by using only the daily signals that agree with the weekly signals, there will be fewer daily signals to act on. By acting only on those daily signals that are in agreement with the weekly signals, you are also assured of trading with the longer trend and not against it.

Be careful of small and shallow divergences. While these may sometimes lead to good signals, they are also more apt to create false signals. One method to avoid small divergences is to look for larger divergences with two or more readily identifiable peaks or troughs. Compare the peaks and troughs from past action to determine significance. Only peaks and troughs that appear to be significant should warrant attention.
MACD and SharpCharts

*/


?>
