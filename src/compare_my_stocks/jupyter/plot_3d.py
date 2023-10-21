#notice that this is licensed under the  Creative Commons BY-SA Attribution-ShareAlike
#see https://stackoverflow.com/questions/53611716/wrong-overlap-in-bar3d-plot/77332262#77332262
import matplotlib.pyplot as plt
import mplcursors
import numpy as np
#from mpl_toolkits.mplot3d.axes3d import Axes3D

#import matplotlib.colors as colors


def plot_3d_bar(df):
    y_labels = list(df.columns)
    x_labels = list(df.index.to_series())
    fig = plt.figure(figsize=(10, 8))
    ax = fig.add_subplot(111, projection='3d')
    # Create cursor object
    cursor = mplcursors.cursor(ax, hover=True)

    @cursor.connect("add")
    def on_add(sel):
        x, y, _ = sel.target
        sel.annotation.set_text(f'Data: ({x}, {y})')

    matrix = df.values
    len_x, len_y = matrix.shape
    _x = np.arange(len_x)
    _y = np.arange(len_y)

    xpos, ypos = np.meshgrid(_x, _y)
    xpos = xpos.flatten('F')
    ypos = ypos.flatten('F')
    zpos = np.zeros_like(xpos)

    dx = np.ones_like(zpos)
    dy = dx.copy()
    dz = matrix.flatten()
    cmap = plt.cm.magma(plt.Normalize(0, max(dz))(dz))

    ax.bar3d(xpos + 0.32, ypos - 0.3, zpos, dx - 0.6, dy - 0.6, dz, zsort='max', color=cmap)

    ax.set_xlabel('x')
    ax.set_xticks(np.arange(len_x))
    ax.set_xticklabels(x_labels)
    ax.set_xlim(0, len_x)

    ax.set_ylabel('y')
    ax.set_yticks(np.arange(len_y))
    ax.set_yticklabels(y_labels)
    ax.set_ylim(-0.5, len_y)

    ax.set_zlabel('z')
    # ax.set_zlim(0,3000)

    ax.view_init(elev=30, azim=-60)

    plt.show()