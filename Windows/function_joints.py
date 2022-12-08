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

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import os

import functions_dbs as dbs


# --------------------------------------------------------------------------------------------------------------------
def _getProfileLabels(para, results):
    ls_par = list()
    [ls_par.append(k) for k in results.keys() if para in k]

    # get information on group / profile-ID
    dcore = None
    if ls_par and para == 'O2':
        dcore = dict()
        for c in results[ls_par[0]].keys():
            ls = list()
            [ls.append(i[0]) if isinstance(i, tuple) else ls.append(i) for i in results[ls_par[0]][c].keys()]
            dcore[dbs.intLab(c)] = ls
    elif ls_par and para != 'O2':
        dcore = dict(map(lambda c: (dbs.intLab(c), list(results[ls_par[0]][c].keys())), results[ls_par[0]].keys()))
    return dcore


def _getParaGroups(para_select, ls_jPlot, data, dav, dunit):
    if para_select == 'combo':
        dunit, dav = load_avProfiles(data)
    lsGrp1, lsGrp2, lsGrp3, lsGrp4 = None, None, None, None
    for p in ls_jPlot:
        for l in enumerate(list(dav.keys())):
            if p in l[1]:
                lsGrp = list(dav[l[1]].keys())
                if p == 'O2':
                    lsGrp1 = lsGrp
                elif p == 'pH':
                    lsGrp2 = lsGrp
                elif p == 'H2S':
                    lsGrp3 = lsGrp
                elif p == 'EP':
                    lsGrp4 = lsGrp
    return lsGrp1, lsGrp2, lsGrp3, lsGrp4, dunit, dav


def find_para_position(en, para, ls_jPlot):
    if len(ls_jPlot) == 4:
        # bottom axes: O2 (axis0) and H2S (axis2) | top axes: pH (axis1) and EP (axis3)
        pos = [em[0] for em in enumerate(['O2', 'pH', 'H2S', 'EP']) if em[1] == para][0]
    elif len(ls_jPlot) == 3:
        if ls_jPlot == sorted(['O2', 'pH', 'H2S']) or ls_jPlot == sorted(['O2', 'pH', 'EP']):
            # order · bottom: O2 and H2S, top: pH
            if para == 'O2':
                pos = 0
            elif para == 'pH':
                pos = 1
            else:
                pos = 2
        elif ls_jPlot == sorted(['O2', 'H2S', 'EP']):
            # order · bottom: O2 and H2S, top: EP
            if para == 'O2':
                pos = 0
            elif para == 'EP':
                pos = 1
            else:
                pos = 2
        else:
            # order · bottom: H2S and EP, top: pH
            if para == 'H2S':
                pos = 0
            elif para == 'pH':
                pos = 1
            else:
                pos = 2
    elif len(ls_jPlot) == 2:
        pos = en
    else:
        pos = 0
    return pos


def _specifyFilter(analyte):
    if 'O2' in analyte:
        filter_ = 'Concentration (µmol/l)'
    elif 'pH' in analyte:
        filter_ = 'pH'
    elif 'H2S' in analyte:
        filter_ = 'H2S_µM'
    elif 'EP' in analyte:
        filter_ = 'EP_mV'
    else:
        filter_ = None
    return filter_


def averageRemains(analyte, col, k, dav_par, dav_):
    # interpolate before averaging
    if len(dav_.keys()) > 1:
        df = pd.concat([dav_[i] for i in dav_.keys()], axis=1).astype(float)
        if _specifyFilter(analyte=analyte) in df.keys():
            df_ = df[_specifyFilter(analyte=analyte)].sort_index().interpolate()
            df_ = pd.concat([df_.mean(axis=1, skipna=True).dropna(), df_.std(axis=1, skipna=True).dropna()], axis=1)
        else:
            if 'O2' in analyte:
                df_ = pd.concat([df.sort_index().interpolate().mean(axis=1, skipna=True).dropna(),
                                 df.sort_index().interpolate().std(axis=1, skipna=True).dropna()], axis=1)
            elif 'H2S' in analyte:
                filter_ = 'total sulfide zero corr_µmol/L'
                df_ = pd.concat([df[filter_].sort_index().interpolate().mean(axis=1, skipna=True).dropna(),
                                 df[filter_].sort_index().interpolate().std(axis=1, skipna=True).dropna()], axis=1)
            else:
                df_ = None
    else:
        df_ = pd.concat([pd.DataFrame(dav_[col]['pH'].sort_index().dropna()) if col else pd.DataFrame(dav_.dropna()),
                         pd.DataFrame(dav_[col]['pH'].sort_index().dropna()) if col else pd.DataFrame(dav_.dropna())],
                        axis=1)
    if isinstance(df_, pd.DataFrame):
        df_.columns = ['mean', 'std']
        dav_par[k] = df_
    return dav_par


def _getAverageProfile(searchK, ls_pop, results):
    dav_par, col = dict(), None
    for k in results[searchK].keys():
        dav_par_ = dict()
        for p in results[searchK][k].keys():
            if isinstance(p, tuple):
                if p[0] not in ls_pop:
                    dav_par_[p[0]] = results[searchK][k][p[0]]
            else:
                if p not in ls_pop:
                    dav_par_[p] = results[searchK][k][p]
        # average the remaining profiles
        dav_par = averageRemains(analyte=searchK, col= list(dav_par_.keys())[0], k=k, dav_par=dav_par, dav_=dav_par_)
    return dav_par


def exeAverageProfileTab(tab, searchK1, searchK2, results):
    # get information which profiles to remove
    ls_pop = list()
    for c in range(tab.rowCount()):
        if isinstance(tab.item(c, 2), type(None)):
            pass
        else:
            if tab.item(c, 2).text() in ['N', 'n', '']:
                ls_pop.append(int(tab.item(c, 1).text()))

    # average remaining profiles (adjusted if in list else raw)
    if searchK1 in list(results.keys()):
        dav_par = _getAverageProfile(searchK=searchK1, ls_pop=ls_pop, results=results)
    else:
        if searchK2 in list(results.keys()):
            dav_par = _getAverageProfile(searchK=searchK2, ls_pop=ls_pop, results=results)
        else:
            dav_par = None
    return dav_par


# --------------------------------------------------------------------------------------------------------------------
def load_avProfiles(data):
    # get the file information and load the excel file
    ls_files = data[1:-1].split(',')[0][1:-1]
    ddf = pd.read_excel(ls_files, sheet_name=None)

    # re-arrange excel sheets/dictionary to the dic form we have from when the user would go through each project
    dav = dict(map(lambda k: (k.split('-')[0].strip(), dbs.load_av_profile(ddata=ddf[k])), ddf.keys()))

    # update unit dictionary
    dunit = dict()
    for i in ddf.keys():
        if len(i.split(' ')) > 1:
            dunit[i.split(' ')[0].strip()] = i.split(' ')[2].strip()
        else:
            dunit[i.split(' ')[0].strip()] = ''
    return dunit, dav


def save_avProfiles(save_path, data, dav, dunit):
    # make a project folder for the specific analyte if it doesn't exist
    if not os.path.exists(save_path):
        os.makedirs(save_path)

    # make for each analyte a separate sheet
    dout_av = dict()
    for c in dav.keys():
        if dav[c]:
            unit = dunit[c][1:].split('/')[0] + dunit[c][1:].split('/')[1] if '/' in dunit[c] else dunit[c]
            if c == 'pH':
                name = c
            elif 'µ' in unit:
                name = c + ' - ' + '\u03BC' + unit[1:]
            else:
                name = c + ' - ' + unit
            dout_av[name] = pd.concat(dav[c], axis=1)

    savename = dbs._actualFileName(savePath=save_path, file=data)
    savename = savename.split('.')[0] + '_avProfiles.xlsx'

    # actually saving DataFrame to excel
    writer = pd.ExcelWriter(savename, options={'encoding':'utf-8'})
    for key in dout_av.keys():
        dout_av[key].to_excel(writer, sheet_name=key, engine='xlsxwriter')
    writer.save()
    writer.close()


# --------------------------------------------------------------------------------------------------------------------
def _plot_joProfile4save(sval, ls_jPlot, tabcorr, dav, fs_, dcolor, dunit, show=False):
    plt.ioff()
    fig, ax = plt.subplots(linewidth=0)
    ax2 = ax.twiny()
    ax.set_ylabel('Depth / µm')

    # layout depending on the amount and type of parameters to plot in a joint graph
    ls_axes = fig.axes

    if len(ls_jPlot) == 1:
        dbs.axisLabel_op1(ls_axes=ls_axes, ls_para=ls_jPlot, dunit=dunit, axJ=ax, fs_=fs_, dcolor=dcolor)
    elif len(ls_jPlot) == 2:
        dbs.axisLabel_op2(ls_axes=ls_axes, ls_para=ls_jPlot, dunit=dunit, axJ=ax, axJ1=ax2, fs_=fs_, dcolor=dcolor)
    elif len(ls_jPlot) == 3:
        dbs.axisLabel_op3(ls_axes=ls_axes, ls_para=ls_jPlot, dunit=dunit, axJ=ax, axJ1=ax2, fs_=fs_, dcolor=dcolor)
    else:
        dbs.axisLabel_op4(ls_axes=ls_axes, dunit=dunit, axJ=ax, axJ1=ax2, fs_=fs_, dcolor=dcolor)
    ls_axes = fig.axes

    # fill the axes with averaged profiles
    for en, para in enumerate(ls_jPlot):
        # find correct position of parameter on coordinate system (separate function)
        pos = find_para_position(en=en, para=para, ls_jPlot=ls_jPlot)

        pkeys = tabcorr[para].to_numpy()
        colK = dbs._findCoreLabel(option1=pkeys[sval], option2='core {}'.format(pkeys[sval]), ls=list(dav[para].keys()))
        data = dav[para][colK]

        # exclude parameter from the index upon first adjustment
        if para in data.index:
            data = data.loc[:data.index[list(data.index).index(para) - 1]]
        ls_axes[pos].plot(data['mean'].values, data.index, lw=1.5, color=dcolor[para])
        ls_axes[pos].xaxis.label.set_color(dcolor[para]), ls_axes[pos].tick_params(axis='x', colors=dcolor[para])
        ls_axes[pos].axhline(0, color='k', lw=0.5)

    # make it a pretty layout
    if len(ls_jPlot) == 1:
        ls_axes[1].set_axis_off()

    # layout and final drawing
    dbs.adjust_axes(ls_jPlot=ls_jPlot, figProf=fig)
    ax.set_ylabel('Depth / µm'), ax.invert_yaxis()
    fig.tight_layout()

    # show or close
    fig.canvas.draw() if show is True else plt.close()
    return fig
