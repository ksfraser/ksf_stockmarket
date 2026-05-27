/****************************************************************************
** Author: Razvan Pascalau
** Location
**      VaR.h
** Name
**      Implementation unit
** Description
**      This is the file in the implementation unit that contains the
**      definitions of the variables to be used in computations.
*****************************************************************************/
//---------------------------------------------------------------------------
#ifndef VaRH
#define VaRH
#define PI 3.14159265358979324
#include "cdf.cpp"
//---------------------------------------------------------------------------
class VaR : public CDF
 {
  public:
   void VaRSetData(float StockPrice, float StrikePrice, float InterestRate,
                   float Maturity, float Volatility, float ExpectedReturn,
                   float ConfidenceInterval, float Horizon);
   long double CalculateCallPrice();
   long double CalculatePutPrice();
   long double CalculateVaRCall();
   long double CalculateVaRPut();
   long double CalculateGamma();
   long double CalculateVaRDeltaCall();
   long double CalculateVaRDeltaPut();
   long double CalculateDeltaGammaCall();
   long double CalculateDeltaGammaPut();
   long double CalculateCallActualVaR();
   long double CalculatePutActualVaR();
  private:
  float CallPrice;
  float PutPrice;
  float StockPrice;
  float StrikePrice;
  float Maturity;
  float InterestRate;
  float ExpectedReturn;
  float Volatility;
  float ConfidenceInterval;
  float Horizon;
  double d1;
  double d2;
  double newd1;
  double newd2;
  double Putd1;
  double Putd2;
  double LowerBound;
  double CalculateCallLowerBound();
  double CalculatePutLowerBound();
  double Calculated1();
  double Calculated2();
  double Calculatenewd1();
  double Calculatenewd2();
  double CalculatePutd1();
  double CalculatePutd2();
  //Output
  double VaRDeltaCall;
  double VaRDeltaPut;
  double DeltaGammaCall;
  double DeltaGammaPut;
  double CallDeltaGamma;
  double PutDeltaGamma;
  double CallActualVaR;
  double PutActualVaR;
 };
#endif


