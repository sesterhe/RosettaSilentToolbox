from distutils.version import LooseVersion
import os
import copy
import math

import pandas as pd
import numpy as np
import seaborn as sns
import networkx as nx
import matplotlib as mpl
import matplotlib.patheffects
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, PathPatch
from matplotlib.font_manager import FontProperties
from matplotlib.text import TextPath

from rstoolbox.analysis import binary_overlap
from rstoolbox.components import DesignFrame, SequenceFrame, get_selection
from .color_schemes import color_scheme


def barcode_plot( df, column_name, ax, color="blue" ):
    result = binary_overlap( df, column_name )
    pd.Series(result).plot("bar", ax=ax, ylim=(0, 1), grid=False, color=color, width=1 )
    ax.yaxis.set_ticks([])
    ax.xaxis.set_ticks(np.arange(0, len(result) + 1, 10))
    ax.xaxis.set_ticklabels(np.arange(0, len(result) + 1, 10) + 1, rotation=45)
    ax.set_xlabel("sequence")


def plot_sequence_frequency_graph( G, ax ):
    """
    Given a sequence frequency graph as obtained through
    :meth:`.FragmentFrame.make_frequency_network` or
    :meth:`.FragmentFrame.make_per_position_frequency_network`,
    generate a plot representing the possible transitions between
    nodes.

    :param G: Sequence frequency graph
    :type G: :class:`~networkx.DiGraph`
    :param ax:
    :type ax: :class:`~matplotlib.axes.Axes`

    """
    alphabet = "ARNDCQEGHILKMFPSTWYV"
    all_pos = {}
    for node, data in G.nodes(data=True):
        if data['type'] in alphabet:
            all_pos.setdefault(node, (data['order'], alphabet.index(data['type'])))
        else:
            all_pos.setdefault(node, (data['order'], len(alphabet) / 2))
    nx.draw_networkx(G, ax=ax, pos=all_pos, with_labels=False, arrows=False)
    ax.set_yticks(range(0, len(alphabet)))
    ax.set_yticklabels(list(alphabet))
    ax.set_xlim(G.node["0X"]['order'] - 1, G.node["-1X"]['order'] + 1)


def sequence_frequency_plot( df, seqID, ax, aminosY=True, clean_unused=-1,
                             refseq=True, key_residues=None, border_color="green",
                             border_width=2, labelsize=None, xrotation=0, yrotation=0,
                             **kwargs ):
    """
    Makes a heatmap subplot into the provided axis showing the sequence distribution
    of each residue type for each position.

    A part from the function arguments, any argument that can be provided to the
    :func:`seaborn.heatmap` function can also be provided here.

    By default, the heatmap generated will have the residue types as y-axis and the
    sequence positions as x-axis.

    Some tips:

    #. **Do you want to set the orientation of the color bar vertical?** \
        Add the parameter: ``cbar_kws={"orientation": "vertical"}``
    #. **Do you want to put the color bar in a different axis?** \
        This is quite recommendable, as the color bar in the same axis does not \
        tend to look that good. Add the parameter: ``cbar_ax=[second_axis]``
    #. **You don't want a color bar?** \
        Add the parameter: ``cbar=False``

    .. ipython::

        In [1]: from rstoolbox.io import parse_rosetta_file
           ...: from rstoolbox.plot import sequence_frequency_plot
           ...: import matplotlib.pyplot as plt
           ...: df = parse_rosetta_file("../rstoolbox/tests/data/input_2seq.minisilent.gz",
           ...:                         {"sequence": "B"})
           ...: fig = plt.figure(figsize=(25, 10))
           ...: ax = plt.subplot2grid((1, 1), (0, 0))
           ...: sequence_frequency_plot(df, "B", ax, refseq=False, cbar=False, xrotation=90)

        @savefig sequence_frequency_plot_docs.png width=5in
        In [2]: plt.show()

    :param df: Data container.
    :type df: Union[:class:`.DesignFrame`, :class:`.SequenceFrame`]
    :param seqID: Identifier of the query sequence.
    :type seqID: :class:`str`
    :param ax: Where to plot the heatmap.
    :type ax: :class:`~matplotlib.axes.Axes`
    :param aminosY: Set to :data:`False` to get invert the orientation of the heatmap.
    :type aminosY: :class:`bool`
    :param clean_unused: Remove amino acids from the plot when they never get represented
        over the given frequency. Residues present in the reference sequence are not taken
        into account.
    :type clean_unused: :class:`float`
    :param refseq: if :data:`True` (default), mark the original residues according to
        the reference sequence.
    :type refseq: :class:`bool`
    :param key_residues: Residues of interest to be plotted.
    :type key_residue: Union[:class:`int`, :func:`list` of :class:`int`, :class:`.Selection`]
    :param border_color: Color to use to mark the original residue types.
    :type border_color: Union[:class:`int`, :class:`str`]
    :param border_width: Line width used to mark the original residue types.
    :type border_width: :class:`int`
    :param labelsize: Change the size of the text in the axis.
    :type labelsize: :class:`int`
    :param xrotation: Rotation to apply in the x-axis text (degrees).
    :type xrotation: :class:`float`
    :param yrotation: Rotation to apply in the y-axis text (degrees).
    :type yrotation: :class:`float`

    :raises:
        :ValueError: if input is not a DataFrame derived object.
        :KeyError: if reference sequence is requested but the data container
            does not have one.
    """

    order = ["A", "V", "I", "L", "M", "F", "Y", "W", "S", "T", "N",
             "Q", "R", "H", "K", "D", "E", "C", "G", "P"]
    data = copy.deepcopy(df)

    fp = FontProperties()
    fp.set_family("monospace")

    # Data type management.
    if not isinstance(data, pd.DataFrame):
        raise ValueError("Input data must be in a DataFrame, DesignFrame or SequenceFrame")
    else:
        if not isinstance(data, (DesignFrame, SequenceFrame)):
            if len(set(data.columns.values).intersction(set(order))) == len(order):
                data = SequenceFrame(data)
            else:
                data = DesignFrame(data)
    if isinstance(data, DesignFrame):
        data = data.sequence_frequencies(seqID)
    if isinstance(data, SequenceFrame):
        order = sorted(data.columns.values.tolist(), key=lambda x: order.index(x))
        if not data.is_transposed():
            data = data.transpose().reindex(order)
        else:
            data = data.reindex(order)

    # Refseq and key_residues management.
    ref_seq = data.get_reference_sequence(seqID, key_residues) if refseq else ""

    # data and key_residues management.
    data = data.get_key_residues(key_residues)

    if clean_unused >= 0:
        data.delete_empty(clean_unused)
        data = data.clean()
        order = sorted(data.index.values.tolist(), key=lambda x: order.index(x))
        data = data.reindex(order)

    # heatmap parameters and others
    kwargs.setdefault("cmap", "Blues")  # define the color-range of the plot
    kwargs.setdefault("linewidths", 1)  # linewidths are fixed to 1
    kwargs.setdefault("square", True)   # square is True if user don't say otherwise
    # by default the color bar is horizontal
    kwargs.setdefault("cbar_kws", {"orientation": "horizontal"})

    # plot
    if not aminosY:
        data = data.transpose()
    sns.heatmap(data, ax=ax, **kwargs)

    # styling plot
    # seaborn made a change in the ticks from 0.7 to 0.8,
    # this should take care that both versions work ok.
    if LooseVersion(sns.__version__) < LooseVersion("0.8"):
        order.reverse()
    if aminosY:
        ax.yaxis.set_ticks(np.arange(0.5, len(order) + 0.5))
        ax.yaxis.set_ticklabels(order, rotation=yrotation)
        for label in ax.get_yticklabels():
            label.set_fontproperties(fp)
        ax.xaxis.set_ticks(np.arange(0.5, len(data.columns.values.tolist()) + 0.5))
        ax.xaxis.set_ticklabels(data.columns.values.tolist(), rotation=xrotation)
        ax.set_ylabel("residue type")
        if labelsize is not None:
            ax.tick_params(labelsize=labelsize)
    else:
        ax.xaxis.set_ticks(np.arange(0.5, len(order) + 0.5))
        ax.xaxis.set_ticklabels(order, rotation=xrotation)
        for label in ax.get_xticklabels():
            label.set_fontproperties(fp)
        ax.yaxis.set_ticks(np.arange(0.5, len(data.index.values.tolist()) + 0.5))
        ax.yaxis.set_ticklabels(data.index.values.tolist(), rotation=yrotation)
        ax.set_xlabel("residue type")
        if labelsize is not None:
            ax.tick_params(labelsize=labelsize)

    # marking reference sequence
    if ref_seq is not "" and refseq:
        if isinstance(border_color, int):
            border_color = sns.color_palette()[border_color]
        for i in range(len(ref_seq)):
            if aminosY:
                aa_position = (i, order.index(ref_seq[i]))
            else:
                aa_position = (order.index(ref_seq[i]), i)
            ax.add_patch(Rectangle(aa_position, 1, 1, fill=False, clip_on=False,
                                   edgecolor=border_color, lw=border_width, zorder=100))


def positional_sequence_similarity_plot( df, ax, identity_color="green", similarity_color="orange" ):
    """
    Generates a plot covering the amount of identities and positives matches from a population of designs
    to a reference sequence according to a substitution matrix.
    Input data can/should be generated with :py:func:`.positional_sequence_similarity`.

    :param df: Input data, where rows are positions and columns are `identity_perc` and `positive_perc`
    :type df: :py:class:`~pandas.DataFrame`
    :param ax: matplotlib axis to which we will plot.
    :type ax: :py:class:`~matplotlib.axes.Axes`

    """

    # Color management
    if isinstance(identity_color, int):
        identity_color = sns.color_palette()[identity_color]
    if isinstance(similarity_color, int):
        similarity_color = sns.color_palette()[similarity_color]

    y = df["positive_perc"].values
    ax.plot(range(len(y)), y, color="orange", linestyle="solid", linewidth=2)
    ax.fill_between(range(len(y)), 0, y, color=similarity_color, alpha=1)

    y = df["identity_perc"].values
    ax.plot(range(len(y)), y, color="green", linestyle="solid", linewidth=2)
    ax.fill_between(range(len(y)), 0, y, color=identity_color, alpha=1)

    ax.set_ylim(0, 1)
    ax.set_xlim(0, len(y) - 1)


def logo_plot( df, seqID, refseq=True, key_residues=None, line_break=None,
               font_size=35, colors="WEBLOGO" ):
    """
    Generates classic **LOGO** plots.

    .. ipython::

        In [1]: from rstoolbox.io import parse_rosetta_file
           ...: from rstoolbox.plot import logo_plot
           ...: import matplotlib.pyplot as plt
           ...: df = parse_rosetta_file("../rstoolbox/tests/data/input_2seq.minisilent.gz",
           ...:                         {"sequence": "B"})
           ...: df.add_reference_sequence("B", df.get_sequence("B")[0])
           ...: fig, axes = logo_plot(df, "B", refseq=True, line_break=50)
           ...: plt.tight_layout()

        @savefig sequence_logo_plot_docs.png width=5in
        In [2]: plt.show()

    :param df: Data container.
    :type df: Union[:class:`.DesignFrame`, :class:`.SequenceFrame`]
    :param seqID: Identifier of the query sequence.
    :type seqID: :class:`str`
    :param refseq: if :data:`True` (default), mark the original residues according to
        the reference sequence.
    :type refseq: :class:`bool`
    :param key_residues: Residues of interest to be plotted.
    :type key_residue: Union[:class:`int`, :func:`list` of :class:`int`, :class:`.Selection`]
    :param line_break: Force a line-change in the plot after n residues are plotted.
    :type line_break: :class:`int`
    :param font_size: Expected size of the axis font.
    :type font_size: :class:`float`
    :param colors: Colors to assign; it can be the name of a available color set or
        a dictionary with a color for each type.
    :type colors: Union[:class:`str`, :class:`dict`]

    :return: :class:`~matplotlib.figure.Figure` and
        :func:`list` of :class:`~matplotlib.axes.Axes`
    """

    class Scale( matplotlib.patheffects.RendererBase ):
        def __init__( self, sx, sy=None ):
            self._sx = sx
            self._sy = sy

        def draw_path( self, renderer, gc, tpath, affine, rgbFace ):
            affine = affine.identity().scale(self._sx, self._sy) + affine
            renderer.draw_path(gc, tpath, affine, rgbFace)

    def _letterAt( letter, x, y, yscale=1, ax=None, globscale=1.35,
                   LETTERS=None, COLOR_SCHEME=None ):
        text = LETTERS[letter]
        t = mpl.transforms.Affine2D().scale(1 * globscale, yscale * globscale) + \
            mpl.transforms.Affine2D().translate(x, y) + ax.transData
        p = PathPatch(text, lw=0, fc=COLOR_SCHEME[letter],  transform=t)
        if ax is not None:
            ax.add_artist(p)
        return p

    def _dataframe2logo( data ):
        aa = list(data)
        odata = []
        for index, pos in data.iterrows():
            pdata = []
            for k in aa:
                if pos[k] > 0.0000000:
                    pdata.append( ( k, float(pos[k]) ) )
            odata.append(sorted(pdata, key=lambda x: x[1]))
        return odata

    def _chunks(l, n):
        for i in range(0, len(l), n):
            yield l[i:i + n]

    order = ["A", "V", "I", "L", "M", "F", "Y", "W", "S", "T", "N",
             "Q", "R", "H", "K", "D", "E", "C", "G", "P"]
    data = copy.deepcopy(df)

    mpl.rcParams['svg.fonttype'] = 'none'
    # Graphical Properties of resizable letters
    path = os.path.join(
        os.path.dirname(os.path.realpath(__file__)),
        '../components/square.ttf'
    )
    fp = FontProperties(fname=path, weight="bold")
    globscale = 1.22
    letters_shift = -0.5
    LETTERS = {}
    for aa in color_scheme(colors):
        LETTERS[aa] = TextPath((letters_shift, 0), aa, size=1, prop=fp)

    # Data type management.
    if not isinstance(data, pd.DataFrame):
        raise ValueError("Input data must be in a DataFrame, DesignFrame or SequenceFrame")
    else:
        if not isinstance(data, (DesignFrame, SequenceFrame)):
            if len(set(data.columns.values).intersection(set(order))) == len(order):
                data = SequenceFrame(data)
            else:
                data = DesignFrame(data)
    if isinstance(data, DesignFrame):
        data = data.sequence_frequencies(seqID)

    # key_residues management.
    length = len(data.get_reference_sequence(seqID)) if refseq else None
    key_residues = get_selection(key_residues, seqID, list(data.index.values), length)

    # Plot
    if line_break is None:
        figsize = (len(data) * 2, 2.3 * 2)
        grid = (1, 1)
        fig  = plt.figure(figsize=figsize)
        axs  = [plt.subplot2grid(grid, (0, 0)), ]
        krs  = [key_residues, ]
    else:
        rows = int(math.ceil(float(len(data)) / line_break))
        figsize = (float(len(data) * 2 ) / rows, 2.3 * 2 * rows)
        grid = (rows, 1)
        fig  = plt.figure(figsize=figsize)
        axs  = [plt.subplot2grid(grid, (_, 0)) for _ in range(rows)]
        krs  = list(_chunks(key_residues, line_break))

    font = FontProperties()
    font.set_size(font_size)
    font.set_weight('bold')

    for _, ax in enumerate(axs):
        # Refseq and key_residues management.
        ref_seq = data.get_reference_sequence(seqID, krs[_]) if refseq else ""
        # data and key_residues management.
        _data = data.get_key_residues(krs[_])

        ticks = len(_data)
        if line_break is not None and len(_data) < line_break:
            ticks = line_break
        ax.set_xticks(np.arange(0.5, ticks + 1))
        ax.set_yticks( range(0, 2) )
        ax.set_xticklabels( _data.index.values )
        ax.set_yticklabels( np.arange( 0, 2, 1 ) )
        if ref_seq is not None:
            ax2 = ax.twiny()
            ax2.set_xticks(ax.get_xticks())
            ax2.set_xticklabels(list(ref_seq))
        sns.despine(ax=ax, trim=True)
        ax.grid(False)
        if ref_seq is not None:
            sns.despine(ax=ax2, top=False, right=True, left=True, trim=True)
            ax2.grid(False)
        ax.lines = []
        wdata = _dataframe2logo( _data )
        x = 0.5
        maxi = 0
        for scores in wdata:
            y = 0
            for base, score in scores:
                _letterAt(base, x, y, score, ax, globscale, LETTERS, color_scheme(colors))
                y += score
            x += 1
            maxi = max(maxi, y)
        for label in (ax.get_xticklabels() + ax.get_yticklabels()):
            label.set_fontproperties(font)
        if ref_seq is not None:
            for label in (ax2.get_xticklabels() + ax2.get_yticklabels()):
                label.set_fontproperties(font)

    return fig, axs
