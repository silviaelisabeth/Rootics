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
"""

import matplotlib
import matplotlib.pylab as plt
import seaborn as sns
import numpy as np
import pandas as pd
import os

import functions_dbs as dbs

# global parameter
sns.set_context('paper'), sns.set_style('ticks')

# color list for samples: grey, orange, petrol, green, yellow, light grey, blue
ls_col = list(['#4c5558', '#eb9032', '#21a0a8', '#9ec759', '#f9d220', '#96a6ab', '#1B08AA', '#3D14E1', '#D20D41',
               '#E87392', '#40A64A'])

# global variables
coords = dict()
ls_figtype = ['png', 'tiff']
dpi = 300
fs_ = 9


# --------------------------------------------------------------------------------------------------------------------
def load_pHdata(dcol_label, grp_label, data, results):
    # check whether we have a data file
    loadData = dbs.check4LoadingData(stringFile=data[1:-1])

    if loadData is True:
        # raw measurement file pre-processed and saved per default as rawData file
        dsheets, dignore = dbs._loadGlobData(file_str=data, dcol_label=dcol_label)
        for k in dignore.keys():
            if 'pH' in dignore[k].keys():
                l = k

        # pre-check whether pH_all in sheet names
        sheet_select = dbs.sheetname_check(dsheets, para='pH')
        checked = dbs.checkDatavsPara(sheet_select, par='pH')

        if checked is True:
            # prepare file depending on the type
            ddata = dsheets[sheet_select].set_index('Nr')

            # remove excluded profiles
            ddata_update = dbs._excludeProfiles(analyt='pH', dignore=dignore[l], ddata=ddata)

            if grp_label is None:
                grp_label = ddata_update.columns[0]

            # list all available cores for pH sheet
            ls_core = list(dict.fromkeys(ddata_update[ddata_update.columns[0]]))

            # import all measurements for given parameter
            [dpH_core, _, ls_colname] = dbs.load_measurements(dsheets=ddata_update, ls_core=ls_core, para=sheet_select)
            results['pH profile raw data'], results['pH adjusted'] = dpH_core, dpH_core.copy()
            return checked, grp_label, results, ls_colname, ls_core
        else:
            return checked, grp_label, results, None, None
    else:
        return False, grp_label, results, None, None


# --------------------------------------------------------------------------------------------------------------------
def save_pHdata(save_path, save_params, data, results):
    dout_pH = dict()
    # for an external function
    ls_saveData = list()
    [ls_saveData.append(i) for i in save_params.split(',') if 'fig' not in i]
    if 'raw data' in ls_saveData:
        dout0 = dict()
        for c in results['pH profile raw data'].keys():
            df = pd.concat([results['pH profile raw data'][c][s][results['pH profile raw data'][c][s].columns[1:]]
                            for s in results['pH profile raw data'][c].keys()], axis=1)
            dout0[c] = df
        dout_pH['pH profile raw data'] = pd.concat(dout0, axis=1)

    # if adjusted in list to save + if anything has changed from raw data
    if 'adjusted data' in ls_saveData:
        dout0 = dict()
        for c in results['pH adjusted'].keys():
            df = pd.concat([results['pH adjusted'][c][s][results['pH adjusted'][c][s].columns[1:]]
                            for s in results['pH adjusted'][c].keys()], axis=1)
            dout0[c] = df
        dout_pH['pH adjusted'] = pd.concat(dout0, axis=1)

    # save to excel sheets
    dbs.save_rawExcel(dout=dout_pH, file=data, savePath=save_path)


def save_pHfigures(save_para, path_save, results, grp_label, fs_):
    # create folder for figure output
    ls_saveFig = list()
    [ls_saveFig.append(i) for i in save_para.split(',') if 'fig' in i]
    if len(ls_saveFig) > 0:
        save_path = path_save + '/Graphs/'
        # make folder "Graphs" if it doesn't exist
        if not os.path.exists(save_path):
            os.makedirs(save_path)

        # make a project folder for the specific analyte if it doesn't exist
        save_path = save_path + 'pH_project/'
        if not os.path.exists(save_path):
            os.makedirs(save_path)

        # save figures
        if 'fig raw' in ls_saveFig:
            dfig = dict()
            for c in results['pH profile raw data'].keys():
                fig = plot_pHProfile(data_pH=results['pH profile raw data'], core=c, scale=None, ls='-.', show=False,
                                     ls_core=list(results['pH profile raw data'].keys()), grp_label=grp_label,
                                     fs_=fs_*0.8)
                dfig[c] = fig

            # make a project folder for the specific analyte if it doesn't exist
            save_folder1 = dbs._actualFolderName(savePath=save_path, cfolder='rawProfile', rlabel='run')
            if not os.path.exists(save_folder1):
                os.makedirs(save_folder1)

            # actual saving of pH raw data
            for f in dfig.keys():
                for t in ls_figtype:
                    name = save_folder1 + 'rawDepthprofile_core-{}.'.format(f) + t
                    dfig[f].savefig(name, bbox_inches='tight', pad_inches=0.1, dpi=dpi)

        if 'fig adjusted' in ls_saveFig:
            dfig = dict()
            for c in results['pH adjusted'].keys():
                fig = plot_pHProfile(data_pH=results['pH adjusted'], core=c, scale=None, ls='-', show=False,
                                     fs_=fs_*0.8, ls_core=list(results['pH adjusted'].keys()), grp_label=grp_label)
                dfig[c] = fig

            # make a project folder for the specific analyte if it doesn't exist
            save_folder2 = dbs._actualFolderName(savePath=save_path, cfolder='DepthProfile', rlabel='run')
            if not os.path.exists(save_folder2):
                os.makedirs(save_folder2)

            # actual saving of pH raw data
            for f in dfig.keys():
                for t in ls_figtype:
                    name = save_folder2 + 'Depthprofile_core-{}.'.format(f) + t
                    dfig[f].savefig(name, bbox_inches='tight', pad_inches=0.1, dpi=dpi)


# --------------------------------------------------------------------------------------------------------------------
def plot_pHProfile(data_pH, core, ls_core, scale, grp_label, fs_, ls='-.', fig=None, ax=None, show=True,
                   trimexact=False):
    plt.ioff()
    # identify closest value in list
    core_select = dbs.closest_core(ls_core=ls_core, core=core)

    # initialize figure
    if ax is None:
        fig, ax = plt.subplots(figsize=(3, 4), linewidth=0)
    else:
        ax.cla()
    ax.set_xlabel('pH value', fontsize=fs_), ax.set_ylabel('Depth / µm', fontsize=fs_)
    ax.invert_yaxis()

    if core_select != 0:
        ax.title.set_text('pH depth profile for {} {}'.format(grp_label, core_select))
        ax.axhline(0, lw=.5, color='k')

        if show is False:
            [ax.spines[axis].set_linewidth(0.5) for axis in ['top', 'bottom', 'left', 'right']]
            ax.tick_params(labelsize=fs_*0.9)
        ms = 4 if show is False else 6
        lw = 0.75 if ls == '-.' else 1.5
        mark = '.' if ls == '-.' else None

        for en, nr in enumerate(data_pH[core_select].keys()):
            ax.plot(data_pH[core_select][nr]['pH'], data_pH[core_select][nr].index, lw=lw, ls=ls, marker=mark, ms=ms,
                    color=ls_col[en], alpha=0.75, label='sample ' + str(nr))
        ax.legend(frameon=True, fontsize=fs_*0.8)

    # update layout
    if scale:
        if trimexact is True:
            scale_min = -1 * scale[1]/10 if scale[0] == 0 else scale[0]
            scale_max = scale[1]
        else:
            scale_min = -1 * scale[1]/100 if scale[0] == 0 else scale[0]*0.995
            scale_max = scale[1]*1.005
        ax.set_xlim(scale_min, scale_max)
    fig.tight_layout(pad=1.5)

    if show is False:
        sns.despine()
        plt.close(fig)
    else:
        fig.canvas.draw()
    return fig


def plot_adjustpH(core, sample, dfCore, scale, grp_label, fig, ax):
    # initialize first plot with first core and sample
    fig = GUI_adjustDepth(core=core, nr=sample, dfCore=dfCore, scale=scale, fig=fig, ax=ax, grp_label=grp_label)
    fig.canvas.draw()
    return fig


def plot_pHUpdate(core, nr, df_pHs, ddcore, scale, grp_label, fig, ax):
    # clear coordinate system but keep the labels
    ax.cla()
    ax.title.set_text('pH profile for {} {} - sample {}'.format(grp_label, core, nr))
    ax.set_xlabel('pH value'), ax.set_ylabel('Depth / µm')

    # plotting part
    ax.axhline(0, lw=.5, color='k')
    for en in enumerate(ddcore.keys()):
        if en[1] == nr:
            pos = en[0]
    ax.plot(df_pHs['pH'], df_pHs.index, lw=0.75, ls='-.', marker='.', ms=4, color=ls_col[pos], alpha=0.75)

    # general layout
    scale_min = -1 * scale[1]/100 if scale[0] == 0 else scale[0]
    ax.invert_yaxis(), ax.set_xlim(scale_min, scale[1])
    sns.despine(), plt.tight_layout()
    fig.canvas.draw()
    return fig


def GUI_adjustDepth(core, nr, dfCore, scale, grp_label, fig=None, ax=None, show=True):
    plt.ioff()
    # initialize figure plot
    if ax is None:
        fig, ax = plt.subplots(figsize=(5, 3), linewidth=0)
    else:
        ax.cla()

    if core != 0:
        ax.title.set_text('pH profile for {} {} - sample {}'.format(grp_label, core, nr))
        ax.set_ylabel('Depth / µm'), ax.set_xlabel('pH value')

    # plotting part
    ax.axhline(0, lw=.5, color='k')

    # position in sample list to get the right color
    for en in enumerate(dfCore.keys()):
        if en[1] == nr:
            pos = en[0]
    ax.plot(dfCore[nr]['pH'], dfCore[nr].index, lw=0.75, ls='-.', marker='.', ms=4, color=ls_col[pos], alpha=0.75)

    # general layout
    scale_min = -1 * scale[1]/10 if scale[0] == 0 else scale[0]*0.95
    ax.invert_yaxis(), ax.set_xlim(scale_min, scale[1]*1.015)
    sns.despine(), plt.tight_layout(pad=0.5)

    if show is False:
        plt.close(fig)
    else:
        fig.canvas.draw()
    return fig