"""Dispersion due to the solar wind."""
from warnings import warn

import astropy.constants as const
import astropy.units as u
import numpy as np
import scipy.special

from pint.models.dispersion_model import Dispersion, DMconst
from pint.models.parameter import floatParameter


class SolarWindDispersion(Dispersion):
    """Dispersion due to the solar wind (basic model).

    The model is a simple spherically-symmetric model that is fit
    only in its constant amplitude.

    Parameters supported:

    .. paramtable::
        :class: pint.models.solar_wind_dispersion.SolarWindDispersion

    References
    ----------
    Edwards et al. 2006, MNRAS, 372, 1549; Setion 2.5.4
    Madison et al. 2019, ApJ, 872, 150; Section 3.1.
    """

    register = True
    category = "solar_wind"

    def __init__(self):
        super().__init__()
        self.add_param(
            floatParameter(
                name="NE_SW",
                units="cm^-3",
                value=0.0,
                aliases=["NE1AU", "SOLARN0"],
                description="Solar Wind density at 1 AU",
            )
        )
        self.add_param(
            floatParameter(
                name="SWM",
                value=0.0,
                units="",
                description="Solar Wind Model (0 is from Edwards+ 2006, others to come)",
            )
        )
        self.dm_value_funcs += [self.solar_wind_dm]
        self.delay_funcs_component += [self.solar_wind_delay]
        self.set_special_params(["NE_SW", "SWM"])

    def setup(self):
        super().setup()
        self.register_dm_deriv_funcs(self.d_dm_d_ne_sw, "NE_SW")
        self.register_deriv_funcs(self.d_delay_d_ne_sw, "NE_SW")

    def solar_wind_geometry(self, toas):
        """Return the geometry of solar wind dispersion.

        Implements the geometry part of equations 29, 30 of Edwards et al. 2006,
        (i.e., without the n0, the solar wind DM amplitude part.)
        Their rho is given as theta here.

        rvec: radial vector from observatory to the center of the Sun
        pos: pulsar position
        """
        angle, r = self._parent.sun_angle(toas, also_distance=True)
        rho = np.pi - angle.value
        solar_wind_geometry = const.au**2.0 * rho / (r * np.sin(rho))
        return solar_wind_geometry

    def solar_wind_dm(self, toas):
        """Return the solar wind dispersion measure.

        Uses equations 29, 30 of Edwards et al. 2006.
        """
        if self.NE_SW.value == 0:
            return np.zeros(len(toas)) * u.pc / u.cm**3
        if self.SWM.value == 0:
            solar_wind_geometry = self.solar_wind_geometry(toas)
            solar_wind_dm = self.NE_SW.quantity * solar_wind_geometry
        else:
            # TODO Introduce the You et.al. (2007) Solar Wind Model for SWM=1
            raise NotImplementedError(
                "Solar Dispersion Delay not implemented for SWM %d" % self.SWM.value
            )
        return solar_wind_dm.to(u.pc / u.cm**3)

    def solar_wind_delay(self, toas, acc_delay=None):
        """This is a wrapper function to compute solar wind dispersion delay."""
        if self.NE_SW.value == 0:
            return np.zeros(len(toas)) * u.s
        return self.dispersion_type_delay(toas)

    def d_dm_d_ne_sw(self, toas, param_name, acc_delay=None):
        """Derivative of of DM wrt the solar wind dm amplitude."""
        if self.SWM.value == 0:
            solar_wind_geometry = self.solar_wind_geometry(toas)
        else:
            # TODO Introduce the You et.al. (2007) Solar Wind Model for SWM=1
            raise NotImplementedError(
                "Solar Dispersion Delay not implemented for SWM %d" % self.SWM.value
            )
        return solar_wind_geometry

    def d_delay_d_ne_sw(self, toas, param_name, acc_delay=None):
        try:
            bfreq = self._parent.barycentric_radio_freq(toas)
        except AttributeError:
            warn("Using topocentric frequency for dedispersion!")
            bfreq = toas.table["freq"]
        deriv = self.d_delay_d_dmparam(toas, "NE_SW")
        deriv[bfreq < 1.0 * u.MHz] = 0.0
        return deriv

    def print_par(self, format="pint"):
        result = ""
        result += getattr(self, "NE_SW").as_parfile_line(format=format)
        result += getattr(self, "SWM").as_parfile_line(format=format)
        return result


def _dm_p_int(b, z, p):
    """Integral function for DM calculation
    from https://github.com/nanograv/enterprise_extensions/blob/master/enterprise_extensions/chromatic/solar_wind.py#L299

    See Figure 1 of Hazboun et al. (2022) for definitions of b, z

    Parameters
    ----------
    b : astropy.quantity.Quantity
        Impact parameter
    z : astropy.quantity.Quantity
        distance from Earth to closest point to the Sun
    p : power-law index

    Returns
    -------
    astropy.quantity.Quantity
    """
    return (z / b) * scipy.special.hyp2f1(
        0.5, p / 2.0, 1.5, -((z**2) / b**2).decompose().value
    )


class SphericalSolarWindDispersion(Dispersion):
    """Dispersion due to the solar wind (spherically symmetric model).

    The model is a simple spherically-symmetric model that is fit
    in its amplitude with a constant a power-law index (that may not be 2)

    Parameters supported:

    .. paramtable::
        :class: pint.models.solar_wind_dispersion.SphericalSolarWindDispersion

    References
    ----------
    Hazboun et al. (2022, ApJ, 929, 39)
    You et al. (2012, MNRAS, 422, 1160)
    """

    register = True
    category = "solar_wind"

    def __init__(self):
        super().__init__()
        self.add_param(
            floatParameter(
                name="NE_SWP",
                units="cm^-3",
                value=0.0,
                aliases=["NE1AUp", "SOLARN0p"],
                description="Solar Wind density at 1 AU",
            )
        )
        self.add_param(
            floatParameter(
                name="SWP",
                value=2.0,
                units="",
                description="Solar Wind Model radial power-law index",
            )
        )
        self.dm_value_funcs += [self.solar_wind_dm]
        self.delay_funcs_component += [self.solar_wind_delay]
        self.set_special_params(["NE_SWP", "SWP"])

    def setup(self):
        super().setup()
        self.register_dm_deriv_funcs(self.d_dm_d_ne_sw, "NE_SWP")
        self.register_deriv_funcs(self.d_delay_d_ne_sw, "NE_SWP")

    def solar_wind_geometry(self, toas):
        """Return the solar wind geometric factor

        Implements Eqn. 12 of Hazboun et al. (2022)
        """
        p = self.SWP.value
        # get elongation angle, distance from Earth to Sun
        theta, r = self._parent.sun_angle(toas, also_distance=True)
        # impact parameter
        b = r * np.sin(theta)
        # distance from the Earth to the impact point
        z_sun = r * np.cos(theta)
        if self.NE_SWP.value == 0:
            return np.zeros(len(toas)) * u.pc / u.cm**3
        if p > 1:
            solar_wind_geometry = (
                (1 / b.to_value(u.AU)) ** p
                * b
                * (_dm_p_int(b, 1e14 * u.cm, p) - _dm_p_int(b, -z_sun, p))
            )
        else:
            raise NotImplementedError(
                "Spherical Solar Dispersion Delay not implemented for power-law index p <= 1"
            )
        return solar_wind_geometry

    def solar_wind_dm(self, toas):
        """Return the solar wind dispersion measure.

        Implements Eqn. 12 of Hazboun et al. (2022)
        """
        solar_wind_dm = self.NE_SWP.quantity * self.solar_wind_geometry(toas)
        return solar_wind_dm.to(u.pc / u.cm**3)

    def solar_wind_delay(self, toas, acc_delay=None):
        """This is a wrapper function to compute solar wind dispersion delay."""
        if self.NE_SWP.value == 0:
            return np.zeros(len(toas)) * u.s
        return self.dispersion_type_delay(toas)

    def d_dm_d_ne_sw(self, toas, param_name, acc_delay=None):
        """Derivative of of DM wrt the solar wind dm amplitude."""
        solar_wind_geometry = self.solar_wind_geometry(toas)
        return solar_wind_geometry

    def d_delay_d_ne_sw(self, toas, param_name, acc_delay=None):
        try:
            bfreq = self._parent.barycentric_radio_freq(toas)
        except AttributeError:
            warn("Using topocentric frequency for dedispersion!")
            bfreq = toas.table["freq"]
        deriv = self.d_delay_d_dmparam(toas, "NE_SWP")
        deriv[bfreq < 1.0 * u.MHz] = 0.0
        return deriv

    def print_par(self, format="pint"):
        result = ""
        result += getattr(self, "NE_SWP").as_parfile_line(format=format)
        result += getattr(self, "SWP").as_parfile_line(format=format)
        return result
