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
def load_EPdata(data, results, dcol_label, grp_label):
    # check whether we have a data file
    loadData = dbs.check4LoadingData(stringFile=data[1:-1])

    # raw measurement file pre-processed and saved per default as rawData file
    if loadData is True:
        dsheets, dignore = dbs._loadGlobData(file_str=data, dcol_label=dcol_label)
        l = [k for k in dignore.keys() if 'EP' in dignore[k].keys()][0]

        # pre-check whether EP_all in sheet names
        sheet_select = dbs.sheetname_check(dsheets, para='EP')
        checked = dbs.checkDatavsPara(sheet_select, par='EP')

        if checked is True:
            # prepare file depending on the type
            ddata = dsheets[sheet_select].set_index('Nr')

            # remove excluded profiles
            ddata_update = dbs._excludeProfiles(analyt='EP', dignore=dignore[l], ddata=ddata)

            if grp_label is None:
                grp_label = ddata_update.columns[0]

            # list all available cores for pH sheet (in time order, eg, not ordered in ascending/ descending order)
            ls_core = list(dict.fromkeys(ddata_update[ddata_update.columns[0]]))

            # import all measurements for given parameter
            [dEP_core, _, ls_colname] = dbs.load_measurements(dsheets=ddata_update, ls_core=ls_core, para=sheet_select)

            # order depth index ascending
            dEP_core = dict(map(lambda c: (c, dict(map(lambda s: (s, dEP_core[c][s].sort_index(ascending=True)),
                                                       dEP_core[c].keys()))), dEP_core.keys()))
            results['EP adjusted'] = dEP_core

            # separate storage of raw data
            results['EP raw data'] = dict()
            for c in results['EP adjusted'].keys():
                ddic = dict()
                for i in results['EP adjusted'][c].keys():
                    df_i = pd.DataFrame(np.array(results['EP adjusted'][c][i]), index=results['EP adjusted'][c][i].index,
                                        columns=results['EP adjusted'][c][i].columns)
                    ddic[i] = df_i
                results['EP raw data'][c] = ddic
            return checked, results, grp_label, ls_core, dEP_core, ls_colname
        else:
            return False, results, grp_label, None, None, None
    else:
        return False, results, grp_label, None, None, None


def load_additionalInfo(data):
    # convert potential str-list into list of strings
    if '[' in data:
        ls_file = [i.strip()[1:-1] for i in data[1:-1].split(',')]
    else:
        ls_file = list(data)

    # load excel sheet with all measurements
    dic_sheets = dict()
    for f in enumerate(ls_file):
        dic_sheets_ = pd.read_excel(f[1], sheet_name=None)
        # get the metadata and correlation sheets
        df_meta = None
        for c in dic_sheets_.keys():
            if 'Meta' in c or 'meta' in c:
                df_meta = dic_sheets_[c]
        dic_sheets[f[0]] = dict({'meta data': df_meta})

    # merge and double check duplicates (especially for pH-H2S correlation)
    dsheets_add = dic_sheets[0]
    for en in range(len(ls_file) - 1):
        # get meta data info
        if 'meta data' in dic_sheets[en + 1].keys():
            dfmeta_sum = pd.concat([dsheets_add['meta data'], dic_sheets[en + 1]['meta data']], axis=0)
        else:
            dfmeta_sum = dsheets_add['meta data']

        dsheets_add = dict({'meta data': dfmeta_sum})
    return dsheets_add


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


def save_EPfigure(save_para, path_save, ls_core, results, dobj_hidEP, grp_label, scaleEP):
    ls_saveFig = list()
    [ls_saveFig.append(i) for i in save_para.split(',') if 'fig' in i]
    if len(ls_saveFig) > 0:
        save_path = path_save + '/Graphs/'
        # make folder "Graphs" if it doesn't exist
        if not os.path.exists(save_path):
            os.makedirs(save_path)

        # make a project folder for the specific analyte if it doesn't exist
        save_path = save_path + 'EP_project/'
        if not os.path.exists(save_path):
            os.makedirs(save_path)

        # generate images of all all samples (don't plot them)
        [dfigRaw, dfigBase, dfigDC,
         dfigFit] = fig4saving_EP(ls_core=ls_core, draw=results['EP raw data'], dadj=results['EP adjusted'],
                                  ddrift=results['EP profile drift'], dfit=results['EP drift correction'],
                                  dobj_hidEP=dobj_hidEP, results=results, grp_label=grp_label, scaleEP=scaleEP)

        # individual profiles / drift corrections
        if 'fig raw' in ls_saveFig:
            save_figraw(save_path=save_path, dfigRaw=dfigRaw)
        if 'fig adjusted' in ls_saveFig:
            save_figdepth(save_path=save_path, dfigBase=dfigBase)
        if 'fig fit' in ls_saveFig:
            save_figFit(save_path=save_path, dfigFit=dfigFit)
            save_figDC(save_path=save_path, dfigDC=dfigDC)


def save_figraw(save_path, dfigRaw):
    # find the actual running number
    save_folder = dbs._actualFolderName(savePath=save_path, cfolder='rawProfile', rlabel='run')
    if not os.path.exists(save_folder):
        os.makedirs(save_folder)

    for f in dfigRaw.keys():
        for t in ls_figtype:
            name = save_folder + 'rawDepthprofile_core-{}.'.format(f) + t
            dfigRaw[f].savefig(name, bbox_inches='tight', pad_inches=0.1, dpi=dpi)


def save_figdepth(save_path, dfigBase):
    # find the actual running number
    save_folder = dbs._actualFolderName(savePath=save_path, cfolder='DepthProfile', rlabel='run')
    if not os.path.exists(save_folder):
        os.makedirs(save_folder)

    for f in dfigBase.keys():
        for t in ls_figtype:
            name = save_folder + 'Depthprofile_core-{}_adjusted.'.format(f) + t
            dfigBase[f].savefig(name, bbox_inches='tight', pad_inches=0.1, dpi=dpi)


def save_figFit(save_path, dfigFit):
    # find the actual running number
    save_folder = dbs._actualFolderName(savePath=save_path, cfolder='DriftCorrect', rlabel='run')
    if not os.path.exists(save_folder):
        os.makedirs(save_folder)

    for f in dfigFit.keys():
        for t in ls_figtype:
            name = save_folder + 'DriftCorrect_group-{}.'.format(f) + t
            dfigFit[f].savefig(name, bbox_inches='tight', pad_inches=0.1, dpi=dpi)


def save_figDC(save_path, dfigDC):
    # find the actual running number
    save_folder = dbs._actualFolderName(savePath=save_path, cfolder='CurveReg', rlabel='run')
    if not os.path.exists(save_folder):
        os.makedirs(save_folder)

    for f in dfigDC.keys():
        for t in ls_figtype:
            name = save_folder + 'CurveReg_group-{}.'.format(f) + t
            dfigDC[f].savefig(name, bbox_inches='tight', pad_inches=0.1, dpi=100)


def save_EPdata(path_save, save_params, dout, data, ls_allData):
    # make a project folder for the specific analyte if it doesn't exist
    save_path = path_save + '/EP_project/'
    if not os.path.exists(save_path):
        os.makedirs(save_path)

    ls_saveData = list()
    [ls_saveData.append(i) for i in save_params.split(',') if 'fig' not in i]
    if len(ls_saveData) > 0:
        # all keys that shall be removed
        ls_removeKey = list()
        [ls_removeKey.append(i) for i in ls_allData if i not in ls_saveData]
        if 'fit_mV' in ls_removeKey:
            ls_removeKey.append('derivative_mV')

        # delete all keys not in that list regardless of whether it is in the dictionary
        [dout.pop(i, None) for i in ls_removeKey]

        # save to excel sheets
        dbs.save_rawExcel(dout=dout, file=data, savePath=save_path)


def cropDF_EP(s, ls_cropy, ddata, Core):
    if ls_cropy:
        # in case there was only 1 point selected -> extend the list to the other end
        if len(ls_cropy) == 1:
            sub = (ddata[Core][s].index[0] - ls_cropy[0], ddata[Core][s].index[-1] - ls_cropy[0])
            if np.abs(sub[0]) < np.abs(sub[1]):
                ls_cropy = [ls_cropy[0], ddata[Core][s].index[-1]]
            else:
                ls_cropy = [ddata[Core][s].index[0], ls_cropy[0]]

        # actually crop the depth profile to the area selected. In case more than 2 points have been selected, choose
        # the outer ones -> trim y-axis
        dcore_crop = ddata[Core][s].loc[min(ls_cropy): max(ls_cropy)]
    else:
        dcore_crop = ddata[Core][s]
    return dcore_crop


def popData_EP(dcore_crop, ls_out):
    ls_pop = [min(dcore_crop.index.to_numpy(), key=lambda x: abs(x - ls_out[p])) for p in range(len(ls_out))
              if ls_out[p] is not None]
    # drop in case value is still there
    [dcore_crop.drop(p, inplace=True) for p in ls_pop if p in dcore_crop.index]
    return dcore_crop


def fig4saving_EP(ls_core, draw, dadj, ddrift, dfit, dobj_hidEP, results, grp_label, scaleEP):
    dfigRaw, dfigBase, dfigDC, dfigFit = dict(), dict(), dict(), dict()
    # raw data and adjusted data
    for c in ls_core:
        dfigRaw[c], _ = plot_initalProfile(data=draw, para='EP', unit='mV', core=c, ls='-.', col_name='EP_mV',
                                           show=False, ls_core=ls_core, dobj_hidEP=dobj_hidEP, trimexact=False,
                                           grp_label=grp_label, scaleEP=None, fs_=fs_*0.8)
        dfigBase[c], _ = plot_initalProfile(data=dadj, para='EP', unit='mV', core=c, ls='-', col_name='EP_mV',
                                            show=False, ls_core=ls_core, dobj_hidEP=dobj_hidEP, trimexact=False,
                                            grp_label=grp_label, scaleEP=scaleEP, fs_=fs_*0.8)

    # profile drift for individual groups + curve fitting
    for g in ddrift.keys():
        df, ax = plot_profileTime(nP=g, df_pack=ddrift[g][1], resultsEP=dadj, dorder=results['EP order'], show=False)
        dfP2_ = [dadj[p[0]][p[1]].sort_index(ascending=True) for p in results['EP order'][g]]
        ax.plot(pd.concat(dfP2_, axis=0)['EP_mV'].to_numpy(), color='darkorange', lw=1., label='corrected')
        sns.despine()
        dfigFit[g] = df

        # add legend for fit info to curve fitting plot
        if g in dfit.keys():
            figR, axR = plot_Fit(df_reg=dfit[g]['regression curve'], ydata=dfit[g]['average EP'], figR=None, axR=None,
                                 show=False)

            ls_label = [('drift correction:', g), ('function:', dfit[g]['regression']),
                        ('fit parameter:', dfit[g]['fit parameter']), ('χ2:', dfit[g]['chi-square'])]
            xpos, ypos = (axR.get_xlim()[1] - axR.get_xlim()[0])*0.75, (axR.get_ylim()[1] - axR.get_ylim()[0])*0.9
            for en, label in enumerate(ls_label):
                axR.annotate(label, xy=(xpos, ypos-en*1/500), xytext=(0, 5), textcoords='offset points',
                             ha='center', va='bottom', fontsize=12)
            sns.despine()
            dfigDC[g] = figR

    return dfigRaw, dfigBase, dfigDC, dfigFit


def plot_profileTime(nP, df_pack, resultsEP, dorder, fig=None, ax=None, show=True):
    plt.ioff()
    # plot all profiles belonging to the same package
    if ax is None:
        fig, ax = plt.subplots(linewidth=0)
    else:
        ax.cla()
    ax.set_xlabel('measurement point'), ax.set_ylabel('EP / mV')
    ax.set_title('EP profile over time for selected group {}'.format(int(nP)))

    # plotting
    ax.plot(df_pack['EP_mV'].to_numpy(), marker='.', lw=0, label='original profiles')

    # indicate horizontal axes after individual profiles and add profile information
    len_prof = [len(resultsEP[p[0]][p[1]].sort_index(ascending=True)) for p in dorder[nP]]
    ls_label = ['(' + str(p[0]) + '|' + str(p[1]) +')' for p in dorder[nP]]

    height = max(df_pack['EP_mV'].to_numpy())
    m, en = len_prof[0], 0
    for en, l in enumerate(len_prof):
        if en < len(len_prof)-1:
            ax.axvline(m, color='k', lw=0.75)
        ax.annotate(ls_label[en], xy=(m-l/2, height), xytext=(0, 15), textcoords='offset points', ha='center',
                    va='bottom', fontsize=6)
        m += l

    sns.despine(), plt.tight_layout(pad=0.5)
    # adjust yscale for both (raw and fitted) data
    ylim = ax.get_ylim()
    ax.set_ylim(-0.5, ylim[1] * 1.15) if ylim[0] > 1 else ax.set_ylim(ylim[0], ylim[1]*1.15)

    # to show or not to show the figure plot
    fig.canvas.draw() if show is True else plt.close()
    return fig, ax


def plot_Fit(df_reg, ydata, figR=None, axR=None, show=True):
    plt.ioff()
    if axR is None:
        figR, axR = plt.subplots(figsize=(5, 3), linewidth=0)
    else:
        axR.cla()
    axR.set_xlabel('number profile'), axR.set_ylabel('average EP / mV')
    axR.plot(ydata, lw=0, marker='o')
    axR.plot(df_reg, ls='-.', color='k')
    sns.despine(), plt.tight_layout()

    if show is True:
        figR.canvas.draw()
    else:
        plt.close()
    return figR, axR


def plot_initalProfile(data, para, unit, col_name, core, ls_core, dobj_hidEP, grp_label, fs_, ls='-.', scaleEP=None,
                       fig=None, ax=None, show=True, trimexact=False):
    plt.ioff()
    lines = list()
    # identify closest value in list
    if isinstance(core, float) or isinstance(core, int):
        core = dbs._findCoreLabel(option1=core, option2='core ' + str(core), ls=ls_core)
    core_select = dbs.closest_core(ls_core=ls_core, core=core)

    # initialize figure
    if ax is None:
        fig, ax = plt.subplots(figsize=(3, 4), linewidth=0)
    else:
        ax.cla()
    ax.set_xlabel('{} / {}'.format(para, unit), fontsize=fs_), ax.set_ylabel('Depth / µm', fontsize=fs_)
    ax.invert_yaxis()

    if core_select != 0:
        ax.title.set_text('{} depth profile for {} {}'.format(grp_label, para, core_select))
        ax.axhline(0, lw=.5, color='k')

        # adjust plot parameters depending on the setting
        if show is False:
            [ax.spines[axis].set_linewidth(0.5) for axis in ['top', 'bottom', 'left', 'right']]
            ax.tick_params(labelsize=fs_*0.9)
        ms = 4 if show is False else 6
        lw = 0.75 if ls == '-.' else 1.5
        mark = '.' if ls == '-.' else None

        # go through samples of the core to plot
        for en, nr in enumerate(data[core_select].keys()):
            if core_select in dobj_hidEP.keys():
                alpha_ = .0 if 'sample ' + str(nr) in dobj_hidEP[core_select] else .6
            else:
                alpha_ = .6
            line, = ax.plot(data[core_select][nr][col_name], data[core_select][nr].index, lw=lw, ls=ls, marker=mark,
                            alpha=alpha_, color=ls_col[en], pickradius=6, ms=ms, label='sample ' + str(nr))
            lines.append(line)
        leg = ax.legend(frameon=True, fontsize=fs_*0.8)

        # ------------------------------------------------------------------
        # combine legend
        lined = dict()
        for legline, origline in zip(leg.get_lines(), lines):
            legline.set_picker(5.)  # 5 pts tolerance
            lined[legline] = origline

        # picker - hid curves in plot
        def onpick(event):
            ls_hid = dobj_hidEP[core_select] if core_select in dobj_hidEP.keys() else list()
            ls_hid = list(dict.fromkeys(ls_hid))

            # on the pick event, find the orig line corresponding to the legend proxy line, and toggle the visibility
            legline = event.artist
            if legline in lined:
                origline = lined[legline]

                # handle initial curve visibility
                curve_vis = not origline.get_visible()

                # handle hidden object list
                if origline.get_label() in ls_hid:
                    # find position of label and pop/remove
                    pos = ls_hid.index(origline.get_label())
                    ls_hid.pop(pos)
                    # update curve visibility accordingly
                    curve_vis = True
                else:
                    ls_hid.append(origline.get_label())

                # handle legend label visibility - check the number of same sample entries
                ls_crop = list(dict.fromkeys(ls_hid))
                ls_hid_split = dict(map(lambda c: (c, [i for i, val in enumerate(ls_hid) if val == c]), ls_crop))
                for s in ls_hid_split.keys():
                    if len(ls_hid_split[s]) % 2 == 0:
                        curve_vis = not curve_vis

                legline.set_alpha(1.0 if curve_vis else 0.2)
                alpha_ = .6 if curve_vis is True else 0.
                origline.set_visible(curve_vis)
                origline.set_alpha(alpha_)

                # collect all hidden curves
                ls_hid = list(dict.fromkeys(ls_hid))
                dobj_hidEP[core_select] = ls_hid
            fig.canvas.draw()

        # Call click func
        fig.canvas.mpl_connect('pick_event', onpick)

    # update layout
    if scaleEP and core_select in scaleEP.keys():
        min_ = np.nanmin(scaleEP[core_select])
        max_ = np.nanmax(scaleEP[core_select])
    else:
        min_ = np.nanmin([data[core_select][nr][col_name].min() for nr in data[core_select].keys()])
        max_ = np.nanmax([data[core_select][nr][col_name].max() for nr in data[core_select].keys()])
    if trimexact is False:
        min_ = min_*1.5 if min_ < 0 else min_*0.95
        max_ = max_*1.05
    ax.set_xlim(min_, max_)
    fig.tight_layout(pad=1.5)

    if show is True:
        fig.canvas.draw()
    else:
        sns.despine()
        plt.close()
    return fig, dobj_hidEP


def plot_adjustEP(core, sample, col, dfCore, grp_label, fig=None, ax=None):
    # initialize first plot with first core and sample
    fig = GUI_adjustDepthEP(core=core, nr=sample, dfCore=dfCore, grp_label=grp_label, col=col, fig=fig, ax=ax)
    fig.canvas.draw()
    return fig


def plot_EPUpdate(core, nr, df, ddcore, scale, col, grp_label, fig, ax):
    # clear coordinate system but keep the labels
    ax.cla()
    ax.title.set_text('EP profile for {} {} - sample {}'.format(grp_label, core, nr))
    ax.set_xlabel('EP / mV'), ax.set_ylabel('Depth / µm')

    # plotting part
    ax.axhline(0, lw=.5, color='k')
    for en in enumerate(ddcore.keys()):
        if en[1] == nr:
            pos = en[0]
    ax.plot(df[col], df.index, lw=0.75, ls='-.', marker='.', ms=4, color=ls_col[pos], alpha=0.75)

    # general layout
    scale_min = -1 * scale[1]/10 if scale[0] == 0 else scale[0]
    ax.invert_yaxis(), ax.set_xlim(scale_min, scale[1])
    sns.despine(), plt.subplots_adjust(bottom=0.2, right=0.95, top=0.8, left=0.25)
    fig.canvas.draw()
    return fig


def GUI_adjustDepthEP(core, nr, dfCore, col, grp_label, fig=None, ax=None, show=True):
    plt.ioff()
    # initialize figure plot
    if ax is None:
        fig, ax = plt.subplots(figsize=(5, 3), linewidth=0)
    else:
        ax.cla()

    if core != 0:
        ax.title.set_text('EP profile for {} {} - sample {}'.format(grp_label, core, nr))
        ax.set_ylabel('Depth / µm'), ax.set_xlabel('EP / mV')

    # plotting part
    ax.axhline(0, lw=.5, color='k')

    # position in sample list to get teh right color
    for en in enumerate(dfCore.keys()):
        if en[1] == nr:
            pos = en[0]

    ax.plot(dfCore[nr][col], dfCore[nr].index, lw=0.75, ls='-.', marker='.', ms=4, color=ls_col[pos], alpha=0.75)

    # general layout
    ax.invert_yaxis(), sns.despine(), fig.subplots_adjust(bottom=0.2, right=0.95, top=0.8, left=0.215)

    if show is False:
        plt.close(fig)
    else:
        fig.canvas.draw()
    return fig