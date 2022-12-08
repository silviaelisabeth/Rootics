__author__ = 'Silvia E Zieger'
__project__ = 'soil profile analysis'

"""Copyright 2022. All rights reserved.

This software is provided 'as-is', without any express or implied warranty. In no event will the authors be held liable 
for any damages arising from the use of this software.
Permission is granted to anyone to use this software for any purpose, including commercial applications, and to alter it 
and redistribute it freely, subject to the following restrictions:
1. The origin of this software must not be misrepresented; you must not claim that you wrote the original software. 
   If you use this software in a product, an acknowledgment in the product documentation would be appreciated but is 
   not required
2. Altered source versions must be plainly marked as such, and must not be misrepresented as being the original software
3. This notice may not be removed or altered from any source distribution.

# ---------------------------------------------------------------------------------------------------------------------
# The code is implemented based on Jan Schulze's code in Pascal
The conductivity ratio (cnd) = 1.0000000 for salinity = 35 PSS-78, temperature=15.0 degC and atmospheric pressure.
function to convert conductivity ratio to salinity (M=0) or salinity to conductivity ratio (M=1, cnd becomes the input
parameter SALINITY)
REFERENCES: cf. UNESCO REPORT NO. 37 1981
practical salinity scale 1978: E.L. LEWIS IEEE OCEAN ENG. JAN. 1980
http://www.code10.info/index.php?option=com_content&view=article&id=65:conversion-between-conductivity-and-pss-78-salinity&catid=54:cat_coding_algorithms_seawater&Itemid=79

translation into Python by Silvia E. Zieger, 24-02-2022
"""

import numpy as np


# --------------------------------------------------------------------------------------------------------------------
def _salinity(xr, temp_degC):
    """ Practical salinity scale 1978 definition with temperature. Corrections made by Schulze: XT :=T-15.0,
    XR:=sqrt(RT).
    """
    # parameter preparation / corrections made by Schulze
    xt = temp_degC #- 15
    # xr = np.sqrt(RT)

    # salinity calculation
    sal = ((((2.7081*xr - 7.0261)*xr + 14.0941)*xr + 25.3851)*xr - 0.1692)*xr + 0.0080 + \
          (xt/(1.0+0.0162*xt))*(((((-0.0144*xr + 0.0636)*xr - 0.0375)*xr - 0.0066)*xr - 0.0056)*xr+0.0005)
    return sal


def _derivSAL(XR, XT):
    """calculates the derivative of _sal(temp_degC, RT) with RT
    :param XT:
    :param XR:
    :return:
    """
    derSal = ((((13.5405 * XR - 28.1044) * XR + 42.2823) * XR + 50.7702) * XR - 0.1692) + \
             (XT / (1.0 + 0.0162 * XT)) * ((((-0.0720 * XR + 0.2544) * XR - 0.1125) * XR - 0.0132) * XR - 0.0056)
    return derSal


def RT35(XT):
    """ conductivity ratio: C(35,T,0)/C(35,15,0) variation with temperature
    :param XT:
    :return:
    """
    return (((1.0031E-9 * XT - 6.9698E-7) * XT + 1.104259E-4) * XT + 2.00564E-2) * XT + 0.6766097


def _Cconst(XP):
    """ polynomial corresponds to A1-A3 constants in LEWIS 1980
    :param XP:
    :return:
    """
    return ((3.989E-15 * XP - 6.370E-10) * XP + 2.070E-5) * XP


def _Bconst(XT):
    """
    :param XT:
    :return:
    """
    return (4.464E-4 * XT + 3.426E-2) * XT + 1.0


def _Aconst(XT):
    """ polynomial corresponds to B3 and B4 constants in LEWIS 1980
    :param XT:
    :return:
    """
    return -3.107E-3 * XT + 0.4215


# --------------------------------------------------------------------------------------------------------------------
def SalCon_Converter(temp_degC, p_dbar, M, cnd):
    """

    :param temp_degC:
    :param p_dbar:
    :param M:
    :param cnd:
    :return:
    """
    # setting start conditions
    SAL78 = 0

    # zero salinity / conductivity trap
    if (M == 0 and cnd <= 5e-4) or (M == 1 and cnd <= 0.2):
        exit()

    # corrected temperature (introduced by Schulze)
    DT = temp_degC - 15

    # either calculate salinity (M=0) or conductivity (M=1)
    if M == 0:
        # convert conductivity to salinity
        Res = cnd
        RT_ = Res / (RT35(temp_degC) * (1.0 + _Cconst(p_dbar) / (_Bconst(temp_degC) + _Aconst(temp_degC) * Res)))
        RT = np.sqrt(np.abs(RT_))

        Sal78 = _salinity(RT, DT)
    elif M == 1:
        # invert salinity to conductivity by the Newton-Raphson iterative method
        # first approximation
        RT = np.sqrt(cnd / 35)
        SI = _salinity(RT, DT)
        N = 0

        # iterative loop begins with a maximum of 10 cycles
        ci = 0
        while ci <= 10:
            ci += 1
            RT = RT + (cnd - SI) / _derivSAL(RT, DT)
            SI = _salinity(RT, DT)
            N += 1
            DELS = np.abs(SI - cnd)

            # if ((DELS.GT.1.0E-4) and (N.LT.10) go to 15 !!!TODO: check what that means
            ci = 15 if (DELS < 1e-4) or (N >= 10) else 0

            # compute conductivity ratio
            RTT = RT35(temp_degC) * RT * RT
            CP = RTT * (_Cconst(p_dbar) + _Bconst(temp_degC))
            BT = _Bconst(temp_degC) - RTT * _Aconst(temp_degC)

            # solve quadratic equation for R: R = RT35*RT*(1 + C/AR + B)
            Res = np.sqrt(np.abs(BT * BT + 4 * _Aconst(temp_degC) * CP)) - BT

            # conductivity return
            Sal78 = 0.5 * Res / _Aconst(temp_degC)
    return Sal78
