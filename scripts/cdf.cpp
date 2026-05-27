#include "cdf.h"
//---------------------------------------------------------------------------
double CDF::N(double D)
 {
  double CN;
  int i;
  if(fabs(D) > 7 )
   {
    if(D>0)
   return(1);
    else
   return(0);
   }
   CN = 0;
   for(i = 0; i <= 12; i ++)
     CN+=exp(-(pow((i+0.5),2))/9)*
     sin(fabs(D)*(i+0.5)*sqrt(2)/3)*pow((i+0.5),-1);
     CN = 0.5 + (1 / PI) * CN;
     if(D > 0)
      return(CN);
     else
       return(1 - CN);
 };
//---------------------------------------------------------------------------
 double CDF::D(double P)
 {
  double SPLIT1, SPLIT2, CONST1, CONST2, A0, A1, A2, A3, B1, B2, B3,
    C0, C1, C2, C3, D1, D2, D3, E0, E1, E2, E3, F1, F2, Q, R;
  double PPND7;
  SPLIT1 = 0.425;
  SPLIT2 = 5.0;
  CONST1 = 0.180625;
  CONST2 = 1.6;
  // Coeffcients for P close to 0.5
  A0 = 3.3871327179E+00; A1 = 5.0434271938E+01; A2 = 1.5929113202E+02;
  A3 = 5.9109374720E+01; B1 = 1.7895169469E+01; B2 = 7.8757757664E+01;
  B3 = 6.7187563600E+01;
  //Hash sum AB 32.3184577772
  // Coeffcients for P not close to 0, 0.5, or 1
  C0 = 1.4234372777E+00; C1 = 2.7568153900E+00; C2 = 1.3067284816E+00;
  C3 = 1.7023821103E-01; D1 = 7.3700164250E-01; D2 = 1.2021132975E-01;
  //HASH SUM CD 15.76149 29821
  // Coeffcients for P not close to 0, 1
  E0 = 6.6579051150E+00; E1 = 3.0812263860E+00; E2 = 4.2868294337E-01;
  E3 = 1.7337203997E-02; F1 = 2.4197894225E-01; F2 = 1.2258202635E-02;
  // HASH SUM EF 19.40529 10204
  if(P <= 0.000000001) P = 0.000000001;
  if (P>= 0.999999999) P = 0.999999999;
  Q = P - 0.5;
  if (fabs(Q) <= SPLIT1) {
  R = CONST1 - Q*Q;
  return (Q * (((A3 * R + A2) * R + A1) * R + A0) /
    (((B3 * R + B2) * R + B1 ) * R + 1.0));
    } else {
    if (Q <= 0.0) {
      R = P;
     } else {
      R = 1.0 - P;
      }
    if (R <= 0.0) return 0.0;
    R = sqrt(-log(R));
    if (R <= SPLIT2) {
    R = R - CONST2;
    PPND7 = (((C3 * R + C2) * R + C1) * R + C0) /
      ((D2 * R + D1) * R + 1.0);
    } else {
    R = R - SPLIT2;
    PPND7 = (((E3 * R + E2) * R + E1) * R + E0) /
      ((F2 * R + F1) * R + 10);
    }
    if (Q <= 0.0) PPND7 = - PPND7;
    return PPND7;
   }
  };
  


