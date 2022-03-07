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

    ax.plot(dic_dcore[core][nr].index, dic_dcore[core][nr]['O2_mV'], lw=0, marker='o', ms=4, color='k')
    ax.plot(dfit[core][nr][1], lw=0.75, ls=':', color='k')

    ax1.plot(dic_deriv[core][nr], lw=1., color='#0077b6')
    ax1.axvline(dic_deriv[core][nr].idxmin().values[0], ls='-.', color='darkorange', lw=1.5)
    text = 'surface level \nat {:.1f}µm'
    ax.text(dic_deriv[core][nr].idxmin().values[0]*2, dic_dcore[core][nr]['O2_mV'].max()*1.15,
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


def GUI_baslineShift(data_shift, core, ls_core, fig=None, ax=None, show=True):
    plt.ioff()

    # identify closest value in list
    if core == 0 or not ls_core:
        core_select = 0
    else:
        core_select = min(ls_core, key=lambda x: abs(x - core))

    # plot figure
    if ax is None:
        fig, ax = plt.subplots(figsize=(3, 4))
    else:
        ax.cla()

    if core_select == 0 or not data_shift:
        pass
    else:
        ax.title.set_text('Sediment water interface profile (SWI) for core {}'.format(core_select))
    ax.set_xlabel('O2 / mV'), ax.set_ylabel('Depth / µm')
    ax.invert_yaxis()

    if core_select != 0:
        ax.axhline(0, lw=.5, color='k')
    if core_select == 0:
        pass
    else:
        for en, nr in enumerate(data_shift[core_select].keys()):
            ax.plot(data_shift[core_select][nr][0].to_numpy(), data_shift[core_select][nr].index, lw=0.75, ls='-.',
                    marker='.', color=ls_col[en], alpha=0.75, label='sample ' + str(nr))
        ax.legend(frameon=True, fontsize=10)

        max_ = max([data_shift[core_select][s].max()[0] for s in data_shift[core_select].keys()])
        minPot = min(data_shift[core_select][nr][0].to_numpy())
        if int(minPot) > 0:
            min_ = min(data_shift[core_select][nr][0].to_numpy())*0.5
        else:
            min_ = -1 * max_ * 0.1
        ax.set_xlim(min_, max_*1.05)

    if show is False:
        plt.close(fig)
    else:
        fig.canvas.draw()
    return fig


def GUI_baslineShiftCore(data_shift, core_select, fig, ax):
    ax.cla()

    # plot figure
    if ax is None:
        fig, ax = plt.subplots(figsize=(3, 4))
    ax.title.set_text('Sediment water interface profile (SWI) for core {}'.format(core_select))
    ax.set_xlabel('O2 / mV'), ax.set_ylabel('Depth / µm')
    ax.invert_yaxis()

    # draw the surface
    ax.axhline(0, lw=.5, color='k')

    # plot the depth corrected profiles for the selected core
    for en, nr in enumerate(data_shift.keys()):
        # draw the recorded points of the sample
        ax.plot(data_shift[nr][0].to_numpy(), data_shift[nr].index, lw=0.5, ls='dotted', marker='.', color=ls_col[en],
                alpha=0.75, label='sample ' + str(nr))
        ax.legend(frameon=True, fontsize=10)

        max_ = max([data_shift[s].max()[0] for s in data_shift.keys()])
        minPot = min(data_shift[nr][0].to_numpy())
        if int(minPot) > 0:
            min_ = min(data_shift[nr][0].to_numpy())*0.5
        else:
            min_ = -1 * max_ * 0.1
        ax.set_xlim(min_, max_*1.05)

    fig.canvas.draw()
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


# --------------------------------------------------------------------------------------------------------------------
def load_measurements(dsheets, ls_core, para):
    dic_dcore, dls_nr = dict(), dict()
    for core in ls_core:
        nr = dsheets[dsheets['Core'] == core].index.to_numpy()

        ls_nr = list(dict.fromkeys(nr))
        dls_nr[core] = ls_nr
        # prepare table (index = depth)
        dcore = dict()
        for n in ls_nr:
            # identify the depth column
            col_ = [c for c in dsheets.loc[n].columns if 'Depth' in c]
            ls_name = ['Core']
            if 'O2' in para or 'o2' in para:
                [ls_name.append(i) for i in dsheets.loc[n].columns if 'O2' in i and 'M' in i]
                [ls_name.append(i) for i in dsheets.loc[n].columns if 'O2' in i and '_mV' in i]
                df = dsheets.loc[n].set_index(col_[0])[ls_name].dropna()
                dcore[n] = df[df['Core'] == core]
            elif 'H2S' in para or 'h2s' in para:
                [ls_name.append(i) for i in dsheets.loc[n].columns if 'H2S' in i and 'M' in i]
                df = dsheets.loc[n].set_index(col_[0])[ls_name].dropna()
                dcore[n] = df[df['Core'] == core]
            elif 'EP' in para or 'Ep' in para or 'ep' in para:
                [ls_name.append(i) for i in dsheets.loc[n].columns if 'EP' in i and '_mV' in i]
                df = dsheets.loc[n].set_index(col_[0])[ls_name].dropna()
                dcore[n] = df[df['Core'] == core]
            else:
                df = dsheets.loc[n].dropna().set_index(col_[0])
                dcore[n] = df[df['Core'] == core]
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
    if 'Metadata' not in df_excel.keys():
        if 'metadata' not in df_excel.keys():
            #!!!TODO: have it as a try function - in case open an additional window
            print('WARNING - metadata required')
    df_meta = df_excel['Metadata'].set_index(['deployment', 'code'])
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


def prep4saveRes(dout, results, typeCalib=None, o2_dis=None, temperature=None, salinity=None, pene2=None):
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

            # derivative
            dcore_der[c] = pd.concat(results['O2 derivative'][c], axis=1)
        dout['fit_mV'] = pd.concat(dcore_fit, axis=1)
        dout['derivative_mV'] = pd.concat(dcore_der, axis=1)

    # handle SWI corrected - results['SWI corrected']
    if 'O2 SWI corrected' in results.keys():
        dcore_swi = dict()
        # only potential data 'O2_mV'
        ddata = results['O2 SWI corrected']['O2_mV']
        for c in ddata.keys():
            # t either µmol/l or mV
            df = pd.concat([ddata[c][s] for s in ddata[c].keys()], axis=1)
            df.columns = ddata[c].keys()
            dcore_swi[c] = df
        dout['SWIcorrected mV'] = pd.concat(dcore_swi, axis=1)

    # handle o2 profiles - results['O2 profile']
    if 'O2 profile' in results.keys():
        dout['O2 profile'] = pd.concat(results['O2 profile'], axis=1)

    # handle penetration depth - results['penetration depth']
    if 'penetration depth' in results.keys():
        ddata = results['O2 penetration depth']
        dpen = dict()
        for c in ddata.keys():
            ls_rel = list()
            [ls_rel.append(k) for k in list(ddata[c].keys()) if 'penetration' in k]
            df = pd.DataFrame([ddata[c][k] for k in ls_rel], index=[int(i.split('-')[0]) for i in ls_rel],
                              columns=['mean', 'std'])

            # add mark for excluded objects
            df.loc[:, 'outlier'] = [None] * len(df.index)
            if c in results['O2 hidden objects'].keys():
                for s in results['O2 hidden objects'][c]:
                    df.loc[int(s.split('-')[-1]), 'outlier'] = 'X'

            # add average penetration depth for core
            df.loc['average', :] = df[df['outlier'] != 'X'].mean().values

            # add all samples of the core to the penetration dictionary and the general output dictionary
            dpen[c] = df
        dout['penetration depth'] = pd.concat(dpen, axis=0)

    # meta data
    if typeCalib:
        if 'recalibration' in typeCalib:
            dmeta = pd.DataFrame([typeCalib, o2_dis, temperature, salinity, pene2], columns=[''],
                                 index=['', 'dissolved O2', 'temp degC', 'salinity', 'sensor LoD'])
        else:
            dmeta = pd.DataFrame([typeCalib], index=[''], columns=[''])
        dout['meta data'] = dmeta
    return dout


def save_rawExcel(dout, file, savePath):
    savename = savePath + "/output_" + file.split('/')[-1]

    # check whether file exist already in folder
    ls_folder = next(walk(savePath), (None, None, []))[2]  # [] if no file

    ls_files = list()
    if savename.split('/')[-1] in ls_folder:
        # return all files with similar pattern
        for f in ls_folder:
            if savename.split('/')[-1].split('_')[0] in f:
                ls_files.append(f)

    if ls_files:
        for f in ls_folder:
            if '-' in f.split('_')[0]:
                addstr = f.split('run')[0] + 'run' + str(int(f.split('-run')[1].split('_')[0]) + 1) + '_'
            else:
                # first run - now add "run1"
                addstr = f.split('_')[0] + '-run1_'
        savename = savePath + '/' + addstr + file.split('/')[-1]

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


def fit_baseline(ls_core, ls_nr, dic_dcore, steps, gmod):
    dfit, dic_deriv = dict(), dict()
    for core in ls_core:
        dfit_, dic_deriv_ = dict(), dict()
        for nr in ls_nr[core]:
            res, df_fit, df_fitder = baseline_finder(dic_dcore=dic_dcore, core=core, nr=nr, steps=steps, model=gmod)
            dfit_[nr], dic_deriv_[nr] = (res, df_fit), df_fitder
        dfit[core] = dfit_
        dic_deriv[core] = dic_deriv_
    return dfit, dic_deriv


def baseline_finder(dic_dcore, core, nr, steps, model):
    # curve fit according to selected model
    xdata = dic_dcore[core][nr].index
    ydata = dic_dcore[core][nr]['O2_mV']

    # initial parameters
    para = model.make_params(a=-int(ydata.loc[xdata[:3]].mean()), b=.001, c=.001)
    res = model.fit(ydata.to_numpy(), para, x=xdata)

    # ................................................................
    # 1st derivative
    arg = [res.params[p].value for p in res.params.keys()]
    xnew = np.linspace(xdata[0], xdata[-1], num=int((xdata[-1]-xdata[0])/steps+1))
    yfit = _gompertz_curve(x=xnew, a=arg[0], b=arg[1], c=arg[2])

    df_fit = pd.DataFrame(yfit, index=xnew)
    df_fitder = df_fit.diff()

    return res, df_fit, df_fitder


def baseline_finder_DF(dic_dcore, steps, model):
    # curve fit according to selected model
    xdata = dic_dcore.index
    ydata = dic_dcore['O2_mV']

    # initial parameters
    para = model.make_params(a=-int(ydata.loc[xdata[:3]].mean()), b=.001, c=.001)
    res = model.fit(ydata.to_numpy(), para, x=xdata)

    # ................................................................
    # 1st derivative
    arg = [res.params[p].value for p in res.params.keys()]
    xnew = np.linspace(xdata[0], xdata[-1], num=int((xdata[-1]-xdata[0])/steps+1))
    yfit = _gompertz_curve(x=xnew, a=arg[0], b=arg[1], c=arg[2])

    df_fit = pd.DataFrame(yfit, index=xnew)
    df_fitder = df_fit.diff()

    return res, df_fit, df_fitder


def baseline_shift(dic_dcore, dic_deriv, column='O2_mV'):
    data_shift = dict(map(lambda core:
                          (core, dict(map(lambda nr: (nr, pd.DataFrame(dic_dcore[core][nr][column].values,
                                                                       dic_dcore[core][nr].index -
                                                                       dic_deriv[core][nr].idxmin().values[0])),
                                          dic_dcore[core].keys()))), dic_dcore.keys()))
    return data_shift


def _calcO2penetration(dO2_core, O2_pen, unit, steps, gmod):
    dcore_pen, dcore_fig = dict(), dict()
    for core in dO2_core.keys():
        dic_pen, dfig_pen = dict(), dict()
        for s in dO2_core[core].keys():
            df_fit = penetration_depth(df=dO2_core[core][s[0]].dropna(), O2_pen=O2_pen, unit=unit, steps=steps,
                                       model=gmod)
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


def penetration_depth(df, unit, O2_pen, steps, model):
    xdata = df.index
    ydata = df['O2_' + unit]

    # initial parameters
    para = model.make_params(a=-int(ydata.loc[xdata[:3]].mean()), b=-.0001, c=0.002)
    res = model.fit(ydata, para, x=xdata)

    # ................................................................
    # 1st derivative
    arg = [res.params[p].value for p in res.params.keys()]
    xnew = np.linspace(xdata[0], xdata[-1], num=int((xdata[-1]-xdata[0])/steps+1))
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


def O2converter4conc(data_shift, o2_dis, lim, lim_min, unit):
    dO2_core = dict()
    for core in data_shift.keys():
        # find minimal and maximal potential for each sample of the core
        # dpot = dict()
        # for s in data_shift[core].keys():
        #     # maximal O2 concentration - potential
        #     idxmax = data_shift[core][s].idxmax()[0]
        #     if len(data_shift[core][s].loc[idxmax-lim:idxmax+lim]) < 3:
        #         print('WARNING - less than 3 points to average maximal potential')
        #         lim = 200
        #     pot_max = (data_shift[core][s].loc[idxmax-lim:idxmax+lim].mean()[0],
        #                data_shift[core][s].loc[idxmax-lim:idxmax+lim].std()[0])
        #
        #     # minimal O2 concentration - potential
        #     idxmin = data_shift[core][s].idxmin()[0]
        #     if len(data_shift[core][s].loc[idxmin-lim:idxmin+lim]) < 3:
        #         print('WARNING - less than 3 points to average minimal potential')
        #         lim = 200
        #     pot_min = (data_shift[core][s].loc[idxmin-lim:idxmin+lim].mean()[0],
        #                data_shift[core][s].loc[idxmin-lim:idxmin+lim].std()[0])
        #
        #     pot_o2 = pd.DataFrame([pot_max, pot_min], columns=['mean', 'std'], index=['max', 'min'])
        #     dpot[s] = pot_o2
        #
        # # min/max potential averaged
        # pot_av = pd.concat([pd.DataFrame(pd.concat(dpot).T.filter(like='max').mean(axis=1)),
        #                     pd.DataFrame(pd.concat(dpot).T.filter(like='min').mean(axis=1))], axis=1)
        # pot_av.columns = ['max', 'min']

        pot_av = findPotentialLimits(df=data_shift[core], lim=lim, lim_min=lim_min)

        # linear calibration (2-point) for this core
        arg = stats.linregress(sorted(list(pot_av.loc['mean'].to_numpy())), sorted([o2_dis[1], o2_dis[0]]))

        do2_calib = dict(map(lambda s:
                             (s, pd.DataFrame(arg[0]*data_shift[core][s][0].to_numpy() + arg[1], columns=['O2_'+unit],
                                              index=data_shift[core][s].index)), data_shift[core].keys()))
        dO2_core[core] = pd.concat(do2_calib, axis=1)
    return dO2_core


def O2calc4conc_one4all(core_sel, data_shift, o2_dis, lim, lim_min, unit):
    # find minimal/maximal potential for samples of selected core
    pot_av = findPotentialLimits(df=data_shift[core_sel], lim=lim, lim_min=lim_min)

    # linear calibration (2-point) for this core
    arg = stats.linregress(sorted(list(pot_av.loc['mean'].to_numpy())), sorted([o2_dis[1], o2_dis[0]]))

    # apply now the calibration to all samples of all cores
    do2_core = dict(map(lambda c:
                        (c, pd.concat(dict(map(lambda s:
                                               (s, pd.DataFrame(arg[0] * data_shift[c][s][0].to_numpy() + arg[1],
                                                                columns=['O2_' + unit], index=data_shift[c][s].index)),
                                               data_shift[c].keys())), axis=1)), data_shift.keys()))
    return do2_core


def O2rearrange(df, unit='µmol/l'):
    dO2_core = dict()
    for core in df.keys():
        d = pd.concat(df[core], axis=1)
        d.columns.set_levels(['O2_' + unit]*len(d.columns.levels[1]), level=1, inplace=True)
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
        [ls.append(i) for i in list(dsheets.keys()) if 'H2S' in i]
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

    # maximal dissolved O2 in µmol/l for a given temperature and salinity
    dO2_max = taylor / (pdO2['R'] * 273.15) * 1000  # µM
    return (0, dO2_max)


def O2_depthProfile(file, file_calib, temp_degC, salinity=0, O2_pen=5, unit='µmol/l', lim=150, steps=0.5,
                    plot_inter=False):
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
    gmod = Model(_gompertz_curve)  # define model for curve fit
    dO2_core, dfilter, dhiden_object, dpen_all, dfig_pen, dfig = dict(), dict(), dict(), dict(), dict(), dict()

    # ----------------------------------------------------------------------------------
    # list all available cores for O2 sheet
    ls_core = list(dict.fromkeys(dsheets[sheet_select].set_index('Nr')['Core'].to_numpy()))

    # import all measurements for given parameter
    dic_dcore, ls_nr = load_measurements(dsheets=dsheets, ls_core=ls_core, para='O2_all')

    # curve fit and baseline finder
    dfit, dic_deriv = fit_baseline(ls_core=ls_core, ls_nr=ls_nr, dic_dcore=dic_dcore, steps=steps, gmod=gmod)

    # baseline shift
    data_shift = baseline_shift(dic_dcore=dic_dcore, dic_deriv=dic_deriv)

    # plotting interim results
    dfig = plot_interimsteps(dfit=dfit, dic_dcore=dic_dcore, dic_deriv=dic_deriv, ls_core=ls_core,
                             data_shift=data_shift, plot_interim=plot_inter)

    # -----------------------------------------------------------------------------------
    # calibration according to oxygen_solubility
    dtab_sal = dissolved_o2(file_calib)

    # minimal and maximal dissolved oxygen; including unit
    o2_dis = defO2calib(dtab_sal=dtab_sal, unit=unit, temp=temp_degC, sal=salinity)

    # convert O2 potential into concentration
    dO2_core = O2converter4conc(data_shift, o2_dis, lim, unit)

    # -----------------------------------------------------------------------------------
    # penetration depth
    # determine penetration depth - store individual samples in plot but don't show them (yet)
    dcore_pen, dcore_fig, dpen_all = _calcO2penetration(dO2_core=dO2_core, O2_pen=O2_pen, unit=unit, steps=steps,
                                                        gmod=gmod)

    # one figure for all samples of the same core - de-check the curves you don't want to add to the averaging process
    # in legend
    dax = dict()
    for core in dcore_pen.keys():
        fig, ax = plot_joint_penetration(core=core, dcore_pen=dcore_pen, dO2_core=dO2_core, unit=unit, show=True,
                                         dobj_hid=dhiden_object)
        dfig[core], dax[core] = fig, ax

    for core in dcore_pen.keys():
        fig1, ax1 = plot_indicate_penetration(core=core, dhiden_object=dhiden_object, unit=unit, dpen_all=dpen_all,
                                              dcore_pen=dcore_pen, dO2_core=dO2_core, ax=dax[core], fig=dfig[core])
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


