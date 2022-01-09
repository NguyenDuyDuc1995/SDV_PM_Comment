import matplotlib.colors
import numpy as np
from matplotlib.cm import get_cmap as mpl_get_cmap, _colormaps

# It means when use: <from mpl_color_utils import *>, it will import all in <__all__> variable.
# If this module has many classes or functions, we need to add more code to import
__all__ = ['COLOR_MAPS', 'BASE_COLORS', 'TABLEAU_COLORS', 'XKCD_COLORS', 'CSS4_COLORS',
           'ColorMap', 'get_cmap', 'to_rgb']

COLOR_MAPS = _colormaps()
BASE_COLORS = list(matplotlib.colors.BASE_COLORS.keys())
TABLEAU_COLORS = list(matplotlib.colors.TABLEAU_COLORS.keys())
XKCD_COLORS = list(matplotlib.colors.XKCD_COLORS.keys())
CSS4_COLORS = list(matplotlib.colors.CSS4_COLORS.keys())


# noinspection PyMethodOverriding
class ColorMap(matplotlib.colors.ListedColormap):
    def __init__(self, colors, name='from_list', N=None, scale=1.0):
        super(ColorMap, self).__init__(colors[:, :3], name, N)
        self.scale = scale

    @staticmethod
    def from_cmap(cmap, scale=1.0):
        if isinstance(cmap, matplotlib.colors.Colormap):
            if hasattr(cmap, 'colors'):
                colors = cmap.colors
            else:
                colors = np.array([cmap(i) for i in range(cmap.N)])
            return ColorMap(colors, cmap.name, scale=scale)
        return ColorMap(np.array(cmap), scale=scale)

    def __call__(self, item):
        color = super(ColorMap, self).__call__(item)
        return np.array(color[:3]) * self.scale

    def __getitem__(self, item):
        return self(item)


def get_cmap(name=None, lut=None, scale=1.0) -> ColorMap:
    """
    Create a list of class - color
    """

    return ColorMap.from_cmap(mpl_get_cmap(name, lut), scale=scale)


def to_rgb(c=None, scale=1.0) -> np.ndarray:
    return np.array(matplotlib.colors.to_rgb(c)) * scale
