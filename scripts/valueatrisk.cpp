/****************************************************************************
** Author: Razvan Pascalau
** Location
**      VaRM.cpp
** Name
**      Implementation unit
** Description
**      This is the implementation file that contains the functions to
**      calculate teh Value at Risk using three different methods (Delta,
**      Delta-Gamma and ACtual VaR) for a long position in a call and a put.
*****************************************************************************/
//---------------------------------------------------------------------------
#pragma hdrstop
#include "var.h"
#pragma package(smart_init)
//---------------------------------------------------------------------------
void VaR::VaRSetData(float tempStockPrice, float tempStrikePrice,
      float tempInterestRate, float tempMaturity, float tempVolatility,
      float tempExpectedReturn, float tempConfidenceInterval, float tempHorizon)
  {
  StockPrice=tempStockPrice;
  StrikePrice=tempStrikePrice;
  InterestRate=tempInterestRate;
  Maturity=tempMaturity;
  ExpectedReturn=tempExpectedReturn;
  Volatility=tempVolatility;
  ConfidenceInterval=tempConfidenceInterval;
  Horizon=tempHorizon;
  }
//-----------------------------------------------------------------------------
long double VaR::CalculateCallPrice()
 {
  CallPrice = StockPrice* N(Calculated1()) -
  StrikePrice * exp(-(InterestRate/100.0)*Maturity) * N(Calculated2());
   CalculateCallLowerBound();
   return CallPrice;
  }
//-----------------------------------------------------------------------------
 long double VaR::CalculatePutPrice()
 {
  PutPrice = StrikePrice * exp(-(InterestRate/100.0) * Maturity)
   *N(-(Calculated2())) - StockPrice*N(-(Calculated1()));
  CalculatePutLowerBound();
  return PutPrice;
 }
//---------------------------------------------------------------------------
double VaR::CalculateCallLowerBound()
{
  LowerBound = StockPrice
    - StrikePrice * exp(-(InterestRate/100.0)* Maturity);
  if (LowerBound > 0.0 && CallPrice < LowerBound) CallPrice = LowerBound;
  return CallPrice;
}
//---------------------------------------------------------------------------
double VaR::CalculatePutLowerBound()
{
  LowerBound = StrikePrice * exp(-(InterestRate/100.0) *Maturity)
		 - StockPrice;
  if (LowerBound > 0.0 && PutPrice < LowerBound) PutPrice = LowerBound;
  return PutPrice;
}
//---------------------------------------------------------------------------
double VaR::Calculated1()
{
  d1 = log(StockPrice/StrikePrice) + (InterestRate/100.0
    + pow(Volatility/100.0, 2)/2.0) * Maturity;
  d1 /= (Volatility/100.0) * pow(Maturity, 0.5);
  return d1;
}
//---------------------------------------------------------------------------
double VaR::Calculated2()
{
  return Calculated1() - (Volatility/100.0) * pow(Maturity, 0.5);
}
//---------------------------------------------------------------------------
long double VaR::CalculateVaRCall()
{
  return -((ExpectedReturn/100.0)*StockPrice*(Horizon/52.0)+ (Volatility/100.0)*
          StockPrice*sqrt(Horizon/52.0)*D(1-ConfidenceInterval/100.0));
}
//---------------------------------------------------------------------------
long double VaR::CalculateVaRPut()
{
  return -((-ExpectedReturn/100.0)*StockPrice*(Horizon/52.0)+(Volatility/100.0)*
          StockPrice*sqrt(Horizon/52.0)*D(1-ConfidenceInterval/100.0));
}
//---------------------------------------------------------------------------
long double VaR::CalculateGamma()
{
  return exp((-Calculated1()*Calculated1())/2.0)/(StockPrice*(Volatility/100.0)*
             sqrt(2*PI*Maturity));
}
//---------------------------------------------------------------------------
long double VaR::CalculateVaRDeltaCall()
{
 return VaRDeltaCall = -(N(Calculated1())*(ExpectedReturn/100.0)*StockPrice*
         (Horizon/52.0)+(Volatility/100.0)*N(Calculated1())*StockPrice*
         sqrt(Horizon/52.0)*D(1-ConfidenceInterval/100.0));
}
//---------------------------------------------------------------------------
long double VaR::CalculateVaRDeltaPut()
{
 return VaRDeltaPut = (-(N(Calculated1())-1.0)*(ExpectedReturn/100.0)*StockPrice*
         (Horizon/52.0)+(Volatility/100.0)*(N(Calculated1())-1.0)*StockPrice*
         sqrt(Horizon/52.0)*D(1-ConfidenceInterval/100.0));
}
//---------------------------------------------------------------------------
long double VaR::CalculateDeltaGammaCall()
{
   DeltaGammaCall = -(N(Calculated1())*(ExpectedReturn/100.0)*StockPrice*
         (Horizon/52.0)+ (CalculateGamma()/2.0)*pow(StockPrice,2)*
         (pow((Volatility/100.0),2)+pow((ExpectedReturn/100.0),2)*
         (Horizon/52.0))*(Horizon/52.0));
   DeltaGammaCall -=  sqrt(pow(N(Calculated1()),2)*pow(StockPrice,2)*
          (pow((Volatility/100.0),2)+pow(ExpectedReturn/100.0,2)*
          (Horizon/52.0))*(Horizon/52.0)+ N(Calculated1())*
          CalculateGamma()*pow(StockPrice,3)*(3*pow((Volatility/100.0),2)+
          pow(ExpectedReturn/100.0,2)*(Horizon/52.0))*(ExpectedReturn/100.0)*
          pow(Horizon/52.0,2)+(1/4)*pow(CalculateGamma(),2)*pow(StockPrice,4)*
          (3*pow(Volatility/100.0,4)+6*pow(ExpectedReturn/100.0,2)*
          pow(Volatility/100.0,2)*(Horizon/52.0)+pow(ExpectedReturn/100.0,4)*
          pow((Horizon/52.0),2))*pow((Horizon/52.0),2)-
          (pow(N(Calculated1())*StockPrice*(ExpectedReturn/100.0)*(Horizon/52.0)+
          (1/2)*CalculateGamma()*pow(StockPrice,2)*(pow((Volatility/100.0),2)+
          (ExpectedReturn/100.0)*(Horizon/52.0))*(Horizon/52.0),2)))*
          D(1-ConfidenceInterval/100.0);
    return DeltaGammaCall;
}
//---------------------------------------------------------------------------
long double VaR::CalculateDeltaGammaPut()
{
   DeltaGammaPut = -((N(Calculated1())-1)*(ExpectedReturn/100.0)*StockPrice*
         (Horizon/52.0)+ (CalculateGamma()/2.0)*pow(StockPrice,2)*
         (pow((Volatility/100.0),2)+pow((ExpectedReturn/100.0),2)*
         (Horizon/52.0))*(Horizon/52.0));
   DeltaGammaPut -=  sqrt(pow(N(Calculated1())-1.0,2)*pow(StockPrice,2)*
          (pow((Volatility/100.0),2)+pow(ExpectedReturn/100.0,2)*
          (Horizon/52.0))*(Horizon/52.0)+ (N(Calculated1())-1.0)*
          CalculateGamma()*pow(StockPrice,3)*(3*pow((Volatility/100.0),2)+
          pow(ExpectedReturn/100.0,2)*(Horizon/52.0))*(ExpectedReturn/100.0)*
          pow(Horizon/52.0,2)+(1/4)*pow(CalculateGamma(),2)*pow(StockPrice,4)*
          (3*pow(Volatility/100.0,4)+6*pow(ExpectedReturn/100.0,2)*
          pow(Volatility/100.0,2)*(Horizon/52.0)+pow(ExpectedReturn/100.0,4)*
          pow((Horizon/52.0),2))*pow((Horizon/52.0),2)-
          (pow((N(Calculated1())-1.0)*StockPrice*(ExpectedReturn/100.0)*(Horizon/52.0)+
          (1/2)*CalculateGamma()*pow(StockPrice,2)*(pow((Volatility/100.0),2)+
          (ExpectedReturn/100.0)*(Horizon/52.0))*(Horizon/52.0),2)))*
          D(1-ConfidenceInterval/100.0);
    return DeltaGammaPut;
}
//---------------------------------------------------------------------------
double VaR::Calculatenewd1()
{
  newd1 = log((StockPrice-CalculateVaRCall())/StrikePrice) + (InterestRate/100.0
    + pow(Volatility/100.0, 2)/2.0) * (Maturity-Horizon/52.0);
  newd1 /= (Volatility/100.0) * pow(Maturity-Horizon/52.0, 0.5);
  return newd1;
}
//---------------------------------------------------------------------------
double VaR::Calculatenewd2()
{
  return Calculatenewd1() - (Volatility/100.0) * pow(Maturity-Horizon/52.0, 0.5);
}
//---------------------------------------------------------------------------
long double VaR::CalculateCallActualVaR()
{
  CallActualVaR = -((StockPrice-CalculateVaRCall())* N(Calculatenewd1()) -
  StrikePrice * exp(-(InterestRate/100.0)*(Maturity-Horizon/52.0)) *
  N(Calculatenewd2())- CalculateCallPrice());
  return CallActualVaR;
}
//---------------------------------------------------------------------------
double VaR::CalculatePutd1()
{
  Putd1 = log((StockPrice+CalculateVaRPut())/StrikePrice) + (InterestRate/100.0
    + pow(Volatility/100.0, 2)/2.0) * (Maturity-Horizon/52.0);
  Putd1 /= (Volatility/100.0) * pow(Maturity-Horizon/52.0, 0.5);
  return Putd1;
}
//---------------------------------------------------------------------------
double VaR::CalculatePutd2()
{
  return CalculatePutd1() - (Volatility/100.0) * pow(Maturity-Horizon/52.0, 0.5);
}
//---------------------------------------------------------------------------

long double VaR::CalculatePutActualVaR()
{
  PutActualVaR = -(StrikePrice * exp(-(InterestRate/100.0)*(Maturity-Horizon/52.0))
   *N(-(CalculatePutd2()))-(StockPrice+CalculateVaRPut())*N(-(CalculatePutd1()))
   - CalculatePutPrice());
  return PutActualVaR;
}


