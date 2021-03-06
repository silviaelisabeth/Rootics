__author__ = 'Silvia E Zieger'
__project__ = 'soil profile analysis'

"""Copyright 2021. All rights reserved.

This software is provided 'as-is', without any express or implied warranty. In no event will the authors be held liable 
for any damages arising from the use of this software.
Permission is granted to anyone to use this software within the scope of evaluating mutli-analyte sensing. No permission
is granted to use the software for commercial applications, and alter it or redistribute it.

This notice may not be removed or altered from any distribution.
"""

import matplotlib
import matplotlib.pylab as plt
import seaborn as sns
import numpy as np
import pandas as pd
from lmfit import Model
from scipy import stats
import time
from datetime import datetime
import PyPDF2
import h5py
from os import walk

import functions_solubilityO2 as calO2

# global parameter
sns.set_context('paper'), sns.set_style('ticks')
# grey, orange, petrol, green, yellow, light grey, blue
ls_col = list(['#4c5558', '#eb9032', '#21a0a8', '#9ec759', '#f9d220', '#96a6ab', '#1B08AA'])
# global variables
coords = dict()


# --------------------------------------------------------------------------------------------------------------------
def plot_surfacefinder(dic_dcore, dfit, dic_deriv, core, nr, figsize=(5, 3)):
    fig, ax = plt.subplots(figsize=figsize)
    fig.canvas.set_window_title('Fit profile data - core {} #{}'.format(core, nr))
    ax1 = ax.twinx()
    ax.set_xlabel('Depth [µm]'), ax.set_ylabel('O2 [mV]'), ax1.set_ylabel('1st derivative', color='#0077b6')

    c = 'O2_mV' if 'O2' in dic_dcore[core][nr].columns else dic_dcore[core][nr].columns[0]
    ax.plot(dic_dcore[core][nr].index, dic_dcore[core][nr][c], lw=0, marker='o', ms=4, color='k')
    ax.plot(dfit[core][nr][1], lw=0.75, ls=':', color='k')

    ax1.plot(dic_deriv[core][nr], lw=1., color='#0077b6')
    ax1.axvline(dic_deriv[core][nr].idxmin().values[0], ls='-.', color='darkorange', lw=1.5)
    text = 'surface level \nat {:.1f}µm'
    c = 'O2_mV' if 'O2' in dic_dcore[core][nr].columns else dic_dcore[core][nr].columns[0]
    ax.text(dic_deriv[core][nr].idxmin().values[0]*2, dic_dcore[core][nr][c].max()*1.15,
            text.format(dic_deriv[core][nr].idxmin().values[0]), ha="left", va="center", color='darkorange', size=9.5)

    sns.despine()
    ax.spines['right'].set_visible(True)
    plt.tight_layout()
    return fig, ax


def plot_shiftedData(core, dfit, data_shifted, figsize=(5, 3)):
    fig, ax = plt.subplots(figsize=figsize)
    fig.canvas.set_window_title('Profile data - core {}'.format(core))
    ax.set_ylabel('Depth [µm]'), ax.set_xlabel('O2 [mV]'),

    for nr in dfit[core].keys():
        ax.plot(data_shifted[core][nr].to_numpy(), data_shifted[core][nr].index, lw=1.5, label='sample ' + str(nr))
    ax.legend(frameon=True, fontsize=10)

    ax.axhline(0, lw=0.5, color='k')
    ax.invert_yaxis()
    sns.despine()
    plt.tight_layout()

    return fig, ax


def plot_interimsteps(dfit, dic_dcore, dic_deriv, data_shift, ls_core, plot_interim=False):
    plt.ioff()
    dfig, dfig_base, dfig_shifted = dict(), dict(), dict()
    for core in ls_core:
        # baseline shift
        dfig_base_ = dict()
        for nr in dfit[core].keys():
            fig, ax = plot_surfacefinder(dic_dcore=dic_dcore, dfit=dfit, core=core, nr=nr, dic_deriv=dic_deriv)
            if plot_interim is False:
                plt.close(fig)
            else:
                plt.show()
            dfig_base_[nr] = fig
        dfig_base[core] = dfig_base_

        # shifted data
        fig1, ax1 = plot_shiftedData(core=core, dfit=dfit, data_shifted=data_shift)
        if plot_interim is False:
            plt.close(fig1)
        else:
            plt.show()
        dfig_shifted[core] = fig1

        dfig['baseline finder'] = dfig_base
        dfig['shifted profile'] = dfig_shifted
    return dfig


def plot_O2depth_sample(core, data_shift, dO2_core, unit):
    # how many colors are required for the gradient
    colors = sns.color_palette("rocket", len(data_shift[core].keys()))

    fig, ax = plt.subplots(figsize=(5, 3))
    fig.canvas.set_window_title('Depth profile for core ' + str(core))

    for en, s in enumerate(data_shift[core].keys()):
        df = dO2_core[core][s].dropna()
        ax.plot(df['O2_'+unit], df.index, lw=1., color=colors[en], label='sample ' + str(s))
    ax.legend(frameon=True, fancybox=True)
    ax.axhline(0, lw=0.75, color='k')
    ax.set_ylabel('Depth / µm'), ax.set_xlabel('O$_2$ concentration / ' + unit)

    ax.invert_yaxis()
    sns.despine(), plt.tight_layout(), plt.show()
    return fig


def plot_penetrationDepth(core, s, df_fit, O2_pen, unit, show=False):
    plt.ioff()
    fig, ax = plt.subplots(figsize=(5, 3))
    fig.canvas.set_window_title('Penetration depth for core ' + str(core) + ' sample-' + str(s))

    # plotting part
    ax.plot(df_fit[0].to_numpy(), df_fit.index, lw=1., color='navy')
    ax.axhline(0, lw=0.75, color='k')

    # indicate penetration depth
    if len(df_fit[df_fit[0] < O2_pen].index) > 0:
        pen_h, pen_v = df_fit[df_fit[0] < O2_pen].index[0], df_fit.loc[df_fit[df_fit[0] < O2_pen].index[0], 0]
        ax.axhline(pen_h, ls=':', color='crimson')
        ax.axvline(pen_v, ls=':', color='crimson')
    else:
        pen_h, pen_v = None, None

    # general layout
    ax.set_xlim(min(df_fit[0].to_numpy()), max(df_fit[0].to_numpy()))

    ax.invert_yaxis()
    ax.set_ylabel('Depth / µm'), ax.set_xlabel('O2 concentration ' + unit)
    sns.despine(), plt.tight_layout()

    if show is False:
        plt.close(fig)
    else:
        plt.show()

    return fig, (pen_h, pen_v)


def plot_joint_penetration(core, dcore_pen, dO2_core, unit, dobj_hid, show=False):
    fig, ax = plt.subplots(figsize=(5, 3))
    fig.canvas.set_window_title('Penetration depth for core ' + str(core))

    # indicate baseline
    ax.axhline(0, lw=0.75, color='k')

    df = pd.concat([dcore_pen[core]['{}-Fit'.format(s[0])] for s in dO2_core[core].keys()], axis=1)
    df.columns = [i[0] for i in dO2_core[core].keys()]
    lines = list()
    for en, s in enumerate(df.columns):
        line, = ax.plot(df[s].dropna(), df[s].dropna().index, color=ls_col[en], lw=1., alpha=.6, label='sample-'+str(s))
        lines.append(line)
    leg = ax.legend(frameon=True, fancybox=True)

    # ------------------------------------------------------------------
    # combine legend
    lined = dict()
    for legline, origline in zip(leg.get_lines(), lines):
        legline.set_picker(5)  # 5 pts tolerance
        lined[legline] = origline

    # picker - hid curves in plot
    ls_hid = list()
    def onpick(event):
        # on the pick event, find the orig line corresponding to the
        # legend proxy line, and toggle the visibility
        legline = event.artist
        origline = lined[legline]
        vis = not origline.get_visible()
        origline.set_visible(vis)
        # Change the alpha on the line in the legend so we can see what lines have been toggled
        legline.set_alpha(1.0 if vis else 0.2)
        if origline.get_label() in ls_hid:
            # find position of label and pop/remove
            pos = ls_hid.index(origline.get_label())
            ls_hid.pop(pos)
        else:
            ls_hid.append(origline.get_label())
        fig.canvas.draw()
    fig.canvas.mpl_connect('pick_event', onpick)

    # collect all hidden curves
    dobj_hid[core] = ls_hid

    # layout
    ax.set_xlim(-10, df.max().max()*1.05),
    ax.set_ylim(df.idxmin().max()*1.05, df.idxmax().min()*1.05)
    ax.set_ylabel('Depth / µm'), ax.set_xlabel('O2 concentration ' + unit)
    sns.despine(), plt.tight_layout()

    if show is False:
        plt.close(fig)
    else:
        plt.show()
    return fig, ax


def plot_indicate_penetration(dcore_pen, dO2_core, core, dhiden_object, unit, dpen_all, ax, fig):
    ax.clear()

    # indicate baseline
    ax.axhline(0, lw=0.75, color='k')

    # samples that should not be included in averaging
    ls_shid = [int(i.split('-')[1]) for i in dhiden_object[core]]

    # all samples for core
    ls_sind = list()
    [ls_sind.append(i) for i in dpen_all.loc[core].index if i != 'mean' and i != 'std']

    # remaining samples for average penetration depth
    ls_remain = list()
    [ls_remain.append(i) for i in ls_sind if i not in ls_shid]

    # re-plot only the ones that are shown
    df = pd.concat([dcore_pen[core]['{}-Fit'.format(s[0])] for s in dO2_core[core].keys()], axis=1)
    df.columns = [i[0] for i in dO2_core[core].keys()]
    for en, s in enumerate(df.columns):
        if s in ls_remain:
            ax.plot(df[s].dropna(), df[s].dropna().index, color=ls_col[en], lw=1., alpha=0.5, label='sample-' + str(s))
    ax.legend(frameon=True, fancybox=True, loc=2)

    # indicate penetration depth mean + std according to visible curves
    mean_ = dpen_all.loc[core].loc[ls_remain].mean().to_numpy()
    std_ = dpen_all.loc[core].loc[ls_remain].std().to_numpy()
    dpen_all.loc[core].loc['mean', :], dpen_all.loc[core].loc['std',:] = mean_, std_

    ax.axhline(mean_[0], ls=':', color='crimson')
    ax.fill_betweenx([mean_[0] - std_[0], mean_[0] + std_[0]], -50, 500, lw=0, alpha=0.5, color='grey')
    ax.axvline(mean_[1], ls=':', color='crimson')
    ax.fill_between([mean_[1] - std_[1], mean_[1] + std_[1]], -5000, 5000, lw=0, alpha=0.5, color='grey')

    fig.text(0.6, .85, 'mean: {:.2f}{}'.format(mean_[0], unit), {'fontsize': 8}, va="top", ha="right")
    # layout
    ax.set_xlim(-10, df.max().max()*1.05),
    ax.set_ylim(df.idxmin().max()*1.05, df.idxmax().min()*1.05)
    ax.set_ylabel('Depth / µm'), ax.set_xlabel('O2 concentration ' + unit)
    sns.despine(), plt.tight_layout()

    fig.canvas.draw()
    return fig, ax, dpen_all


def plot_pHProfile(ls_core, dic_dcore, plot_res=True):
    dfig = dict()
    for core in ls_core:
        # plot pH depth profile
        plt.ioff()
        fig, ax = plt.subplots(figsize=(5, 3))
        fig.canvas.set_window_title('pH profile of core ' + str(core))

        ax.axhline(0, lw=0.5, color='k')
        for s in dic_dcore[core].keys():
            ax.plot(dic_dcore[core][s]['pH'], dic_dcore[core][s]['pH'].index, lw=1., ls='-.',
                    label='sample-{}'.format(s))
        ax.legend(frameon=True, fancybox=True)
        ax.invert_yaxis(), ax.set_xlim(6.5, 8.5)
        ax.set_ylabel('Depth / µm'), ax.set_xlabel('pH value')
        sns.despine(), plt.tight_layout()

        # either show or hide figure
        if plot_res is True:
            plt.show()
        else:
            pass
        # save figure to dictionary
        dfig[core] = fig
    return dfig


def GUI_rawProfile(core, ls_core, O2data, grp_label, fig=None, ax=None, show=True):
    plt.ioff()

    # identify closest value in list
    core_select = closest_core(ls_core=ls_core, core=core)

    # identify column to plot
    for c in O2data[core_select][list(O2data[core_select].keys())[0]].columns:
        if 'mV' in c:
            col2plot = c

    # initialize figure
    if ax is None:
        fig, ax = plt.subplots(figsize=(3, 4))
    else:
        ax.cla()
    ax.set_xlabel('O2 concentration / mV'), ax.set_ylabel('Depth / µm')
    ax.invert_yaxis()

    if core_select != 0:
        ax.title.set_text('O2 depth profile for {} {}'.format(grp_label, core_select))
        ax.axhline(0, lw=.5, color='k')
        for en, nr in enumerate(O2data[core_select].keys()):
            ax.plot(O2data[core_select][nr][col2plot], O2data[core_select][nr].index, lw=1, ls='-.', marker='.',
                    color=ls_col[en], alpha=0.75, label='sample ' + str(nr))
        ax.legend(frameon=True, fontsize=10)

    # update layout
    fig.tight_layout(pad=1.5)

    if show is False:
        plt.close(fig)
    else:
        fig.canvas.draw()

    return fig


def GUI_baslineShift(data_shift, core, ls_core, plot_col, grp_label, fig=None, ax=None, show=True):
    plt.ioff()

    # identify closest value in list
    core_select = closest_core(ls_core=ls_core, core=core)

    # identify column to plot
    for c in data_shift[core_select][list(data_shift[core_select].keys())[0]].columns:
        if plot_col in c:
            col2plot = c
            if '_' in col2plot:
                unit = col2plot.split('_')[1]
            else:
                unit = col2plot.split('(')[1].split(')')[0]

    # plot figure
    if ax is None:
        fig, ax = plt.subplots(figsize=(3, 4))
    else:
        ax.cla()

    if core_select == 0 or not data_shift:
        pass
    else:
        ax.title.set_text('Sediment water interface profile (SWI) for {} {}'.format(grp_label, core_select))
    ax.set_xlabel('O2 / {}'.format(unit)), ax.set_ylabel('Depth / µm')
    ax.invert_yaxis()

    if core_select != 0:
        ax.axhline(0, lw=.5, color='k')
    if core_select == 0:
        pass
    else:
        df = data_shift[core_select]
        for en, nr in enumerate(df.keys()):
            ax.plot(df[nr][col2plot].to_numpy(), df[nr].index, lw=.75, ls='-.', marker='.', color=ls_col[en], alpha=.75,
                    label='sample ' + str(nr))
        ax.legend(frameon=True, fontsize=10)

        max_ = np.max([max(df[nr][col2plot].to_numpy()) for nr in df.keys()])
        minPot = np.min([min(df[nr][col2plot].to_numpy()) for nr in df.keys()])
        min_ = minPot*0.5 if int(minPot) > 0 else -1 * np.abs(max_) * 0.1
        ax.set_xlim(min_, np.abs(max_)*1.05)

    # layout editing - ticks orientation and frame line width
    [x.set_linewidth(.5) for x in ax.spines.values()]
    ax.tick_params(axis='both', bottom=True, top=False, direction='out', length=5, width=0.75)
    plt.tight_layout()

    # show or hide figure plot
    plt.close(fig) if show is False else fig.canvas.draw()
    return fig


def GUI_baslineShiftCore(data_shift, core_select, plot_col, grp_label, fig, ax):
    ax.cla()

    # identify the columns to plot
    s = list(data_shift.keys())[0]
    col2plot, unit = None, None
    for i in data_shift[s].columns:
        if isinstance(plot_col, int):
            if plot_col == i:
                col2plot = i
                if plot_col == 0:
                    unit = 'mV'
                else:
                    if '_' in col2plot:
                        unit = col2plot.split('_')[1]
                    else:
                        unit = col2plot.split('(')[1].split(')')[0]
        else:
            if plot_col in i:
                col2plot = i
                if plot_col == 0:
                    unit = 'mV'
                else:
                    if '_' in col2plot:
                        unit = col2plot.split('_')[1]
                    else:
                        unit = col2plot.split('(')[1].split(')')[0]

    if unit is None:
        print('Nothing to plot here. Expected column not in dataframe.')
    else:
        # plot figure
        if ax is None:
            fig, ax = plt.subplots(figsize=(3, 4))
        ax.title.set_text('Sediment water interface profile (SWI) for {} {}'.format(grp_label, core_select))
        ax.set_xlabel('O2 / {}'.format(unit)), ax.set_ylabel('Depth / µm')
        ax.invert_yaxis()

        # draw the surface
        ax.axhline(0, lw=.5, color='k')
        # plot the depth corrected profiles for the selected core
        for en, nr in enumerate(data_shift.keys()):
            # draw the recorded points of the sample
            ax.plot(data_shift[nr][col2plot].to_numpy(), data_shift[nr].index, lw=.5, ls='-.', marker='.', alpha=.75,
                    color=ls_col[en], label='sample ' + str(nr))
            ax.legend(frameon=True, fontsize=10)

            max_ = max(data_shift[nr][col2plot].to_numpy())
            minPot = min(data_shift[nr][col2plot].to_numpy())
            min_ = minPot * 0.5 if int(minPot) > 0 else -1 * np.abs(max_) * 0.1
            ax.set_xlim(min_, np.abs(max_) * 1.05)

        # layout editing - ticks orientation and frame line width
        [x.set_linewidth(.5) for x in ax.spines.values()]
        ax.tick_params(axis='both', bottom=True, top=False, direction='out', length=5, width=0.75)
        plt.tight_layout(), fig.canvas.draw()
    return fig


# --------------------------------------------------------------------------------------------------------------------
def _gompertz_curve(x, a, b, c):
    """ Gompertz curve to describe a positive s-shaped curve with the following parameter:
    :param x:
    :param a:   maximal x-level
    :param b:   shift along x-axis
    :param c:   slope
    :return:
    """
    y = a * np.exp(-1 * np.exp(b - c * x))-a
    return y


def _gompertz_curve_adv(x, a, b, c, d):
    """ Gompertz curve to describe a positive s-shaped curve with the following parameter:
    :param x:
    :param a:   maximal x-level
    :param b:   shift along x-axis
    :param c:   slope
    :return:
    """
    y = a * (np.exp(-1 * np.exp(b - c * x))-1) + d
    return y


# --------------------------------------------------------------------------------------------------------------------
def loadMeas4GUI(file):
    # load sheets from excel file
    df_excel = pd.read_excel(file, sheet_name=None)

    # identify sensors used
    dfsens = df_excel['Sensors'][['Type', 'Unit']]

    # check requirements for meta data and correlation (where applicable)
    col = precheckMeta(ls_cols=df_excel.keys())
    cols = precheckCorrelation(ls_cols=df_excel.keys())

    # split full dataframe with all profiles into individual samples belonging to certain groups
    dprof = loadProfile(dfsens=dfsens, dfprof=df_excel['Profiles'])

    # additional prep to fit it to the previous version
    dprof = prepAnalytes(dprof=dprof)

    # split full dataset into individual profiles and label them according to sample ID and group (e.g. "core")
    dprofiles = splitIntoSamples(dprof=dprof, df_meta=df_excel[col])

    return dprofiles


def precheckMeta(ls_cols):
    # meta data sheet
    if 'Metadata' not in ls_cols and 'metadata' not in ls_cols:
        print('warning - include an additional metadata sheet as described in the manual.')
        col = None
    else:
        col = 'Metadata' if 'Metadata' in ls_cols else 'metadata'
    return col


def precheckCorrelation(ls_cols):
    # pH and H2S correlation sheet
    if 'Correlation' not in ls_cols and 'correlation' not in ls_cols:
        # print('Warning - if total sulfide shall be calculated, profive an additional correlation sheet as described in '
        #       'the manual.')
        col = None
    else:
        col = 'Correlation' if 'Correlation' in ls_cols else 'correlation'
    return col


def splitIntoSamples(dprof, df_meta):
    dprofiles = dict()
    # split full dataset into individual profiles and label them according to sample ID and group (e.g. "core")
    for par in dprof.keys():
        if 'Oxygen' in par or 'oxygen' in par:
            label_par = 'O2_all'
        elif 'Redox' in par or 'ep' in par or 'Ep' in par or 'redox' in par:
            label_par = 'EP_all'
        else:
            label_par = par + '_all'

        # prepare label for all eventualities
        if 'Sensor' in label_par:
            label_par = label_par.split(' ')[-1]

        # metadata sheet
        ls_empty = list()
        [ls_empty.append(i) for i in dprof[par].index if pd.isna(dprof[par].loc[i]).all()]

        # identify index column (Time)
        colInd = None
        for i in dprof[par].columns:
            if 'Time' in i:
                colInd = i

        # split into profiles for individual samples and cores; add Nr and group information
        dprofile = splitDF2samples(dfex=df_meta, ls_empty=ls_empty, dprof=dprof, par=par, colInd=colInd)

        # add sample-ID and group label to DF for sorting
        dprofileS = addInfo2DF(dprofile=dprofile)

        # dictionary of all sensors containing a full dataframe of all profiles sorted by group-label with a running
        # sample-ID. The dataframe consists of the following columns: Nr	Core	Depth	concentration	signal
        dprofiles[label_par] = dprofileS.dropna()
    return dprofiles


def splitDF2samples(dfex, ls_empty, dprof, par, colInd):
    if 'code' in dfex.columns:
        c = 'code'
    elif 'Code' in dfex.columns:
        c = 'Code'
    group = dfex[c].to_numpy()[0].split(' ')[0]
    for c in dprof[par].columns:
        if 'Depth' in c:
            colD = c
        else:
            pass

    dprofile, start = dict(), 0
    for r in range(len(ls_empty)):
        if r != 0:
            start = ls_empty[r - 1]
        df = dprof[par].loc[start:ls_empty[r] - 1].dropna().sort_values(by=colD)
        # add sample-ID and group info for all but the last profile
        df.loc[:, 'Nr'] = [dfex.loc[r].to_numpy()[0]] * len(df.index)
        df.loc[:, group] = [int(dfex.loc[r].to_numpy()[1].split(' ')[1])] * len(df.index)
        dprofile[tuple(dfex.loc[r].to_numpy()[:2])] = df.set_index(colInd)

        if r == len(ls_empty) - 1:
            # separate procedure for the last profile
            df = dprof[par].loc[ls_empty[r] + 1:].dropna().sort_values(by=colD)
            df.loc[:, 'Nr'] = [dfex.loc[r].to_numpy()[0] + 1] * len(df.index)
            df.loc[:, group] = [int(dfex.loc[r].to_numpy()[1].split(' ')[1])] * len(df.index)
            dprofile[tuple(dfex.loc[r + 1].to_numpy()[:2])] = df.set_index(colInd)
    return dprofile


def sortCols4DF(ls_cols, group):
    cols_sort = list()
    for c in ls_cols:
        if 'Nr' in c or 'nr' in c:
            cols_sort.append((0, c))
        elif group in c:
            cols_sort.append((1, c))
        elif 'Depth' in c:
            cols_sort.append((2, c))
        elif 'sig' in c or 'Sig' in c:
            cols_sort.append((4, c))
        else:
            cols_sort.append((3, c))
    cols_sort = list(pd.DataFrame(cols_sort).sort_values(by=0)[1].to_numpy())
    return cols_sort


def addInfo2DF(dprofile):
    # identify group label and columns order
    group = list(dprofile.keys())[0][1].split(' ')[0]
    ls_cols = dprofile[list(dprofile.keys())[0]].columns.to_numpy()

    # sort columns for dataframe
    cols_sort = sortCols4DF(ls_cols=ls_cols, group=group)

    # adjust DF
    for k in dprofile.keys():
        dprofile[k] = dprofile[k][cols_sort]

    # combine all sample-IDs and cores to one full DF
    dprofileS = pd.concat(dprofile)
    dprofileS.index = np.arange(len(dprofileS.index))

    return dprofileS


# -------------------------------------------------------------------------------------------------------
def loadProfile(dfsens, dfprof):
    # split where blank line is
    arrSens = splitProfiles2Samples(dfsens=dfsens)

    # split into sensors
    ls_sens, head = list(), dfprof.columns
    [ls_sens.append((en, c)) for en, c in enumerate(head) if 'Sensor' in c]

    # read profiles
    dprof = dict()
    for s in range(len(ls_sens)):
        if s == len(ls_sens) - 1:
            df = (dfprof.loc[:, head[ls_sens[s][0]]:])
            dprof[arrSens[s][0]] = df.T.set_index(0).T
        else:
            df = dfprof.loc[:, head[ls_sens[s][0]]:head[ls_sens[s + 1][0] - 1]]
            dprof[arrSens[s][0]] = df.T.set_index(0).T
    return dprof


def prepAnalytes(dprof):
    if 'Oxygen' in dprof.keys() or 'oxygen' in dprof.keys():
        ls_cols = list()
        for c in dprof['Oxygen'].columns:
            if 'Concentration' in c:
                ls_cols.append('O2_µmol/l')
            elif 'Signal' in c:
                ls_cols.append('O2_mV')
            else:
                ls_cols.append(c)
        dprof['Oxygen'].columns = ls_cols

    if 'pH' in dprof.keys():
        ls_cols = list()
        for c in dprof['pH'].columns:
            if 'Signal' in c:
                ls_cols.append('pH_mV')
            else:
                ls_cols.append(c)
        dprof['pH'].columns = ls_cols

    for c in dprof.keys():
        if 'EP' in c or 'Ep' in c or 'ep' in c:
            ls_cols = list()
            for co in dprof[c].columns:
                if 'Concentration' in co:
                    ls_cols.append('EP')
                elif 'Signal' in co:
                    ls_cols.append('EP_mV')
                else:
                    ls_cols.append(co)
            dprof[c].columns = ls_cols
        elif 'Redox' in c or 'redox' in c:
            ls_cols = list()
            for co in dprof[c].columns:
                if 'Concentration' in co:
                    ls_cols.append('EP')
                elif 'Signal' in co:
                    ls_cols.append('EP_mV')
                else:
                    ls_cols.append(co)
            dprof[c].columns = ls_cols

    for c in dprof.keys():
        if 'H2S' in c:
            ls_cols = list()
            for co in dprof[c].columns:
                if 'Concentration' in co:
                    ls_cols.append('H2S_µM')
                elif 'Signal' in co:
                    ls_cols.append('H2S_mV')
                else:
                    ls_cols.append(co)
            dprof[c].columns = ls_cols

    return dprof


def splitProfiles2Samples(dfsens):
    # split where blank line is
    ls_end = list()
    [ls_end.append(en) for en, i in enumerate(dfsens.index) if pd.isna(dfsens.loc[i].to_numpy()).all()]
    arrSens = np.array(dfsens.loc[:ls_end[0] - 1])
    return arrSens


# ------------------------------------------------------------------------------
def load_measurements(dsheets, ls_core, para):
    dic_dcore, dls_nr = dict(), dict()
    for core in ls_core:
        ls_nr = list(dict.fromkeys(dsheets[dsheets[dsheets.columns[0]] == core].index))
        dls_nr[core] = ls_nr

        # prepare table (index = depth)
        dcore = dict()
        for n in ls_nr:
            # identify the depth column
            col_ = [c for c in dsheets.columns if 'Depth' in c]
            ls_name = [dsheets.loc[:, : col_[0]].columns[-2]]

            # get individual samples belonging to the same core
            dfcore = dsheets[dsheets[dsheets.columns[0]] == core]

            # oxygen profiles
            if 'O2' in para or 'o2' in para:
                df = dfcore[dfcore.index == n].set_index(col_[0]).dropna()

                # crop dataframe of sample --> remove core information
                ls_col = list()
                [ls_col.append(i) for i in list(df.columns) if 'M' in i or 'mV' in i or 'mol' in i]
                dcore[n] = df[ls_col].sort_index()
            elif 'H2S' in para or 'h2s' in para:
                df = dfcore[dfcore.index == n].set_index(col_[0]).dropna()
                # crop dataframe of sample --> remove core information
                [ls_name.append(i) for i in list(df.columns) if 'H2S' in i and 'M' in i]
                [ls_name.append(i) for i in list(df.columns) if 'H2S' in i and 'mV' in i]
                # no negative concentration shall be possible --> zero correction
                for c in ls_name[1:]:
                    df[c] = df[c] - df[c].min()
                dcore[n] = df[ls_name].sort_index()
            elif 'EP' in para or 'Ep' in para or 'ep' in para:
                [ls_name.append(i) for i in dsheets.loc[n].columns if 'EP' in i and '_mV' in i]
                df = dsheets.loc[n].set_index(col_[0])[ls_name].dropna()
                dcore[n] = df[df[ls_name[0]] == core].sort_index()
            elif 'pH' in para:
                df = dfcore[dfcore.index == n].set_index(col_[0]).dropna()
                dcore[n] = df.sort_index()
            else:
                df = dsheets.set_index(col_[0]).dropna()
                dcore[n] = df[df[ls_name[0]] == core]
        dic_dcore[core] = dcore
    return dic_dcore, dls_nr, ls_name


def read_hdf5(file):
    f = h5py.File(file, 'r')

    ls_page = list()
    [ls_page.append(i.split(' ')[0]) for i in list(f.keys()) if i.split(' ')[0] not in ls_page]

    dic_pages = dict()
    for p in ls_page:
        title = ''.join([i.astype('U13')[0] for i in f[ls_page[0] + ' info']])
        unit = ''.join([[el.decode('UTF-8') for el in i][0] for i in f[ls_page[0] + ' unit']])
        df = pd.DataFrame(list(f[p + ' data']), index=list(f[p + ' index']), columns=list(f[p + ' columns']))
        df.columns.name, df.index.name = 'Temperature degC', 'salinity'

        dic_pages[int(p.split('-')[1])] = (title, df, unit)
    return dic_pages


def _loadFile4GUI(file):
    # load measurement file as it was given by the measurement software
    df_excel = pd.read_excel(file, sheet_name=None)

    # import meta data and pre-check whether file contains metadata - if not, return warning
    if 'Metadata' in df_excel.keys():
        col = 'Metadata'
    elif 'metadata' in df_excel.keys():
        col = 'metadata'
    else:
        #!!!TODO: have it as a try function - in case open an additional window
        print('WARNING - metadata required')
    df_meta = df_excel[col].set_index(['deployment', 'code'])
    df_meta = df_meta.T.dropna().T

    # split profiles into sensors
    # what type of sensors are used?
    ls_analytes = list()
    for c in df_meta.columns:
        if c.split('.')[0] not in ls_analytes:
            ls_analytes.append(c.split('.')[0])

    # get sensor ID
    ls = list()
    [ls.append(i) for i in df_excel['Profiles'].columns if 'Sensor' in i]

    # load profiles for each sensor
    dsens = dict(map(lambda i: (i, profileSensor(df_profile=df_excel['Profiles'], ls_analytes=ls_analytes,
                                                 ID=int(i.split(' ')[-1]))), ls))
    # split profiles into different samples / cores and find the name for the excel sheet "analyte_all"
    dout = dict(map(lambda s: (dsens[s][0] + '_all', _split2Samples(dsens=dsens, df_meta=df_meta, s=s)), ls))

    return dout


def prep4saveRes(dout, results, dpenStat, typeCalib=None, o2_dis=None, temperature=None, salinity=None, pene2=None):
    # handle raw profiles to one dataframe results['raw data']
    if 'O2 raw data' in results.keys():
        dcore_raw = dict()
        for c in results['O2 raw data'].keys():
            dcore_raw[c] = pd.concat(results['O2 raw data'][c], axis=1)
        dout['O2 raw data'] = pd.concat(dcore_raw, axis=1)

    # handle fit and derivative - results['fit'], results['derivative']
    if 'O2 fit' in results.keys():
        dcore_fit, dcore_der = dict(), dict()
        for c in results['O2 fit'].keys():
            # fit
            df_fit = pd.concat([results['O2 fit'][c][s][1] for s in results['O2 fit'][c].keys()], axis=1)
            df_fit.columns = results['O2 fit'][c].keys()
            dcore_fit[c] = df_fit
            # 1st derivative
            dcore_der[c] = pd.concat([results['O2 derivative'][c][s][0] for s in results['O2 derivative'][c].keys()],
                                     axis=1)
        dout['fit_mV'] = pd.concat(dcore_fit, axis=1)
        dout['derivative_mV'] = pd.concat(dcore_der, axis=1)

    # handle SWI corrected - results['SWI corrected']
    if 'O2 SWI corrected' in results.keys():
        dcore_swi = dict()
        # only potential data 'O2_mV'
        ddata = results['O2 SWI corrected']
        for c in ddata.keys():
            # either µmol/L or mV -> take the first columns
            col = ddata[c][list(ddata[c].keys())[0]].columns[-1]
            df = pd.concat([ddata[c][s][col] for s in ddata[c].keys()], axis=1)
            df.columns = ddata[c].keys()
            dcore_swi[c] = df
        dout['SWIcorrected {}'.format(col)] = pd.concat(dcore_swi, axis=1)

    # handle o2 profiles - results['O2 profile']
    if 'O2 profile' in results.keys():
        dic = dict()
        for c in results['O2 profile'].keys():
            dic[c] = pd.concat(results['O2 profile'][c], axis=1)
        dout['O2 profile'] = pd.concat(dic, axis=1)

    # handle penetration depth - results['penetration depth']
    if 'O2 penetration depth' in results.keys():
        df = dict(map(lambda k: (k, pd.DataFrame(dpenStat[k])), dpenStat.keys()))
        ddf = pd.concat(df, axis=1)
        col_new = ddf.columns.levels[0]
        ddf.columns = col_new

        # ddata = results['O2 penetration depth']
        # dpen = dict()
        # for c in ddata.keys():
        #     ls_rel = list()
        #     [ls_rel.append(k) for k in list(ddata[c].keys()) if 'penetration' in k]
        #     df = pd.DataFrame([ddata[c][k] for k in ls_rel], index=[int(i.split('-')[0]) for i in ls_rel],
        #                       columns=['mean', 'std'])
            # # add mark for excluded objects
            # df.loc[:, 'outlier'] = [None] * len(df.index)
            # if c in results['O2 hidden objects'].keys():
            #     for s in results['O2 hidden objects'][c]:
            #         df.loc[int(s.split('-')[-1]), 'outlier'] = 'X'
            #
            # # add average penetration depth for core
            # df.loc['average', :] = df[df['outlier'] != 'X'].mean().values
            #
            # # add all samples of the core to the penetration dictionary and the general output dictionary
            # dpen[c] = df
        dout['penetration depth'] = ddf # pd.concat(dpen, axis=0)

    # meta data
    if typeCalib:
        if 'recalibration' in typeCalib:
            dmeta = pd.DataFrame([typeCalib, o2_dis, temperature, salinity, pene2], columns=[''],
                                 index=['', 'dissolved O2', 'temp degC', 'salinity', 'sensor LoD'])
        else:
            dmeta = pd.DataFrame([typeCalib], index=[''], columns=[''])
        dout['meta data'] = dmeta
    return dout


def prepDataH2Soutput(dout, results):
    # handle raw profiles to one dataframe results['raw data']
    if 'H2S profile raw data' in results.keys():
        dcore_raw = dict()
        for c in results['H2S profile raw data'].keys():
            dcore_raw[c] = pd.concat(results['H2S profile raw data'][c], axis=1)
        dout['H2S profile raw data'] = pd.concat(dcore_raw, axis=1)

    # adjusted data
    if 'H2S profile total sulfide' in results.keys():
        dcore_tsulf = dict()
        ddata = results['H2S profile total sulfide']
        for c in ddata.keys():
            # -> take the last column
            col = ddata[c][list(ddata[c].keys())[0]].columns[-1]
            df = pd.concat([ddata[c][s][col] for s in ddata[c].keys()], axis=1)
            df.columns = ddata[c].keys()
            dcore_tsulf[c] = df
        dout['Depth profile total sulfide'] = pd.concat(dcore_tsulf, axis=1)

    if 'H2S adjusted' in results.keys():
        dcore_swi = dict()
        for c in results['H2S adjusted'].keys():
            dcore_swi[c] = pd.concat(results['H2S adjusted'][c], axis=1)
        dout['H2S adjusted'] = pd.concat(dcore_swi, axis=1)

    # handle penetration depth - results['penetration depth']
    if 'H2S sulfidic front' in results.keys():
        ddata = results['H2S sulfidic front']
        dpen = dict()
        for c in ddata.keys():
            df = pd.DataFrame(ddata[c])
            # add mark for excluded objects
            df.loc[:, 'outlier'] = [None] * len(df.index)
            if c in results['H2S hidden objects'].keys():
                for s in results['H2S hidden objects'][c]:
                    df.loc[s, 'outlier'] = 'X'
            dpen[c] = df
        dout['penetration depth'] = pd.concat(dpen, axis=0)

    # meta data
    dm = pd.DataFrame([results['temperature degC'], results['salinity PSU']], index=['temp degC', 'salinity PSU'])
    df_meta1 = results['pH - H2S correlation']
    colNew = df_meta1.columns
    df_meta1.loc[0, :] = colNew
    df_meta1.columns = np.arange(len(df_meta1.columns))
    dmeta = pd.concat([dm, results['pH - H2S correlation']], axis=0, ignore_index=True)
    dmeta.index = ['temp degC', 'salinity PSU', 'pH - H2S correlation'] + list(np.arange(len(df_meta1.index)-1))
    dout['meta data'] = dmeta
    return dout


def prepDataEPoutput(dout, results):
    # handle raw profiles to one dataframe results['raw data']
    if 'EP raw data' in results.keys():
        dcore_raw = dict()
        for c in results['EP raw data'].keys():
            dcore_raw[c] = pd.concat(results['EP raw data'][c], axis=1)
        dout['EP raw data'] = pd.concat(dcore_raw, axis=1)

    # adjusted data
    if 'EP adjusted' in results.keys():
        dcore_adj = dict()
        for c in results['EP adjusted'].keys():
            dcore_adj[c] = pd.concat(results['EP adjusted'][c], axis=1)
        dout['EP adjusted'] = pd.concat(dcore_adj, axis=1)

    return dout


def _actualFolderName(savePath, cfolder, rlabel='run'):
    # check whether file exist already in folder
    ls_folder = next(walk(savePath), (None, None, []))[1]  # returns all the sub-folder
    count = 0
    for f in ls_folder:
        if cfolder in f:
            count += 1
    savefolder = savePath + cfolder + '_' + rlabel + str(count) + '/'
    return savefolder


def _actualFileName(savePath, file=None, clabel='output', rlabel='run'):
    # check whether file exist already in folder
    ls_folder = next(walk(savePath), (None, None, []))[2]  # [] if no file

    now = datetime.now().strftime("%Y%d%m-%H:%M:%S")
    addstr = now
    if ls_folder:
        ls_addstr = list()
        for f in ls_folder:
            if '~' not in f:
                if '-' + rlabel in f.split('_')[0]:
                    ls_addstr.append(int(f.split('-' + rlabel)[1].split('_')[0]) + 1)
                    if ls_addstr:
                        addstr = f.split(rlabel)[0] + rlabel + str(max(ls_addstr)) + '_'
                    else:
                        addstr = f.split(rlabel)[0] + rlabel + str(0) + '_'
    else:
        addstr = clabel + "-" + rlabel + str(0) + "_"
    if file:
        savename = savePath + '/' + addstr + file.split('/')[-1]
    else:
        savename = savePath + '/' + addstr

    # compatibility mode
    if savename.split('.')[1] != 'xlsx':
        savename = savename.split('.')[0] + '.xlsx'
    return savename


def save_rawExcel(dout, file, savePath):
    savename = _actualFileName(savePath=savePath, file=file, clabel='output', rlabel='run')

    # actually saving DataFrame to excel
    writer = pd.ExcelWriter(savename)
    for key in dout.keys():
        dout[key].to_excel(writer, sheet_name=key)
    writer.save()
    writer.close()


def save_hdf5(dtab_sal, fname):
    h = h5py.File(fname, 'w')
    for k, v in dtab_sal.items():
        asciiList = [n.encode("utf-8", "ignore") for n in v[0]]
        h.create_dataset('page-{} info'.format(k), (len(asciiList), 1), 'S13', asciiList)
        asciiList = [n.encode("utf-8", "ignore") for n in v[2]]
        h.create_dataset('page-{} unit'.format(k), (len(asciiList), 1), 'S13', asciiList)

        h.create_dataset('page-{} index'.format(k), data=list(v[1].index))
        h.create_dataset('page-{} columns'.format(k), data=list(v[1].columns))
        h.create_dataset('page-{} data'.format(k), data=np.array(v[1], dtype=float))
    h.close()


# --------------------------------------------------------------------------------------------------------------------
def closest_core(ls_core, core):
    if isinstance(core, str):
        core_select = core
    else:
        if core == 0 or not ls_core:
            core_select = 0
        else:
            core_select = min(ls_core, key=lambda x: abs(x - core))
    return core_select


def removeGrpLabel(ls, grp_label, sep=' '):
    lsnew = list()
    for p in ls:
        if grp_label in p:
            lsnew.append(p.split(sep)[1])
        else:
            lsnew.append(p)
    return lsnew


# --------------------------------------------------------------------------------------------------------------------
def profileSensor(df_profile, ls_analytes, ID):
    ls_sens, lsColAll = list(), list()
    for en, s in enumerate(df_profile.columns):
        if 'Sensor' in s:
            ls_sens.append((en, s))
        lsColAll.append(s)

    # include the analyte for the dict (sensor 1)
    if ID < len(ls_sens):
        end_ = ls_sens[ID][0]
    else:
        end_ = None
    return ls_analytes[ID-1], df_profile[lsColAll[ls_sens[ID-1][0]:end_]].T.set_index(0).T


def _split2Samples(dsens, df_meta, s):
    a = dsens[s][0]

    # find blank line
    lsPosNaT = list()
    for en, t in enumerate(dsens[s][1]['Time'].values):
        if pd.isnull(t) is True:
            lsPosNaT.append(en)

    # make time the index to sort
    dsamples = dict()
    for n in range(len(lsPosNaT)+1):
        if n == 0:
            start = None
            stop = lsPosNaT[n]
        elif n == len(lsPosNaT):
            start = lsPosNaT[-1]+1
            stop = None
        else:
            start = lsPosNaT[n-1]+1
            stop = lsPosNaT[n]
        dsamples['Nr ' + str(n+1)] = dsens[s][1].loc[start:stop].set_index('Time')

    # rename the columns to include the analyte
    ls_col = list()
    for c in dsamples[list(dsamples.keys())[0]].columns:
        if 'centration' in c:
            ls_col.append(a + '_' + c.split('(')[-1].split(')')[0])
        elif 'gnal' in c:
            ls_col.append(a + '_' + c.split('(')[-1].split(')')[0])
        else:
            ls_col.append(c)

    # add column with core assignment depending on metadata for each sample (running number)
    for k in dsamples.keys():
        dsamples[k].columns = ls_col
        coreID = int(df_meta.loc[int(k.split(' ')[1])].index[0].split(' ')[1])
        dsamples[k]['Core'] = [coreID]*len(dsamples[k])
        dsamples[k]['Nr'] = [int(k.split(' ')[1])] * len(dsamples[k])

    # dataframe of one sensor - indicated with core and nr (running number set as index)
    # equals one sheet in the excel output file
    df = pd.concat(dsamples).set_index('Nr')

    # re-arrange columns core first, then the rest
    colNew = ['Core'] + list(df.columns[:-1].to_numpy())
    df = df[colNew]
    return df


def fit_baseline(ls_core, ls_nr, dic_dcore, steps, gmod, adv):
    dfit, dic_deriv = dict(), dict()
    for core in ls_core:
        dfit_, dic_deriv_ = dict(), dict()
        for nr in ls_nr[core]:
            [res, df_fit, df_fitder, df_fitder2,
             xshift] = baseline_finder(dic_dcore=dic_dcore, core=core, nr=nr, steps=steps, model=gmod, adv=adv)
            dfit_[nr], dic_deriv_[nr] = (res, df_fit, xshift), (df_fitder, df_fitder2)
        dfit[core] = dfit_
        dic_deriv[core] = dic_deriv_
    return dfit, dic_deriv


def baseline_finder(dic_dcore, core, nr, steps, model, adv):
    # curve fit according to selected model
    xdata = dic_dcore[core][nr].index
    c = 'O2_mV' if 'O2' in dic_dcore[core][nr].columns else dic_dcore[core][nr].columns[0]
    ydata = dic_dcore[core][nr][c]

    # initial parameters
    if adv is True:
        para = model.make_params(a=-int(ydata.loc[xdata[:3]].mean()), b=.001, c=.001,
                                 d=-int(ydata.loc[xdata[-3:]].mean()))
    else:
        para = model.make_params(a=-int(ydata.loc[xdata[:3]].mean()), b=.001, c=.001)
    res = model.fit(ydata.to_numpy(), para, x=xdata)

    # ................................................................
    # 1st derivative
    arg = [res.params[p].value for p in res.params.keys()]
    xnew = np.linspace(xdata[0], xdata[-1], num=int((xdata[-1]-xdata[0])/steps+1))
    if adv is True:
        yfit = _gompertz_curve_adv(x=xnew, a=arg[0], b=arg[1], c=arg[2], d=arg[3])
    else:
        yfit = _gompertz_curve(x=xnew, a=arg[0], b=arg[1], c=arg[2])

    df_fit = pd.DataFrame(yfit, index=xnew)
    df_fitder = df_fit.diff()

    # ................................................................
    # 2nd derivative
    df_fitder2 = df_fitder.diff()

    # identify type of extrema
    xshift = df_fitder.idxmin()[0]
    xturn = np.abs(df_fitder2.loc[xshift - 2:xshift + 2]).idxmin()[0]
    if xturn in [xshift-steps, xshift, xshift+steps]:
        pass
    else:
        print('Warning! Extreme point for core {}-sample {} might not be a real point of inflection'.format(core, nr))

    return res, df_fit, df_fitder, df_fitder2, xshift


def baseline_finder_DF(dic_dcore, steps, model, adv):
    # curve fit according to selected model
    xdata = dic_dcore.index
    c = 'O2_mV' if 'O2' in dic_dcore.columns else dic_dcore.columns[0]
    ydata = dic_dcore[c]

    # initial parameters
    if adv is True:
        para = model.make_params(a=-int(ydata.loc[xdata[:3]].mean()), b=.001, c=.001,
                                 d=-int(ydata.loc[xdata[-3:]].mean()))
    else:
        para = model.make_params(a=-int(ydata.loc[xdata[:3]].mean()), b=.001, c=.001)
    res = model.fit(ydata.to_numpy(), para, x=xdata)

    # ................................................................
    # 1st derivative
    arg = [res.params[p].value for p in res.params.keys()]
    xnew = np.linspace(xdata[0], xdata[-1], num=int((xdata[-1]-xdata[0])/steps+1))
    if adv is True:
        yfit = _gompertz_curve_adv(x=xnew, a=arg[0], b=arg[1], c=arg[2], d=arg[3])
    else:
        yfit = _gompertz_curve(x=xnew, a=arg[0], b=arg[1], c=arg[2])

    df_fit = pd.DataFrame(yfit, index=xnew)
    df_fitder = df_fit.diff()

    return res, df_fit, df_fitder


def baseline_shift(dic_dcore, dfit):
    data_shift = dict(map(lambda c:
                          (c, dict(map(lambda n:
                                       (n, pd.DataFrame(np.array(dic_dcore[c][n]),
                                                        index=dic_dcore[c][n].index - dfit[c][n][2],
                                                        columns=dic_dcore[c][n].columns)), dic_dcore[c].keys()))),
                          dic_dcore.keys()))
    return data_shift


def _calcO2penetration(dO2_core, O2_pen, unit, steps, gmod, adv):
    dcore_pen, dcore_fig = dict(), dict()
    for core in dO2_core.keys():
        dic_pen, dfig_pen = dict(), dict()
        for s in dO2_core[core].keys():
            df_fit = penetration_depth(df=dO2_core[core][s[0]].dropna(), unit=unit, steps=steps, model=gmod, adv=adv)
            dic_pen[str(s[0]) + '-Fit'] = df_fit
            [fig, depth_pen] = plot_penetrationDepth(core=core, s=s[0], df_fit=df_fit, O2_pen=O2_pen, unit=unit,
                                                     show=False)
            dic_pen[str(s[0]) + '-penetration'] = depth_pen
            dfig_pen[int(s[0])] = fig
        dcore_pen[core] = dic_pen
        dcore_fig[core] = dfig_pen

    # store all penetration depth information for all samples of the same core in a dictionary
    dpenetration = dict()
    for core in dcore_pen.keys():
        ls_pen = list()
        for i in dcore_pen[core].keys():
            if 'penetration' in i:
                ls_pen.append(i)
        dfpen_core = pd.DataFrame([dcore_pen[core][l] for l in ls_pen], columns=['Depth / µm', 'O2_' + unit],
                                  index=[int(i.split('-')[0]) for i in ls_pen])

        dfpen_core.loc['mean'] = dfpen_core.mean()
        dfpen_core.loc['std'] = dfpen_core.std()

        dpenetration[core] = dfpen_core
    dpen_all = pd.concat(dpenetration, axis=0)
    return dcore_pen, dcore_fig, dpen_all


def penetration_depth(df, unit, steps, model, adv):
    xdata = df.index
    ydata = df['O2_' + unit]

    # baseline correction
    ydata = ydata - ydata.loc[xdata[-3:]].mean()

    # initial parameters
    if adv is True:
        para = model.make_params(a=-int(ydata.loc[xdata[:3]].mean()), b=-.0001, c=0.002,
                                 d=-int(ydata.loc[xdata[-3:]].mean()))
    else:
        model = Model(_gompertz_curve)
        para = model.make_params(a=-int(ydata.loc[xdata[:3]].mean()), b=-.0001, c=0.002)
    res = model.fit(ydata.to_numpy(), para, x=xdata)

    # ................................................................
    # 1st derivative
    arg = [res.params[p].value for p in res.params.keys()]
    xnew = np.linspace(xdata[0], xdata[-1], num=int((xdata[-1]-xdata[0])/steps+1))
    if adv is True:
        yfit = _gompertz_curve_adv(x=xnew, a=arg[0], b=arg[1], c=arg[2], d=arg[3])
    else:
        yfit = _gompertz_curve(x=xnew, a=arg[0], b=arg[1], c=arg[2])

    df_fit = pd.DataFrame(yfit, index=xnew)

    return df_fit


def defO2calib(dtab_sal, unit, temp, sal):
    # determine maximal and minimal dissolved oxygen concentration depending on temperature and salinity
    for i in dtab_sal.keys():
        if unit in dtab_sal[i][2]:
            for c in dtab_sal[i][1].columns:
                if np.abs(temp - c) < 0.5:
                    temp_col = (i, c)

    # minimal and maximal dissolved oxygen; including unit
    o2_dis = (0, dtab_sal[temp_col[0]][1][temp_col[1]].loc[sal], unit)
    return o2_dis


def findPotentialLimits(df, lim, lim_min):
    # for all samples in selected core - find (absolute) minima/maxima potential
    ls_potMax, ls_potMin, pot_max, pot_min = list(), list(), list(), list()
    dpot = dict()
    for s in df.keys():
        # maximal O2 concentration - potential for selected core
        df[s] = pd.DataFrame(df[s]).astype(float)
        idxmax = df[s].idxmax()[0]
        if len(df[s].loc[idxmax - lim:idxmax + lim]) < 3:
            lim = 200
        pot_max = (df[s].loc[idxmax - lim:idxmax + lim].mean()[0],
                   df[s].loc[idxmax - lim:idxmax + lim].std()[0])

        # minimal O2 concentration - potential for selected core
        idxmin = df[s].idxmin()[0]
        if len(df[s].loc[idxmin - np.abs(lim_min):idxmin + np.abs(lim_min)]) < 3:
            lim_min = -50
        pot_min = (df[s].loc[idxmin - np.abs(lim_min):idxmin + np.abs(lim_min)].mean()[0],
                   df[s].loc[idxmin - np.abs(lim_min):idxmin + np.abs(lim_min)].std()[0])
        # update nan by 0 for minimal potential
        pot_min = [0 if x != x else x for x in pot_min]

        # combine all samples of selected core in dictionary
        pot_o2 = pd.DataFrame([pot_max, pot_min], columns=['mean', 'std'], index=['max', 'min'])
        dpot[s] = pot_o2

    # find averaged min/max potential of all samples in selected core
    # !!!TODO: better absolute max/min?
    pot_av = pd.concat([pd.DataFrame(pd.concat(dpot).T.filter(like='max').mean(axis=1)),
                        pd.DataFrame(pd.concat(dpot).T.filter(like='min').mean(axis=1))], axis=1)
    pot_av.columns = ['max', 'min']
    return pot_av


def O2converter4conc(data_shift, o2_dis, lim_min, lim, unit):
    # get the correct column
    dex = pd.concat(data_shift[list(data_shift.keys())[0]], axis=1)
    col = [c for c in dex.columns.levels[1] if 'M' not in c][0]

    dO2_core = dict()
    for core in data_shift.keys():
        # find minimal and maximal potential for all samples of the core
        pot_av = findPotentialLimits(df=data_shift[core], lim=lim, lim_min=lim_min)

        # linear calibration (2-point) for this core
        arg = stats.linregress(sorted(list(pot_av.loc['mean'].to_numpy())), sorted([o2_dis[1], o2_dis[0]]))

        do2_calib = dict(map(lambda s:
                             (s, pd.DataFrame(arg[0]*data_shift[core][s][col].to_numpy() + arg[1], columns=['O2_'+unit],
                                              index=data_shift[core][s].index)), data_shift[core].keys()))
        dO2_core[core] = pd.concat(do2_calib, axis=1)
    return dO2_core


def O2calc4conc_one4all(core_sel, data_shift, o2_dis, lim, lim_min, unit):
    # get the correct column
    dex = pd.concat(data_shift[list(data_shift.keys())[0]], axis=1)
    col = [c for c in dex.columns.levels[1] if 'M' not in c][0]

    # find minimal/maximal potential for samples of selected core
    pot_av = findPotentialLimits(df=data_shift[core_sel], lim=lim, lim_min=lim_min)

    # linear calibration (2-point) for this core
    arg = stats.linregress(sorted(list(pot_av.loc['mean'].to_numpy())), sorted([o2_dis[1], o2_dis[0]]))

    # apply now the calibration to all samples of all cores
    do2_core = dict(map(lambda c:
                        (c, pd.concat(dict(map(lambda s:
                                               (s, pd.DataFrame(arg[0] * data_shift[c][s][col].to_numpy() + arg[1],
                                                                columns=['O2_' + unit], index=data_shift[c][s].index)),
                                               data_shift[c].keys())), axis=1)), data_shift.keys()))
    return do2_core


def O2rearrange(df, unit='µmol/L'):
    # pre-filter columns to get the desired ones
    dex = pd.concat(df[list(df.keys())[0]], axis=1)
    if 'µ' in unit:
        col = [c for c in dex.columns.levels[1] if 'M' in c or 'mol' in c][0]
    else:
        col = [c for c in dex.columns.levels[1] if 'M' not in c or 'mol' in c][0]

    dO2_core = dict()
    for core in df.keys():
        d = pd.concat(df[core], axis=1).filter(like=col)
        d.columns.set_levels(['O2_' + unit] * len(d.columns.levels[1]), level=1, inplace=True, verify_integrity=False)
        dO2_core[core] = d
    return dO2_core


# --------------------------------------------------------------------------------------------------------------------
# main functions for individual projects
def sheetname_check(dsheets, para='O2'):
    ls, sheet_select = list(), None
    # define list for individual parameter
    if para == 'O2':
        [ls.append(i) for i in list(dsheets.keys()) if 'O2' in i or 'o2' in i]
    elif para == 'pH':
        [ls.append(i) for i in list(dsheets.keys()) if 'pH' in i]
    elif para == 'H2S':
        [ls.append(i) for i in list(dsheets.keys()) if 'H2S' in i or 'h2s' in i]
    elif para == 'EP':
        [ls.append(i) for i in list(dsheets.keys()) if 'EP' in i or 'ep' in i or 'Ep' in i]

    for l in ls:
        if 'all' in l:
            sheet_select = l
        elif len(ls) == 1:
            sheet_select = ls[0]
        else:
            sheet_select = ls[0]
    return sheet_select


def dissolved_o2(file):
    # when using the presense gas table, use the following pages:
    ls_sal = list([3, 4, 5, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19])

    # read pages from pdf
    read_pdf = PyPDF2.PdfFileReader(file)

    # extract the salinity pages
    dtab_sal = dict(map(lambda p: (p, calO2.read_fullpage(file=file, read_pdf=read_pdf, p=p)[1]), ls_sal))
    return dtab_sal


def dissolvedO2_calc(T, salinity):
    # specific constants for taylor series expansion for O2
    # resource: Weiss R.F. 1970. The solubility of nitrogen, oxygen and argon in water and seawater.
    #           Deep Sea Research 17:721-735
    pdO2 = dict({'A1': -173.4292, 'A2': 249.6339, 'A3': 143.3483, 'A4': -21.8492, 'B1': -0.033096, 'B2': 0.014259,
                 'B3': -0.0017000, 'STP': 22.4139, 'R': 0.0821, 'T_K': 286.35})

    # conversion factors
    tempK = T + 273.15
    convF = 100 / tempK
    # taylor series expansion (Taylor) with specific constants for O2
    taylor = np.exp(pdO2['A1'] + pdO2['A2'] * convF + pdO2['A3'] * np.log(1 / convF) + pdO2['A4'] * (1 / convF) +
                    salinity * (pdO2['B1'] + pdO2['B2'] * (1 / convF) + pdO2['B3'] * (1 / convF) ** 2))

    # maximal dissolved O2 in µmol/L for a given temperature and salinity
    dO2_max = taylor / (pdO2['R'] * 273.15) * 1000  # µM
    return (0, dO2_max)


def O2_depthProfile(file, file_calib, temp_degC, adv, salinity=0, O2_pen=5, unit='µmol/L', lim_min=120, lim=-5,
                    steps=0.5, plot_inter=False):
    """

    :param file:
    :param temp_degC:
    :param salinity:
    :param O2_pen:
    :param unit:
    :param lim:
    :param steps:
    :param plot_inter:
    :return:
    """

    # load excel sheet with all measurements
    dsheets = pd.read_excel(file, sheet_name=None)
    # pre-check whether O2_all in sheet names
    sheet_select = sheetname_check(dsheets)

    # pre-set of parameters
    if adv is True:
        gmod = Model(_gompertz_curve_adv)  # define model for curve fit
    else:
        gmod = Model(_gompertz_curve)  # define model for curve fit
    dO2_core, dfilter, dhiden_object, dpen_all, dfig_pen, dfig = dict(), dict(), dict(), dict(), dict(), dict()

    # ----------------------------------------------------------------------------------
    # list all available cores for O2 sheet
    ls_core = list(dict.fromkeys(dsheets[sheet_select].set_index('Nr')['Core'].to_numpy()))

    # import all measurements for given parameter
    dic_dcore, ls_nr, ls_name = load_measurements(dsheets=dsheets, ls_core=ls_core, para='O2_all')

    # curve fit and baseline finder
    dfit, dic_deriv = fit_baseline(ls_core=ls_core, ls_nr=ls_nr, dic_dcore=dic_dcore, steps=steps, gmod=gmod, adv=adv)

    # baseline shift
    data_shift = baseline_shift(dic_dcore=dic_dcore, dfit=dfit)

    # plotting interim results
    dfig = plot_interimsteps(dfit=dfit, dic_dcore=dic_dcore, dic_deriv=dic_deriv, ls_core=ls_core,
                             data_shift=data_shift, plot_interim=plot_inter)

    # -----------------------------------------------------------------------------------
    # calibration according to oxygen_solubility
    dtab_sal = dissolved_o2(file_calib)

    # minimal and maximal dissolved oxygen; including unit
    o2_dis = defO2calib(dtab_sal=dtab_sal, unit=unit, temp=temp_degC, sal=salinity)

    # convert O2 potential into concentration
    dO2_core = O2converter4conc(data_shift, o2_dis, lim_min, lim, unit)

    # -----------------------------------------------------------------------------------
    # penetration depth
    # determine penetration depth - store individual samples in plot but don't show them (yet)
    dcore_pen, dcore_fig, dpen_all = _calcO2penetration(dO2_core=dO2_core, O2_pen=O2_pen, unit=unit, steps=steps,
                                                        gmod=gmod, adv=adv)

    # one figure for all samples of the same core - de-check the curves you don't want to add to the averaging process
    # in legend
    dax = dict()
    for core in dcore_pen.keys():
        fig, ax = plot_joint_penetration(core=core, dcore_pen=dcore_pen, dO2_core=dO2_core, unit=unit, show=True,
                                         dobj_hid=dhiden_object)
        dfig[core], dax[core] = fig, ax

    for core in dcore_pen.keys():
        fig1, ax1, dpen_all = plot_indicate_penetration(dcore_pen=dcore_pen, dO2_core=dO2_core, core=core, ax=dax[core],
                                                        dhiden_object=dhiden_object, unit=unit, dpen_all=dpen_all,
                                                        fig=dfig[core])
        dfig_pen[core] = fig1

    # -----------------------------------------------------------------------------------
    # collect for output and storage
    for core in dcore_pen.keys():
        ls_filter = list()
        [ls_filter.append(i) for i in dcore_pen[core].keys() if 'Fit' in i]
        dfFit = pd.concat([dcore_pen[core][i] for i in ls_filter], axis=1)
        dfFit.columns = ls_filter
        dfilter[core] = dfFit

    # ---------------------------------
    # dictionary to be saved as output
    # in each case, whenever during the project - save the stage in which it has been stored
    # for non-existing data - use None
    # delete previous step (output) in case the next step has been reached successfully
    do2_res = {'O2 baseline corr': dO2_core, 'Fits': dfilter, 'excluded for core penetration depth': dhiden_object,
               'penetration depth': dpen_all, 'figures penetration depth': dfig_pen}

    return do2_res


def _getProfileStack(nP, dataEP, dorder):
    # drift correction for individual package
    dfP_ = [dataEP[p[0]][p[1]].sort_index(ascending=True) for p in dorder[nP]]
    dfP = pd.concat(dfP_, axis=0)
    return dfP_, dfP


def curveFitPack(dfP_, numP, nP, dorder, resultsEP, fit_select='2nd order polynomial fit'):
    # curve fit
    ydata = [dfP_[n].loc[dfP_[n].index[:numP]].mean()['EP_mV'] for n in range(len(dfP_))]
    xdata = np.arange(len(ydata))
    xnew = np.linspace(0, xdata[-1], num=int(xdata[-1] / 0.2 + 1))
    if len(ydata) > 2 and fit_select == '2nd order polynomial fit':
        arg = np.polyfit(x=xdata, y=ydata, deg=2)
        c, t = arg[2], arg[-1]
        df_reg = pd.DataFrame(arg[0] * (xnew ** 2) + arg[1] * xnew + arg[2], index=xnew, columns=['EP_reg'])
    elif len(ydata) <= 2 or fit_select == 'linear regression':
        arg = stats.linregress(x=xdata, y=ydata)
        c, t = arg[1], arg[1]
        df_reg = pd.DataFrame(arg[0] * xnew + arg[1], index=xnew, columns=['EP_reg'])
    else:
        arg, c, t = [np.nan], 0, 0
        df_reg = pd.DataFrame([np.nan] * xnew, index=xnew, columns=['EP_reg'])

    # determine goodness of fit
    chi_squared = np.sum((np.polyval(arg, xdata) - ydata) ** 2)

    # actual correction of all profiles part of the package | target value - actual value
    corr_f = [c - ydata[n] - t for n in range(len(xdata))]
    for en, r in enumerate(dorder[nP]):
        c, s = r
        for col_ in dfP_[en].columns:
            if 'mV' not in col_:
                col = col_
        resultsEP[c][s] = pd.concat([dfP_[en][col], dfP_[en]['EP_mV'] + corr_f[en]], axis=1)

    return ydata, df_reg, chi_squared, arg, corr_f
