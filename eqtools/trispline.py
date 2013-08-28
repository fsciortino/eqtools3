import scipy 
import scipy.interpolate
import _tricubic


"""
    This file is part of the EqTools package.

    EqTools is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    EqTools is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with EqTools.  If not, see <http://www.gnu.org/licenses/>.

    Copyright 2013 Ian C. Faust
"""

class spline():


    def __init__(self,z,y,x,f):
        self._f = scipy.zeros(scipy.array(f.shape)+(2,2,2)) #pad the f array so as to force the Neumann Boundary Condition
        self._f[1:-1,1:-1,1:-1] = scipy.array(f) # place f in center, so that it is padded by unfilled values on all sides
        # faces
        self._f[(0,-1),1:-1,1:-1] = f[(0,-1),:,:] 
        self._f[1:-1,(0,-1),1:-1] = f[:,(0,-1),:]
        self._f[1:-1,1:-1,(0,-1)] = f[:,:,(0,-1)]
        #verticies
        self._f[(0,0,-1,-1),(0,-1,0,-1),1:-1] = f[(0,0,-1,-1),(0,-1,0,-1),:] 
        self._f[(0,0,-1,-1),1:-1,(0,-1,0,-1)] = f[(0,0,-1,-1),:,(0,-1,0,-1)]
        self._f[1:-1,(0,0,-1,-1),(0,-1,0,-1)] = f[:,(0,0,-1,-1),(0,-1,0,-1)]
        #corners
        self._f[(0,0,0,0,-1,-1,-1,-1),(0,0,-1,-1,0,0,-1,-1),(0,-1,0,-1,0,-1,0,-1)] = f[(0,0,0,0,-1,-1,-1,-1),(0,0,-1,-1,0,0,-1,-1),(0,-1,0,-1,0,-1,0,-1)]

        self._x = scipy.array(x)
        self._y = scipy.array(y)
        self._z = scipy.array(z)

    def ev(self,z1,y1,x1):
        x = scipy.atleast_1d(x1)
        y = scipy.atleast_1d(y1)
        z = scipy.atleast_1d(z1) # This will not modify x1,y1,z1.
        val = scipy.nan*scipy.zeros(x.shape)
        if scipy.any(x < self._x[0]) or scipy.any(x > self._x[-1]):
            raise ValueError('x value exceeds bounds of interpolation grid ')
        if scipy.any(y < self._y[0]) or scipy.any(y > self._y[-1]):
            raise ValueError('y value exceeds bounds of interpolation grid ')
        if scipy.any(z < self._z[0]) or scipy.any(z > self._z[-1]):
            raise ValueError('z value exceeds bounds of interpolation grid ')
        xinp = scipy.array(scipy.where(scipy.isfinite(x)))
        yinp = scipy.array(scipy.where(scipy.isfinite(y)))
        zinp = scipy.array(scipy.where(scipy.isfinite(z)))
        inp = scipy.intersect1d(scipy.intersect1d(xinp,yinp),zinp)

        if inp.size != 0:
            ix = scipy.digitize(x[inp],self._x)
            ix = ix.clip(0,self._x.size - 1) - 1
            iy = scipy.digitize(y[inp],self._y)
            iy = iy.clip(0,self._y.size - 1) - 1
            iz = scipy.digitize(z[inp],self._z)
            iz = iz.clip(0,self._z.size - 1) - 1
            pos = ix + self._f.shape[1]*(iy + self._f.shape[2]*iz)
            indx = scipy.argsort(pos) #each voxel is described uniquely, and this is passed to speed evaluation.
            dx =  (x[inp]-self._x[ix])/(self._x[ix+1]-self._x[ix])
            dy =  (y[inp]-self._y[iy])/(self._y[iy+1]-self._y[iy])
            dz =  (z[inp]-self._z[iz])/(self._z[iz+1]-self._z[iz])
            val[inp] = _tricubic.ev(dx,dy,dz,self._f,pos,indx)  

 
        return(val)


class RectBivariateSpline(scipy.interpolate.RectBivariateSpline):
    """ the lack of a graceful bounds error causes the fortran to fail hard. This masks the 
    scipy.interpolate.RectBivariateSpline with a proper bound checker and value filler
    such that it will not fail in use for EqTools"""

    def __init__(self, x, y, z, bbox=[None] *4, kx=3, ky=3, s=0, bounds_error=True, fill_value=scipy.nan):

        super(RectBivariateSpline, self).__init__( x, y, z, bbox=bbox, kx=kx, ky=ky, s=s)
        self._xlim = scipy.array((x.min(),x.max()))
        self._ylim = scipy.array((y.min(),y.max()))
        self.bounds_error = bounds_error
        self.fill_value = fill_value

    def _check_bounds(self, x_new, y_new):
        """Check the inputs for being in the bounds of the interpolated data.

        Parameters
        ----------
        x_new: array
        y_new: array

        Returns
        -------
        out_of_bounds : bool array
           The mask on x_new and y_new of values that are NOT of bounds.
        """
        below_bounds_x = x_new < self._xlim[0]
        above_bounds_x = x_new > self._xlim[1]

        below_bounds_y = y_new < self._ylim[0]
        above_bounds_y = y_new > self._ylim[1]

        # !! Could provide more information about which values are out of bounds
        if self.bounds_error and below_bounds_x.any():
            raise ValueError("A value in x is below the interpolation "
                "range.")
        if self.bounds_error and above_bounds_x.any():
            raise ValueError("A value in x is above the interpolation "
                "range.")
        if self.bounds_error and below_bounds_y.any():
            raise ValueError("A value in y is below the interpolation "
                "range.")
        if self.bounds_error and above_bounds_y.any():
            raise ValueError("A value in y is above the interpolation "
                "range.")

        out_of_bounds = scipy.logical_not(scipy.logical_or(scipy.logical_or(below_bounds_x, above_bounds_x),
                                                           scipy.logical_or(below_bounds_y, above_bounds_y)))
        return out_of_bounds


    def ev(self, xi, yi):
        """
        Evaluate spline at points (x[i], y[i]), i=0,...,len(x)-1
        """

        idx = self._check_bounds(xi,yi)
        zi = self.fill_value*scipy.ones(xi.shape)
        zi[idx] = super(RectBivariateSpline, self).ev(xi[idx], yi[idx])
        return zi

