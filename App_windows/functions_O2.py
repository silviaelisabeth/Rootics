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
from lmfit import Model
from scipy import stats
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
def load_O2data(data, grp_label, dcol_label):
    # check whether we have a data file
    loadData = dbs.check4LoadingData(stringFile=data[1:-1])

    # raw measurement file pre-processed and saved per default as rawData file
    if loadData is True:
        dsheets, dignore = dbs._loadGlobData(file_str=data, dcol_label=dcol_label)
        for k in dignore.keys():
            if 'O2' in dignore[k].keys():
                l = k

        # pre-check whether O2_all in sheet names
        sheet_select = dbs.sheetname_check(dsheets, para='O2')
        checked = dbs.checkDatavsPara(sheet_select, par='O2')

        if checked is True:
            # prepare file depending on the type
            ddata = dsheets[sheet_select].set_index('Nr')

            # remove excluded profiles
            ddata_update = dbs._excludeProfiles(analyt='O2', dignore=dignore[l], ddata=ddata)

            if grp_label is None:
                grp_label = ddata_update.columns[0]

            return ddata_update, sheet_select, checked, grp_label
        else:
            return None, None, False, grp_label
    else:
        return None, None, False, grp_label


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
            name = save_folder + 'Depthprofile_core-{}_SWI_corrected.'.format(f) + t
            dfigBase[f].savefig(name, bbox_inches='tight', pad_inches=0.1, dpi=dpi)


def save_figFit(save_path, dfigFit):
    # find the actual running number
    save_folder = dbs._actualFolderName(savePath=save_path, cfolder='Fit', rlabel='run')
    if not os.path.exists(save_folder):
        os.makedirs(save_folder)

    for f in dfigFit.keys():
        for ff in dfigFit[f].keys():
            for t in ls_figtype:
                if isinstance(ff, tuple):
                    name = save_folder + 'Fit_core-{}_sample-{}.'.format(f, ff[0]) + t
                else:
                    name = save_folder + 'Fit_core-{}_sample-{}.'.format(f, ff) + t
                dfigFit[f][ff].savefig(name, bbox_inches='tight', pad_inches=0.1, dpi=dpi)


def save_figPen(save_path, dfigPen):
    # find the actual running number
    save_folder = dbs._actualFolderName(savePath=save_path, cfolder='PenetrationDepth', rlabel='run')
    if not os.path.exists(save_folder):
        os.makedirs(save_folder)

    for f in dfigPen.keys():
        for t in ls_figtype:
            name = save_folder + 'PenetrationDepth_core-{}.'.format(f) + t
            dfigPen[f].savefig(name, bbox_inches='tight', pad_inches=0.1, dpi=dpi)


def save_figure(save_params, path_save, analyte, ls_core, ddata_shift, dic_deriv, dcore_pen, results, dO2_core, dunit,
                dobj_hid, grp_label, dpen_glob):
    ls_saveFig = list()
    [ls_saveFig.append(i) for i in save_params.split(',') if 'fig' in i]
    if len(ls_saveFig) > 0:
        save_path = path_save + '/Graphs/'
        # make folder "Graphs" if it doesn't exist
        if not os.path.exists(save_path):
            os.makedirs(save_path)

        # make a project folder for the specific analyte if it doesn't exist
        save_path = save_path + analyte + '_project/'
        if not os.path.exists(save_path):
            os.makedirs(save_path)

        # generate images of all all samples (don't plot them)
        [dfigRaw, dfigBase, dfigFit,
         dfigPen] = figures4saving(ls_core=ls_core, draw=results['O2 raw data'], ddcore=results['O2 profile'],
                                   deriv=dic_deriv, ddata_shift=ddata_shift, dfit=results['O2 fit'], dunit=dunit,
                                   dcore_pen=dcore_pen, dO2_core=dO2_core, dobj_hid=dobj_hid, dpen_glob=dpen_glob,
                                   grp_label=grp_label)
        # Depth profiles
        if 'fig raw' in ls_saveFig:
            save_figraw(save_path=save_path, dfigRaw=dfigRaw)
        if 'fig adjusted' in ls_saveFig:
            save_figdepth(save_path=save_path, dfigBase=dfigBase)
        # Fit profiles
        if 'fig fit' in ls_saveFig:
            if dfigFit:
                save_figFit(save_path=save_path, dfigFit=dfigFit)
        # Penetration depth
        if 'fig penetration' in ls_saveFig:
            if dfigPen:
                save_figPen(save_path=save_path, dfigPen=dfigPen)


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
def findPotentialLimits(df, lim, lim_min):
    # for all samples in selected core - find (absolute) minima/maxima potential
    dpot = dict()
    for s in df.keys():
        # maximal O2 concentration - potential for selected core
        df[s] = pd.DataFrame(df[s]).astype(float)
        idxmax = df[s].idxmax()[0]
        if len(df[s].loc[idxmax - lim:idxmax + lim]) < 3:
            lim = 200
        pot_max = (df[s].loc[idxmax - lim:idxmax + lim].mean()[0], df[s].loc[idxmax - lim:idxmax + lim].std()[0])

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
    pot_av = pd.concat([pd.DataFrame(pd.concat(dpot).T.filter(like='max').mean(axis=1)),
                        pd.DataFrame(pd.concat(dpot).T.filter(like='min').mean(axis=1))], axis=1)
    pot_av.columns = ['max', 'min']
    return pot_av


def av_penetrationDepth(dpen_glob, core_select, ls_remain):
    mean_ = (dpen_glob['Depth / µm'].loc[core_select].loc[ls_remain].mean(),
             dpen_glob['O2_µmol/L'].loc[core_select].loc[ls_remain].mean())
    std_ = (dpen_glob['Depth / µm'].loc[core_select].loc[ls_remain].std(),
            dpen_glob['O2_µmol/L'].loc[core_select].loc[ls_remain].std())

    # update dpen_glob
    dpen_glob['Depth / µm'].loc[core_select].loc['mean'] = mean_[0]
    dpen_glob['O2_µmol/L'].loc[core_select].loc['mean'] = mean_[1]
    dpen_glob['Depth / µm'].loc[core_select].loc['std'] = std_[0]
    dpen_glob['O2_µmol/L'].loc[core_select].loc['std'] = std_[1]
    return dpen_glob, mean_, std_


# --------------------------------------------------------------------------------------------------------------------
def fit_baseline(ls_core, ls_nr, dunit_O2, dic_dcore, steps, gmod, adv):
    dfit, dic_deriv = dict(), dict()
    for core in ls_core:
        dfit_, dic_deriv_ = dict(), dict()
        for nr in ls_nr[core]:
            [res, df_fit, df_fitder, df_fitder2,
             xshift] = baseline_finder(dic_dcore=dic_dcore, core=core, nr=nr, dunit_O2=dunit_O2, steps=steps, adv=adv,
                                       model=gmod)
            dfit_[nr], dic_deriv_[nr] = (res, df_fit, xshift), (df_fitder, df_fitder2)
        dfit[core] = dfit_
        dic_deriv[core] = dic_deriv_
    return dfit, dic_deriv


def baseline_finder(dic_dcore, core, nr, dunit_O2, steps, model, adv):
    # curve fit according to selected model
    if isinstance(nr, tuple):
        nr = nr[0]
        if '/L' in dunit_O2 or '/l' in dunit_O2:
            col_plot = None
            for c in pd.DataFrame(dic_dcore[core][nr]).columns:
                if isinstance(c, str):
                    if '/L' in c or '/l' in c:
                        col_plot = c
                else:
                    col_plot = pd.DataFrame(dic_dcore[core][nr]).columns[0]
        else:
            col_plot = [c for c in pd.DataFrame(dic_dcore[core][nr]).columns if dunit_O2 in c][0]
    else:
        col_plot = dbs.find_column2plot(unit=dunit_O2, df=dic_dcore[core][nr])

    if isinstance(dic_dcore[core][nr], pd.Series):
        ydata_ = pd.DataFrame(dic_dcore[core][nr]).dropna()
        ydata = ydata_[ydata_.columns[0]]
    else:
        ydata = dic_dcore[core][nr][col_plot].dropna()
    xdata = ydata.index

    # initial parameters
    if adv is True:
        para = model.make_params(a=-int(ydata.loc[xdata[:3]].mean()), b=.001, c=.001,
                                 d=-int(ydata.loc[xdata[-3:]].mean()))
    else:
        para = model.make_params(a=-int(ydata.loc[xdata[:3]].mean()), b=.001, c=.001)
    res = model.fit(ydata.to_numpy(), para, x=xdata)

    # 1st derivative
    arg = [res.params[p].value for p in res.params.keys()]
    xnew = np.linspace(xdata[0], xdata[-1], num=int((xdata[-1]-xdata[0])/steps+1))
    if adv is True:
        yfit = _gompertz_curve_adv(x=xnew, a=arg[0], b=arg[1], c=arg[2], d=arg[3])
    else:
        yfit = _gompertz_curve(x=xnew, a=arg[0], b=arg[1], c=arg[2])
    df_fit = pd.DataFrame(yfit, index=xnew)
    df_fitder = df_fit.diff()

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


def baseline_finder_DF(dic_dcore, dunit_O2, steps, model, adv):
    # curve fit according to selected model
    if '/L' in dunit_O2 or '/l' in dunit_O2:
        col_plot = [c for c in dic_dcore.columns if '/L' in c or '/l' in c][0]
    else:
        col_plot = [c for c in dic_dcore.columns if dunit_O2 in c][0]

    ydata = dic_dcore[col_plot].dropna()
    xdata = ydata.index

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
                          (c, dict(map(lambda n: (n, pd.DataFrame(np.array(dic_dcore[c][n]),
                                                                  index=dic_dcore[c][n].index - dfit[c][n][2],
                                                                  columns=dic_dcore[c][n].columns)),
                                       dic_dcore[c].keys()))), dic_dcore.keys()))
    return data_shift


def penetration_depth(df, unit, steps, model, adv):
    xdata = df.index
    # find column to be fitted
    col_plot = dbs.find_col2plot(unit=unit, df=df)
    ydata = df[col_plot]

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


def sigmoidalFit(ddata, sheet_select, dunit, results, steps):
    # pre-set of parameters
    gmod = Model(_gompertz_curve_adv)

    # ----------------------------------------------------------------------------------
    # list all available cores for O2 sheet
    ls_core = list(dict.fromkeys(ddata[ddata.columns[0]]))

    # import all measurements for given parameter
    [dic_dcore, ls_nr, ls_colname] = dbs.load_measurements(dsheets=ddata, ls_core=ls_core, para=sheet_select)
    results['O2 profile'] = dic_dcore

    # separate storage of raw data
    results['O2 raw data'] = dict()
    for c in results['O2 profile'].keys():
        ddic = dict()
        for i in results['O2 profile'][c].keys():
            df_i = pd.DataFrame(np.array(results['O2 profile'][c][i]), index=results['O2 profile'][c][i].index,
                                columns=results['O2 profile'][c][i].columns)
            ddic[i] = df_i
        results['O2 raw data'][c] = ddic

    # curve fit and baseline finder
    dfit, dic_deriv = fit_baseline(ls_core=ls_core, ls_nr=ls_nr, dunit_O2=dunit['O2'], dic_dcore=dic_dcore, steps=steps,
                                   gmod=gmod, adv=True)
    results['O2 fit'], results['O2 derivative'] = dfit, dic_deriv
    return ls_core, ls_colname, gmod, dic_dcore, dic_deriv, dfit, results


def updateBaseline_O2Fit(results, dunit, steps, gmod):
    # get the relevant parameters ls_core and samples of each core (dls_nr)
    ls_core = list(dict.fromkeys(results['O2 profile'].keys()))

    if isinstance(results['O2 profile'][ls_core[0]].keys(), tuple):
        dls_nr = dict(map(lambda core: (core, [c[0] for c in results['O2 profile'][core].keys()]), ls_core))
    else:
        dls_nr = dict(map(lambda core: (core, list(dict.fromkeys(results['O2 profile'][core].keys()))), ls_core))

    # update baseline finding fit function
    dfit, dic_deriv = fit_baseline(ls_core=ls_core, ls_nr=dls_nr, dunit_O2=dunit['O2'], dic_dcore=results['O2 profile'],
                                   steps=steps, gmod=gmod, adv=True)

    # update results dictionary for fit and derivative
    results['O2 fit'], results['O2 derivative'] = dfit, dic_deriv
    return results


# --------------------------------------------------------------------------------------------------------------------
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


def dissolvedO2_calc(T, sal):
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
                    sal * (pdO2['B1'] + pdO2['B2'] * (1 / convF) + pdO2['B3'] * (1 / convF) ** 2))

    # maximal dissolved O2 in µmol/L for a given temperature and salinity
    dO2_max = taylor / (pdO2['R'] * 273.15) * 1000  # µM
    return 0, dO2_max


def O2calc4conc_one4all(core_sel, data_shift, o2_dis, lim, lim_min, unit):
    # get the correct column
    dex = pd.concat(data_shift[list(data_shift.keys())[0]], axis=1)
    if '/L' in unit or '/l' in unit:
        col = [c for c in dex.columns.levels[1] if '/L' in c or '/l' in c][0]
    else:
        col = [c for c in dex.columns.levels[1] if unit in c][0]

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
def plot_penetrationDepth(core, s, df_fit, O2_pen, unit, show=False):
    plt.ioff()
    fig, ax = plt.subplots(figsize=(5, 3), linewidth=0)
    fig.canvas.set_window_title('Penetration depth for core ' + str(core) + ' sample-' + str(s))

    # plotting part
    ax.plot(df_fit[0].to_numpy(), df_fit.index, lw=1., color='navy')
    ax.axhline(0, lw=0.75, color='k')

    # indicate penetration depth
    if len(df_fit[df_fit[0] < O2_pen].index) > 0:
        pen_h, pen_v = df_fit[df_fit[0] < O2_pen].index[0], df_fit.loc[df_fit[df_fit[0] < O2_pen].index[0], 0]
        ax.axhline(pen_h, ls=':', color='crimson')
    else:
        pen_h, pen_v = None, None

    # general layout
    ax.set_xlim(min(df_fit[0].to_numpy()), max(df_fit[0].to_numpy()))

    ax.invert_yaxis()
    ax.set_ylabel('Depth / µm'), ax.set_xlabel('O2 concentration ' + unit)
    sns.despine(), plt.tight_layout()

    if show is False:
        sns.despine()
        plt.close(fig)
    else:
        plt.show()

    return fig, (pen_h, pen_v)


def GUI_rawProfile(core, ls_core, O2data, grp_label, fig=None, ax=None, show=True, fs=8):
    plt.ioff()

    # identify closest value in list
    core_select = dbs.closest_core(ls_core=ls_core, core=core)

    # identify column to plot
    for c in O2data[core_select][list(O2data[core_select].keys())[0]].columns:
        if 'mV' in c:
            col2plot = c

    # initialize figure
    if ax is None:
        fig, ax = plt.subplots(figsize=(3, 4), linewidth=0)
    else:
        ax.cla()

    # set layout for GUI or saved plot
    ax.set_xlabel('$O_2$ concentration / mV', fontsize=fs), ax.set_ylabel('Depth / µm', fontsize=fs)
    ax.tick_params(which='both', axis='both', labelsize=fs*0.9), ax.invert_yaxis()

    if show is False:
        [ax.spines[axis].set_linewidth(0.5) for axis in ['top', 'bottom', 'left', 'right']]
    ms = 4 if show is False else 6
    if core_select != 0:
        ax.title.set_text('$O_2$ depth profile for {} {}'.format(grp_label, core_select))
        ax.axhline(0, lw=.5, color='k')
        for en, nr in enumerate(O2data[core_select].keys()):
            ax.plot(O2data[core_select][nr][col2plot], O2data[core_select][nr].index, lw=1, ls='-.', marker='.', ms=ms,
                    color=ls_col[en], alpha=0.75, label='sample ' + str(nr))
        leg = ax.legend(frameon=True, fancybox=True, fontsize=fs*0.8)

    # update layout
    leg.get_frame().set_linewidth(0.5)
    fig.tight_layout(pad=1.5)

    if show is False:
        sns.despine()
        plt.close(fig)
    else:
        fig.canvas.draw()

    return fig


def GUI_baslineShift(data_shift, core, ls_core, plot_col, grp_label, fig=None, ax=None, show=True, fs=8):
    plt.ioff()
    # identify closest value in list
    core_select = dbs.closest_core(ls_core=ls_core, core=core)

    # identify column to plot
    ls_columns = data_shift[core_select][list(data_shift[core_select].keys())[0]].columns
    col2plot, unit = dbs._find_unit_in_column(ls_columns=ls_columns, plot_col=plot_col)

    # plot figure
    if ax is None:
        fig, ax = plt.subplots(figsize=(3, 4), linewidth=0)
    else:
        ax.cla()

    # set layout for GUI or saved plot
    if show is False:
        [ax.spines[axis].set_linewidth(0.5) for axis in ['top', 'bottom', 'left', 'right']]
    ms = 4 if show is False else 6
    ax.set_xlabel('$O_2$ concentration / {}'.format(unit), fontsize=fs), ax.set_ylabel('Depth / µm', fontsize=fs)
    ax.tick_params(which='both', axis='both', labelsize=fs * 0.9), ax.invert_yaxis()

    if core_select == 0 or not data_shift:
        pass
    else:
        ax.title.set_text('Sediment water interface profile (SWI) for {} {}'.format(grp_label, core_select))

    if core_select != 0:
        ax.axhline(0, lw=.5, color='k')
    if core_select == 0:
        pass
    else:
        df = data_shift[core_select]
        for en, nr in enumerate(df.keys()):
            ax.plot(df[nr][col2plot].to_numpy(), df[nr].index, lw=.75, ls='-.', marker='.', color=ls_col[en], alpha=.75,
                    ms=ms, label='sample ' + str(nr))
        leg = ax.legend(frameon=True, fontsize=fs*0.8)

        max_ = np.max([max(df[nr][col2plot].to_numpy()) for nr in df.keys()])
        minPot = np.min([min(df[nr][col2plot].to_numpy()) for nr in df.keys()])
        min_ = minPot*0.5 if int(minPot) > 0 else -1 * np.abs(max_) * 0.15
        ax.set_xlim(min_, np.abs(max_)*1.05)

    # layout editing - ticks orientation and frame line width
    [x.set_linewidth(.5) for x in ax.spines.values()]
    ax.tick_params(axis='both', bottom=True, top=False, direction='out', length=5, width=0.75)
    leg.get_frame().set_linewidth(0.5)
    plt.tight_layout()

    # show or hide figure plot
    if show is False:
        sns.despine()
        plt.close(fig)
    else:
        fig.canvas.draw()
    return fig


def GUI_baslineShiftCore(data_shift, core_select, plot_col, grp_label, fig, ax):
    ax.cla()
    # identify the columns to plot
    dic_col2plot, unit = dbs._find_unit_in_columns_dic(df_data=data_shift, plot_col=plot_col)
    if unit is None:
        print('Nothing to plot here. Expected column not in dataframe.')
    else:
        # plot figure
        if ax is None:
            fig, ax = plt.subplots(figsize=(3, 4), linewidth=0)
        ax.title.set_text('Sediment water interface profile (SWI) for {} {}'.format(grp_label, core_select))
        ax.set_xlabel('$O_2$ / {}'.format(unit)), ax.set_ylabel('Depth / µm')
        ax.invert_yaxis()

        # draw the surface
        ax.axhline(0, lw=.5, color='k')
        # plot the depth corrected profiles for the selected core
        for en, nr in enumerate(data_shift.keys()):
            # draw the recorded points of the sample
            data = data_shift[nr][dic_col2plot[nr]].dropna()
            ax.plot(data.to_numpy(), data.index, lw=.5, ls='-.', marker='.', alpha=.75, color=ls_col[en],
                    label='sample ' + str(nr))
            ax.legend(frameon=True, fontsize=10)

            max_ = np.nanmax(data_shift[nr][dic_col2plot[nr]].to_numpy())
            minPot = np.nanmin(data_shift[nr][dic_col2plot[nr]].to_numpy())
            min_ = minPot * 0.5 if int(minPot) > 0 else -1 * np.abs(max_) * 0.1
            ax.set_xlim(min_, np.abs(max_) * 1.05)

        # layout editing - ticks orientation and frame line width
        [x.set_linewidth(.5) for x in ax.spines.values()]
        ax.tick_params(axis='both', bottom=True, top=False, direction='out', length=5, width=0.75)
        plt.tight_layout(), fig.canvas.draw()
    return fig


def figures4saving(ls_core, dunit, dpen_glob, grp_label, draw=None, ddata_shift=None, ddcore=None, dfit=None,
                   deriv=None, dcore_pen=None, dO2_core=None, dobj_hid=None):
    dfigRaw, dfigBase, dfigFit, dfigProf, dfigPen = dict(), dict(), dict(), dict(), dict()
    for c in ls_core:
        # raw data
        if draw:
            dfigRaw[c] = GUI_rawProfile(O2data=draw, core=c, show=False, ls_core=ls_core, grp_label=grp_label)

        # SWI corrected
        if ddata_shift:
            dfigBase[c] = GUI_baslineShift(data_shift=ddata_shift, grp_label=grp_label, core=c, show=False,
                                           ls_core=ls_core, plot_col='mV')

        # Fit plots
        dfigFitS = dict()
        if ddcore:
            for s in ddcore[c].keys():
                dfigFitS[s] = GUI_FitDepth(core=c, nr=s, dfCore=ddcore[c], dfFit=dfit[c], dfDeriv=deriv[c], dunit=dunit,
                                           grp_label=grp_label, show=False)
            dfigFit[c] = dfigFitS

        # indicated penetration depth
        if dcore_pen:
            dfigPen[c] = GUI_penetration_av_save(core=c, ls_core=ls_core, dpen_glob=dpen_glob, grp_label=grp_label,
                                                 dcore_pen=dcore_pen, dO2_core=dO2_core, dobj_hid=dobj_hid, fs_=fs_,
                                                 show=False)
    return dfigRaw, dfigBase, dfigFit, dfigPen


def plot_Fitselect(core, sample, dfCore, dfFit, dfDeriv, dunit, grp_label, fig, ax, ax1):
    fig3 = GUI_FitDepth(core=core, nr=sample, dunit=dunit, grp_label=grp_label, dfCore=dfCore, dfFit=dfFit,
                        dfDeriv=dfDeriv, fig=fig, ax=ax, ax1=ax1)
    fig3.canvas.draw()
    return fig3


def plot_FitUpdate(core, nr, grp_label, dic_dcore, dfit, dic_deriv, fig, ax, ax1, dunit):
    # clear coordinate system but keep the labels
    ax.cla(), ax1.cla()
    ax.title.set_text('Fit characteristics for {} {} - sample {}'.format(grp_label, core, nr))
    ax.set_xlabel('Depth / µm'), ax.set_ylabel('dissolved O2 / mV'), ax1.set_ylabel('1st derivative', color='#0077b6')

    # plotting part
    col_plot = dbs.find_column2plot(unit=dunit['O2'], df=dic_dcore)
    ax.plot(dic_dcore.index, dic_dcore[col_plot], lw=0, marker='o', ms=4, color='k')
    ax.plot(dfit[dfit.columns[0]], lw=0.75, ls=':', color='k')

    ax1.plot(dic_deriv, lw=1., color='#0077b6')
    ax1.axvline(dic_deriv.idxmin().values[0], ls='-.', color='darkorange', lw=1.5)

    # text annotation to indicate depth correction
    text = 'surface level \nat {:.1f}µm'
    c = 'O2_mV' if 'O2' in dic_dcore.columns else dic_dcore.columns[0]
    ax.text(dic_dcore[c].index[-1] * 0.6, dic_dcore[c].max() * 0.5, text.format(dic_deriv.idxmin().values[0]),
            ha="left", va="center", color='k', size=9.5, bbox=dict(fc='lightgrey', alpha=0.25))

    # general layout
    sns.despine()
    ax.spines['right'].set_visible(True)
    plt.tight_layout(pad=0.75)
    fig.canvas.draw()
    return fig


def GUI_FitDepth(core, nr, dunit, grp_label, dfCore, dfFit, dfDeriv, fig=None, ax=None, ax1=None, show=True):
    # prepare parameters
    nr_ = nr[0] if isinstance(nr, tuple) else nr
    col_plot = dbs.find_column2plot(unit=dunit['O2'], df=dfCore[nr_])

    # ----------------------------------------------------------------
    # initialize figure plot
    plt.ioff()
    if ax is None:
        fig, ax = plt.subplots(figsize=(5, 3), linewidth=0)
        ax1 = ax.twinx()
    else:
        ax.cla(), ax1.cla()

    if core != 0:
        ax.title.set_text('Fit characteristics for {} {} - sample {}'.format(grp_label, core, nr_))
        ax.set_xlabel('Depth / µm')
        ax.set_ylabel('dissolved O2 / {}'.format(dunit['O2'])), ax1.set_ylabel('1st derivative', color='#0077b6')

    # plotting part
    ax.plot(dfCore[nr_].index, pd.DataFrame(dfCore[nr_]).filter(like=col_plot), lw=0, marker='o', ms=4, color='k')
    ax.plot(dfFit[nr][1], lw=0.75, ls=':', color='k')
    ax1.plot(dfDeriv[nr_][0], lw=1., color='#0077b6')
    ax1.axvline(dfFit[nr][2], ls='-.', color='darkorange', lw=1.5)

    # text annotation for sediment water interface depth correction
    text = 'surface level \nat {:.1f}µm'
    if isinstance(pd.DataFrame(dfCore[nr_]).columns[0], tuple):
        c = pd.DataFrame(dfCore[nr_]).columns[0][1]
        df = pd.DataFrame(dfCore[nr_]).filter(like=c)
    else:
        c = 'O2_mV' if 'O2' in dfCore[nr_].columns else dfCore[nr_].columns[0]
        df = dfCore[nr_][c]
    if show is True:
        ax.text(df.index[-1] * 0.6, df.max() * 0.5, text.format(dfFit[nr_][2]), ha="left", va="center", color='k',
                size=9.5, bbox=dict(fc='lightgrey', alpha=0.25))

    # general layout
    ax.set_xlim(df.index[0] * 1.05, df.index[-1] * 1.05)
    sns.despine(), ax.spines['right'].set_visible(True)
    plt.tight_layout(pad=1.)

    # plot or not to plot
    plt.close(fig) if show is False else fig.canvas.draw()
    return fig


def GUI_O2depth(core, ls_core, grp_label, dcore_pen, dobj_hid, dO2_core, fig, ax, fs_):
    ax.cla()
    lines = list()
    # identify closest value in list
    core_select = dbs.closest_core(ls_core=ls_core, core=core)

    # initialize figure plot
    if ax is None:
        fig, ax = plt.subplots(figsize=(3, 4), linewidth=0)
    if core_select != 0:
        ax.title.set_text('Fit depth profile for {} {}'.format(grp_label, core_select))
    ax.set_xlabel('dissolved O2 / µmol/L'), ax.set_ylabel('Depth / µm')
    ax.invert_yaxis()

    if core_select != 0:
        ax.axhline(0, lw=.5, color='k')
        df = pd.concat([dcore_pen[core_select]['{}-Fit'.format(s[0] if isinstance(s, tuple) else s)]
                 for s in dO2_core[core_select].keys()], axis=1)
        df.columns = [i[0] if isinstance(i, tuple) else i for i in dO2_core[core_select].keys()]

        # plot depending whether some samples have already been excluded
        for en, s in enumerate(df.columns):
            if core_select in dobj_hid.keys():
                alpha_ = .0 if 'sample-' + str(s) in dobj_hid[core_select] else .6
            else:
                alpha_ = .6
            d = df[s].dropna()
            line, = ax.plot(d, d.index, color=ls_col[en], lw=1.5, alpha=alpha_, pickradius=6, label='sample-' + str(s))
            lines.append(line)
        leg = ax.legend(frameon=True, fancybox=True, fontsize=fs_ * 0.8)

        # ------------------------------------------------------------------
        # combine legend
        lined = dict()
        for legline, origline in zip(leg.get_lines(), lines):
            legline.set_picker(5.)  # 5 pts tolerance
            lined[legline] = origline

        # picker - hid curves in plot
        def onpick(event):
            ls_hid = dobj_hid[core_select] if core_select in dobj_hid.keys() else list()
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
                dobj_hid[core_select] = ls_hid
            fig.canvas.draw()

        # call click func
        fig.canvas.mpl_connect('pick_event', onpick)

        # layout
        ax.set_xlim(-10, df.max().max() * 1.05), ax.set_ylim(df.idxmin().max() * 1.05, df.idxmax().min() * 1.05)
    return fig, dobj_hid


def GUI_calcO2penetration(O2_pen, dO2_core, unit, steps, gmod, dpen_glob):
    dcore_pen, dcore_fig = dict(), dict()
    for core in dO2_core.keys():
        dic_pen, dfig_pen = dict(), dict()
        for s in dO2_core[core].keys():
            s_col = s[0] if isinstance(s, tuple) else s
            df_fit = penetration_depth(df=dO2_core[core][s_col].dropna(), unit=unit, steps=steps, model=gmod, adv=False)
            dic_pen[str(s_col) + '-Fit'] = df_fit
            [fig, depth_pen] = plot_penetrationDepth(core=core, s=s_col, df_fit=df_fit, O2_pen=O2_pen, unit=unit,
                                                     show=False)

            dic_pen[str(s_col) + '-penetration'] = depth_pen
            dfig_pen[int(s_col)] = fig
        dcore_pen[core], dcore_fig[core] = dic_pen, dfig_pen

    # store all penetration depth information for all samples of the same core in a dictionary
    dpenetration = dict()
    for core in dcore_pen.keys():
        # get specific sample names (keys) where 'penetration' is contained
        ls_pen = list()
        [ls_pen.append(i) for i in dcore_pen[core].keys() if 'penetration' in i]
        dfpen_core = pd.DataFrame([dcore_pen[core][l] for l in ls_pen], columns=['Depth / µm', 'O2_' + unit],
                                  index=[int(i.split('-')[0]) for i in ls_pen])
        dfpen_core.loc['mean', 'Depth / µm'] = dfpen_core['Depth / µm'].mean()
        dfpen_core.loc['std', 'Depth / µm'] = dfpen_core['Depth / µm'].std()
        dfpen_core.loc['mean', 'O2_' + unit] = dfpen_core['O2_' + unit].mean()
        dfpen_core.loc['std', 'O2_' + unit] = dfpen_core['O2_' + unit].std()
        dpenetration[core] = dfpen_core

    dpen_glob.update(pd.concat(dpenetration, axis=0))
    return dcore_pen, dcore_fig


def _supplPlot(core_select, dobj_hid, dpen_glob):
    # samples that should not be included in averaging
    ls_shid = [int(i.split('-')[1]) for i in dobj_hid[core_select]] if core_select in dobj_hid.keys() else list()

    # all samples for core
    ls_sind = list()
    [ls_sind.append(i) for i in dpen_glob['Depth / µm'].loc[core_select].index if i != 'mean' and i != 'std']

    # remaining samples for average penetration depth
    ls_remain = list()
    [ls_remain.append(i) for i in ls_sind if i not in ls_shid]
    return ls_remain


def GUI_penetration_av_save(dpen_glob, grp_label, core, ls_core, dcore_pen, fs_, dO2_core, dobj_hid, fig=None, ax=None,
                            show=True):
    plt.ioff()

    # identify closest value in list
    core_select = dbs.closest_core(ls_core=ls_core, core=core)

    # initialize figure plot
    if ax is None:
        fig, ax = plt.subplots(figsize=(3, 4), linewidth=0)
    else:
        ax.cla()

    # set layout for GUI or saved plot
    [ax.spines[axis].set_linewidth(0.5) for axis in ['top', 'bottom', 'left', 'right']]
    ax.set_xlabel('dissolved $O_2$ / mV', fontsize=fs_), ax.set_ylabel('Depth / µm', fontsize=fs_)
    ax.tick_params(which='both', axis='both', labelsize=fs_ * 0.9), ax.invert_yaxis()
    ax.invert_yaxis()

    # indicate baseline
    if core_select != 0:
        ax.axhline(0, lw=0.75, color='k')

    if core_select != 0:
        # preparation for plot - remaining samples for average penetration depth calculation
        ls_remain = _supplPlot(core_select=core_select, dobj_hid=dobj_hid, dpen_glob=dpen_glob)

        # re-plot only the ones that are shown
        df = pd.concat([dcore_pen[core_select]['{}-Fit'.format(s[0] if isinstance(s, tuple) else s)]
                        for s in dO2_core[core_select].keys()], axis=1)
        df.columns = [i[0] if isinstance(i, tuple) else i for i in dO2_core[core].keys()]
        for en, s in enumerate(df.columns):
            if s in ls_remain:
                d = df[s].dropna()
                ax.plot(d, d.index, color=ls_col[en], lw=1.5, alpha=0.5, label='sample-' + str(s))
        leg = ax.legend(frameon=True, fancybox=True, fontsize=fs_*0.8)
        leg.get_frame().set_linewidth(0.5)

        # indicate penetration depth mean + std according to visible curves
        dpen_glob, mean_, std_ = av_penetrationDepth(dpen_glob=dpen_glob, core_select=core_select, ls_remain=ls_remain)
        ax.axhline(mean_[0], ls=':', color='crimson')
        ax.fill_betweenx([mean_[0] - std_[0], mean_[0] + std_[0]], -50, 500, lw=0, alpha=0.5, color='grey')
        ax.axvline(mean_[1], ls=':', color='crimson')
        ax.fill_between([mean_[1] - std_[1], mean_[1] + std_[1]], -5000, 5000, lw=0, alpha=0.5, color='grey')

        # layout
        ax.set_xlim(-20, df.max().max() * 1.05), ax.set_ylim(df.idxmin().max() * 1.05, df.idxmax().min() * 1.05)
        ax.set_ylabel('Depth / µm'), ax.set_xlabel('dissolved $O_2$ / µmol/L')

        # include mean depth in title
        if core_select == 0 or not dcore_pen:
            pass
        else:
            ax.title.set_text('Average penetration depth for {} {}: {:.0f} ± {:.0f}µm'.format(grp_label, core_select,
                                                                                              mean_[0], std_[0]))
        if show is False:
            sns.despine()
            plt.close(fig)
        else:
            fig.canvas.draw()
    return fig
