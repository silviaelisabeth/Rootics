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
from PyQt5.QtGui import *
from PyQt5.QtWidgets import QMessageBox
import matplotlib.pylab as plt
import seaborn as sns
import numpy as np
import pandas as pd
import os
import re

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


def cropDF_H2S(ls_cropy, s, Core, dic_H2S, results):
    lab_sulfid = 'H2S total sulfide adjusted'
    if ls_cropy:
        # in case there was only 1 point selected -> extend the list to the other end
        if len(ls_cropy) == 1:
            sub = (dic_H2S[Core][s].index[0] - ls_cropy[0], dic_H2S[Core][s].index[-1] - ls_cropy[0])
            if np.abs(sub[0]) < np.abs(sub[1]):
                ls_cropy = [ls_cropy[0], dic_H2S[Core][s].index[-1]]
            else:
                ls_cropy = [dic_H2S[Core][s].index[0], ls_cropy[0]]

        # actually crop the depth profile to the area selected.
        # In case more than 2 points have been selected, choose the outer ones -> trim y-axis
        dcore_crop = dic_H2S[Core][s].loc[min(ls_cropy): max(ls_cropy)]
        # trim also total sulfide in case it is already possible
        if lab_sulfid in results.keys():
            op2 = int(Core.split(' ')[-1]) if isinstance(Core, str) else 'core ' + str(Core)
            lab = dbs._findCoreLabel(option1=Core, option2=op2, ls=results[lab_sulfid].keys())
            results[lab_sulfid][lab][s] = results[lab_sulfid][lab][s].loc[min(ls_cropy): max(ls_cropy)]
    else:
        dcore_crop = dic_H2S[Core][s]
        if lab_sulfid in results.keys():
            op2 = int(Core.split(' ')[-1]) if isinstance(Core, str) else 'core ' + str(Core)
            lab = dbs._findCoreLabel(option1=Core, option2=op2, ls=results[lab_sulfid].keys())
            results[lab_sulfid][lab][s] = results[lab_sulfid][lab][s]
    return dcore_crop, results, ls_cropy


def popData_H2S(dcore_crop, ls_out):
    ls_pop = [min(dcore_crop.index.to_numpy(), key=lambda x: abs(x - ls_out[p])) for p in range(len(ls_out))]
    # drop in case value is still there
    [dcore_crop.drop(p, inplace=True) for p in ls_pop if p in dcore_crop.index]
    return dcore_crop


def correlationInfo(dsheets_add, dic_sheets, en, key):
    df1, df2 = dsheets_add[key], dic_sheets[en + 1][key]
    if df1 is None:
        dfcorrel_sum = df2
    elif df2 is None:
        dfcorrel_sum = df1
    else:
        if len(df1) == 0 and len(df2) !=0:
            dfcorrel_sum = df2
        elif len(df1) != 0 and len(df2) == 0:
            dfcorrel_sum = df1
        else:
            if df1.merge(df2).drop_duplicates().shape == df1.drop_duplicates().shape is True:
                # dataframe with same shape -> check whether they have the same content
                if ((dsheets_add[key] == dic_sheets[en + 1][key]).all().all()) is True:
                    # dataframe matches - no need to do anything
                    dfcorrel_sum = dsheets_add['pH - H2S correlation']
                else:
                    df_mima = dsheets_add[key].ne(dic_sheets[en + 1][key], axis=1).dot(dsheets_add[key].columns)
                    for index, value in df_mima.items():
                        if value:
                            msgBox = QMessageBox()
                            msgBox.setIcon(QMessageBox.Information)
                            msgBox.setText("The excel sheets contain mismatching information for pH-H2S correlation. "
                                           "Please check column {} in line {}".format(value, index))
                            msgBox.setFont(QFont('Helvetica Neue', 11))
                            msgBox.setWindowTitle("Warning")
                            msgBox.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)

                            returnValue = msgBox.exec()
                            if returnValue == QMessageBox.Ok:
                                pass

                    dfcorrel_sum = dsheets_add['pH - H2S correlation']
            else:
                df_mima = dsheets_add[key].ne(dic_sheets[en + 1][key], axis=1).dot(dsheets_add[key].columns)
                for index, value in df_mima.items():
                    if value:
                        msgBox = QMessageBox()
                        msgBox.setIcon(QMessageBox.Information)
                        msgBox.setText("The excel sheets contain mismatching information for pH-H2S correlation.  "
                                       "Please check column {} in line {}".format(value, index))
                        msgBox.setFont(QFont('Helvetica Neue', 11))
                        msgBox.setWindowTitle("Warning")
                        msgBox.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)

                        returnValue = msgBox.exec()
                        if returnValue == QMessageBox.Ok:
                            pass
                dfcorrel_sum = dsheets_add['pH - H2S correlation']
    return dfcorrel_sum


def _calcTotalSulfide(tempK, sal_pmill, coreh2s, sampleS, pH_coreS, dH2S_core):
    coreh2s = int(coreh2s.split(' ')[1])

    # pK1 equation
    pK1 = -98.08 + (5765.4/tempK) + 15.04555*np.log(tempK) + -0.157*(sal_pmill**0.5) + 0.0135*sal_pmill
    K1 = 10**(-pK1)

    # get appropriate column of H2S
    for c in dH2S_core[coreh2s][sampleS].columns:
        if 'M' in c or 'mol' in c:
            col = c
    d_H2S = dH2S_core[coreh2s][sampleS][col] if col else dH2S_core[coreh2s][sampleS]

    # interpolate profiles to align data to the same index
    df_interpol = H2S_pH_interpolation(pd.DataFrame(pH_coreS), pd.DataFrame(d_H2S))

    # generate total sulfide DF
    df_interpol['total sulfide_µmol/L'] = df_interpol['H2S'] * (1 + (K1 / 10**(-df_interpol['pH'])))

    # zero correction -> everything that is negative is set to 0
    df_ = df_interpol['total sulfide_µmol/L'].copy()
    df_[df_ < 0] = 0
    df_interpol['total sulfide zero corr_µmol/L'] = df_
    return df_interpol


def H2S_pH_interpolation(pH_coreS, d_H2S):
    # new index
    depth_interpol = np.arange(max(pH_coreS.index[0], d_H2S.index[0]), min(pH_coreS.index[-1], d_H2S.index[-1]) + 1)
    df_combo = pd.DataFrame(np.nan, index=depth_interpol, columns=['pH', 'H2S'])

    # fill NaN values first with actual values, then by interpolation
    col_pH, col_H2S = pH_coreS.columns[0], d_H2S.columns[0]
    d_pH_crop = pH_coreS.loc[depth_interpol[0]:depth_interpol[-1]]
    d_H2S_crop = d_H2S.loc[depth_interpol[0]:depth_interpol[-1]]
    df_combo.loc[d_pH_crop.index, 'pH'] = d_pH_crop[col_pH].to_numpy()
    df_combo.loc[d_H2S_crop.index, 'H2S'] = d_H2S_crop[col_H2S].to_numpy()
    for col in df_combo:
        df_combo[col] = pd.to_numeric(df_combo[col], errors='coerce')

    # interpolate(method='linear')
    df_interpol = df_combo.interpolate(method='linear').dropna()
    return df_interpol


def swi_correctionpHII(results, pH_data):
    # add to results dictionary
    if 'H2S profile total sulfide' in results.keys():
        results['H2S profile total sulfide swi corrected pH'] = pH_data
    else:
        results['H2S profile swi corrected pH'] = pH_data
    return results


def updateH2Sscale(H2Strim_edit, scaleh2s, scale_, Core):
    # get pH range form LineEdit
    if H2Strim_edit.text():
        if '-' in H2Strim_edit.text():
            if len(H2Strim_edit.text().split('-')) > 1:
                # assume that negative numbers occur
                ls = re.findall(r"[-+]?(?:\d*\.\d+|\d+)", H2Strim_edit.text())
                scale = (float(ls[0]), float(ls[1]))
            else:
                scale = (float(H2Strim_edit.text().split('-')[0]),
                         float(H2Strim_edit.text().split('-')[1].strip()))
        elif ',' in H2Strim_edit.text():
            scale = (float(H2Strim_edit.text().split(',')[0]),
                     float(H2Strim_edit.text().split(',')[1].strip()))
        else:
            scale = (float(H2Strim_edit.text().split(' ')[0]),
                     float(H2Strim_edit.text().split(' ')[1].strip()))
    else:
        scale = None

    # if pH range was updated by the user -> update self.scale (prevent further down)
    if scale:
        if scale != scale_:
            scale_ = scale
        # update global variable
        scaleh2s[Core] = (round(scale_[0], 2), round(scale_[1], 2))
    return scaleh2s, scale_


def calc_total_sulfide(results, dH2S_core, tempC_edit, sal_edit, convC2K):
    # convert parameter
    tempK, sal_pmill = float(tempC_edit.text()) + convC2K, float(sal_edit.text())
    df_corr = results['pH - H2S correlation']

    # get all cores of H2S profiles
    ls_coreH2S = list()
    [ls_coreH2S.append(l) for l in df_corr['H2S code'].to_numpy() if l not in ls_coreH2S]

    # calculate total sulfide
    dsulfide, n = dict(), 0
    for em, coreh2s in enumerate(ls_coreH2S):
        # get all samples of the specific core
        samplesh2S = df_corr[df_corr['H2S code'] == coreh2s]['H2S Nr'].to_numpy()
        dsulfideS = dict()
        for en, s in enumerate(samplesh2S):
            # get the original pH profile
            pH_coreS = getOriginal_pH(corepH=df_corr.loc[n]['pH code'], sample=df_corr.loc[n]['pH Nr'], results=results)

            # calculate total sulfide for specific core and sample according to associated pH profile
            df = _calcTotalSulfide(coreh2s=coreh2s, sampleS=s, tempK=tempK, sal_pmill=sal_pmill, pH_coreS=pH_coreS,
                                   dH2S_core=dH2S_core)
            dsulfideS[s] = df
            n += 1
        dsulfide[coreh2s] = dsulfideS

    return dsulfide, results


def select_h2sDF_core(core, results, dic_H2S, rawPlot, main=False, reset=False):
    if main is True:
        if 'H2S profile total sulfide' in results:
            dic_data = results['H2S profile total sulfide'] if reset is True else results['H2S total sulfide adjusted']
        else:
            dic_data = results['H2S profile interim'] if reset is True else results['H2S adjusted']
    else:
        dic_data = results['H2S profile interim'] if reset is True else results['H2S adjusted']

    if rawPlot is True:
        if isinstance(core, str):
            lab = dbs._findCoreLabel(option1=core, option2=int(core.split(' ')[-1]), ls=dic_data.keys())
        else:
            lab = dbs._findCoreLabel(option1=core, option2='core ' + str(core), ls=dic_data.keys())
        df = dic_data[lab]
    else:
        if isinstance(core, str):
            lab = dbs._findCoreLabel(option1=core, option2=int(core.split(' ')[-1]), ls=dic_H2S.keys())
        else:
            lab = dbs._findCoreLabel(option1=core, option2='core ' + str(core), ls=dic_H2S.keys())
        df = dic_H2S[lab]
    return dic_data, df


def identify_col2plot_h2s(ls_lookup):
    col_plot = [c for c in ls_lookup if 'µM' in c]
    col_plot = [c for c in ls_lookup if 'H2S' in c][0] if len(col_plot) == 0 else col_plot[0]
    return col_plot


# --------------------------------------------------------------------------------------------------------------------
def load_H2Sdata(data, dcol_label, grp_label, results):
    # check whether we have a data file
    loadData = dbs.check4LoadingData(stringFile=data[1:-1])

    # raw measurement file pre-processed and saved per default as rawData file
    if loadData is True:
        dsheets, dignore = dbs._loadGlobData(file_str=data, dcol_label=dcol_label)
        for k in dignore.keys():
            if 'H2S' in dignore[k].keys():
                l = k

        # pre-check whether pH_all in sheet names
        sheet_select = dbs.sheetname_check(dsheets, para='H2S')
        checked = dbs.checkDatavsPara(sheet_select, par='H2S')
        if checked is True:
            # prepare file depending on the type
            ddata = dsheets[sheet_select].set_index('Nr')

            # remove excluded profiles
            ddata_update = dbs._excludeProfiles(analyt='H2S', dignore=dignore[l], ddata=ddata)

            if grp_label is None:
                grp_label = ddata_update.columns[0]

            # list all available cores for pH sheet
            ls_core = list(dict.fromkeys(ddata_update[ddata_update.columns[0]].to_numpy()))

            # import all measurements for given parameter
            [dH2S_core, _, ls_colname] = dbs.load_measurements(dsheets=ddata_update, ls_core=ls_core, para=sheet_select)
            label = 'H2S adjusted'
            results[label] = dH2S_core

            # separate storage of raw data
            results['H2S profile raw data'] = dict()
            for c in results[label].keys():
                ddic = dict()
                for i in results[label][c].keys():
                    ddic[i] = pd.DataFrame(np.array(results[label][c][i]), index=results[label][c][i].index,
                                           columns=results[label][c][i].columns)
                results['H2S profile raw data'][c] = ddic
            return checked, ls_core, results, ls_colname, dH2S_core, grp_label
        else:
            return False, None, results, None, None, grp_label
    else:
        return False, None, results, None, None, grp_label


def load_additionalInfo_h2s(data):
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
        df_meta, df_correl = None, None
        for c in dic_sheets_.keys():
            if 'Meta' in c or 'meta' in c:
                df_meta = dic_sheets_[c]
            if 'Corr' in c or 'corr' in c:
                df_correl = dic_sheets_[c]
        dic_sheets[f[0]] = dict({'meta data': df_meta, 'pH - H2S correlation': df_correl})

    # merge and double check duplicates (especially for pH-H2S correlation)
    dsheets_add = dic_sheets[0]
    for en in range(len(ls_file) - 1):
        # get meta data info
        if 'meta data' in dic_sheets[en + 1].keys():
            dfmeta_sum = pd.concat([dsheets_add['meta data'], dic_sheets[en + 1]['meta data']], axis=0)
        else:
            dfmeta_sum = dsheets_add['meta data']

        # get correlation info
        if 'pH - H2S correlation' in dic_sheets[en + 1].keys():
            key = 'pH - H2S correlation'
            dfcorrel_sum = correlationInfo(en=en, key=key, dsheets_add=dsheets_add, dic_sheets=dic_sheets)
        else:
            dfcorrel_sum = dsheets_add['pH - H2S correlation']
        dsheets_add = dict({'meta data': dfmeta_sum, 'pH - H2S correlation': dfcorrel_sum})
    return dsheets_add


def getOriginal_pH(results, corepH, sample):
    if 'pH swi depth' in results.keys():
        corepH1 = dbs._findCoreLabel(option1=corepH, option2=int(corepH.split(' ')[1]),
                                     ls=results['pH swi depth'].keys())
        if corepH1:
            pass
        else:
            corepH1 = dbs._findCoreLabel(option1=corepH, option2=int(corepH.split(' ')[1]), ls=results['pH adjusted'])
        xold = results['pH adjusted'][corepH1][sample].index
        pH_coreS = pd.DataFrame(results['pH adjusted'][corepH1][sample]['pH'])
        pH_coreS.index = xold
    else:
        corepH = dbs._findCoreLabel(option1=corepH, option2=int(corepH.split(' ')[1]), ls=results['pH adjusted'])
        if corepH:
            if corepH not in results['pH adjusted'].keys():
                msgBox = QMessageBox()
                msgBox.setIcon(QMessageBox.Warning)
                msgBox.setText("Information missing how to correlate pH and H2S sensor profiles. The requested pH"
                               "profile {} was not found".format(corepH))
                msgBox.setFont(QFont('Helvetica Neue', 11))
                msgBox.setWindowTitle("Warning")
                msgBox.setStandardButtons(QMessageBox.Ok)

                returnValue = msgBox.exec()
                if returnValue == QMessageBox.Ok:
                    pass
            else:
                if sample not in results['pH adjusted'][corepH].keys():
                    msgBox = QMessageBox()
                    msgBox.setIcon(QMessageBox.Warning)
                    msgBox.setText("Information missing how to correlate pH and H2S sensor profiles. The requested "
                                   "pH profile {} was not found".format(sample))
                    msgBox.setFont(QFont('Helvetica Neue', 11))
                    msgBox.setWindowTitle("Warning")
                    msgBox.setStandardButtons(QMessageBox.Ok)

                    returnValue = msgBox.exec()
                    if returnValue == QMessageBox.Ok:
                        pass
                else:
                    pH_coreS = results['pH adjusted'][corepH][sample]['pH']
        else:
            pH_coreS = None
    return pH_coreS


def save_H2Sdata(save_path, save_para, data, ls_allData, dout):
    # make a project folder for the specific analyte if it doesn't exist
    save_path = save_path + '/H2S_project/'
    if not os.path.exists(save_path):
        os.makedirs(save_path)

    ls_saveData = list()
    [ls_saveData.append(i) for i in save_para.split(',') if 'fig' not in i]
    if len(ls_saveData) > 0:
        # all keys that shall be removed
        ls_removeKey = list()
        [ls_removeKey.append(i) for i in ls_allData if i not in ls_saveData]
        if 'fit_mV' in ls_removeKey:
            ls_removeKey.append('derivative_mV')

        # delete a keys not in that list regardless of whether it is in the dictionary
        [dout.pop(i, None) for i in ls_removeKey]

        # save to excel sheets
        dbs.save_rawExcel(dout=dout, file=data, savePath=save_path)


def save_H2Sfigure(save_para, save_path, ls_core, grp_label, dunit, dobj_hidH2S, fs_, results):
    ls_saveFig = list()
    [ls_saveFig.append(i) for i in save_para.split(',') if 'fig' in i]
    if len(ls_saveFig) > 0:
        save_path = save_path + '/Graphs/'
        # make folder "Graphs" if it doesn't exist
        if not os.path.exists(save_path):
            os.makedirs(save_path)

        # make a project folder for the specific analyte if it doesn't exist
        save_path = save_path + 'H2S_project/'
        if not os.path.exists(save_path):
            os.makedirs(save_path)

        # generate images of all all samples (don't plot them)
        [dfigRaw, dfigBase,
         dfigPen] = fig4saving_H2S(ls_core=ls_core, draw=results['H2S profile raw data'], dadj=results['H2S adjusted'],
                                   grp_label=grp_label, dunit=dunit, fs_=fs_, dobj_hidH2S=dobj_hidH2S,
                                   dsulFront=results['H2S sulfidic front'])

        # Depth profiles
        if 'fig raw' in ls_saveFig:
            save_figraw(save_path=save_path, dfigRaw=dfigRaw)
        if 'fig adjusted' in ls_saveFig:
            save_figdepth(save_path=save_path, dfigBase=dfigBase)
        # Penetration depth
        if 'fig penetration' in ls_saveFig:
            if dfigPen:
                save_figPen(save_path=save_path, dfigPen=dfigPen)


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


def save_figPen(save_path, dfigPen):
    # find the actual running number
    save_folder = dbs._actualFolderName(savePath=save_path, cfolder='SulfidicFront', rlabel='run')
    if not os.path.exists(save_folder):
        os.makedirs(save_folder)

    for f in dfigPen.keys():
        for t in ls_figtype:
            name = save_folder + 'SulfidicFront_core-{}.'.format(f) + t
            dfigPen[f].savefig(name, bbox_inches='tight', pad_inches=0.1, dpi=dpi)


def fig4saving_H2S(ls_core, draw, dadj, grp_label, dunit, fs_, dobj_hidH2S, dsulFront=None):
    dfigRaw, dfigBase, dfigPen = dict(), dict(), dict()
    # raw data
    for c in ls_core:
        dfigRaw[c] = plot_H2SProfile(data_H2S=draw, core=c, ls_core=ls_core, scale=None, col='H2S_uM', dobj_hidH2S=None,
                                     ls='-.', show=False, trimexact=False, grp_label=grp_label, dunit=dunit, fs_=fs_)[0]
    # adjusted data
    for c in ls_core:
        cC = dbs._findCoreLabel(option1=c, option2='core ' + str(c), ls=dadj)
        s = list(dadj[cC].keys())
        dfigBase[c] = plot_H2SProfile(data_H2S=dadj, core=c, ls_core=ls_core, scale=None, col=dadj[cC][s[0]].columns[-1],
                                      ls='-', show=False, dobj_hidH2S=dobj_hidH2S, trimexact=False, grp_label=grp_label,
                                      dunit=dunit, fs_=fs_)[0]

    # sulfidic front in adjusted profile
    if dsulFront:
        for c in ls_core:
            cC = dbs._findCoreLabel(option1=c, option2='core ' + str(c), ls=dadj)
            s = list(dadj[cC].keys())
            df, ax, _ = plot_H2SProfile(data_H2S=dadj, core=c, ls_core=ls_core, scale=None, grp_label=grp_label,
                                        col=dadj[cC][s[0]].columns[-1], ls='-', show=False, dobj_hidH2S=dobj_hidH2S,
                                        trimexact=False, dunit=dunit, fs_=fs_)
            cC = dbs._findCoreLabel(option1=c, option2='core ' + str(c), ls=dsulFront.keys())
            ax.axhline(dsulFront[cC].loc['mean'].values[0], color='crimson', lw=0.75, ls=':')
            ax.fill_betweenx([dsulFront[cC].loc['mean'].values[0] - dsulFront[cC].loc['std'].values[0],
                              dsulFront[cC].loc['mean'].values[0] + dsulFront[cC].loc['std'].values[0]],
                             ax.get_xlim()[0], ax.get_xlim()[1], lw=0, alpha=0.5, color='grey')
            dfigPen[c] = df

    return dfigRaw, dfigBase, dfigPen


# --------------------------------------------------------------------------------------------------------------------
def plot_H2SProfile(data_H2S, core, ls_core, col, grp_label, dunit, dobj_hidH2S, fs_, ls='-.', scale=None, fig=None,
                    ax=None, show=True, trimexact=False):
    plt.ioff()
    lines = list()
    # identify closest value in list and the plotted analyte
    core_select = dbs.closest_core(ls_core=ls_core, core=core)
    if core_select in data_H2S.keys():
        s0 = list(data_H2S[core_select].keys())[0]
        labCore = core_select
    else:
        s0 = list(data_H2S['core ' + str(core_select)].keys())[0]
        labCore = 'core ' + str(core_select)

    para = 'total sulfide zero corr_µmol/L' if 'total sulfide zero corr_µmol/L' in data_H2S[labCore][s0].columns else col
    unit = dunit['total sulfide'] if 'total sulfide' in dunit.keys() else dunit['H2S']

    # initialize figure
    if ax is None:
        fig, ax = plt.subplots(figsize=(3, 4), linewidth=0)
    else:
        ax.cla()
    ax.set_xlabel('{} / {}'.format(para.split('zero')[0].split('_')[0], unit), fontsize=fs_*0.9)
    ax.set_ylabel('Depth / µm', fontsize=fs_*0.9)
    ax.invert_yaxis()
    if show is False:
        [ax.spines[axis].set_linewidth(0.5) for axis in ['top', 'bottom', 'left', 'right']]
        ax.tick_params(labelsize=fs_ * 0.9)

    if core_select != 0:
        ax.title.set_text('{} depth profile for {} {}'.format(para.split('zero')[0].split('_')[0], grp_label,
                                                              core_select))
        ax.axhline(0, lw=.5, color='k')

        # additional warning
        if len(data_H2S[labCore].keys()) >= len(ls_col):
            msgBox = QMessageBox()
            msgBox.setIcon(QMessageBox.Warning)
            msgBox.setText("Number of samples exceeds number of available colors to visualize in the same plot. "
                           "Please update ls_col")
            msgBox.setFont(QFont('Helvetica Neue', 11))
            msgBox.setWindowTitle("Warning")
            msgBox.setStandardButtons(QMessageBox.Ok)

        for en, nr in enumerate(data_H2S[labCore].keys()):
            lab = int(labCore.split(' ')[-1]) if isinstance(labCore, str) else labCore
            if dobj_hidH2S and lab in dobj_hidH2S.keys():
                alpha_ = .0 if 'sample ' + str(nr) in dobj_hidH2S[lab] else .6
            else:
                alpha_ = .6

            if para not in data_H2S[labCore][nr].columns:
                para = data_H2S[labCore][nr].filter(like='H2S').columns[0]
            df = data_H2S[labCore][nr][para].dropna()
            mark = '.' if ls == '-.' else None
            lw = .75 if ls == '-.' else 1.5
            if en <= len(ls_col):
                line, = ax.plot(df, df.index, lw=lw, ls=ls, marker=mark, color=ls_col[en], alpha=alpha_, pickradius=5,
                                label='sample ' + str(nr))
                lines.append(line)
        leg = ax.legend(frameon=True, fancybox=True, fontsize=fs_ * 0.8)

        # ------------------------------------------------------------------
        # combine legend
        lined = dict()
        for legline, origline in zip(leg.get_lines(), lines):
            legline.set_picker(5.)
            lined[legline] = origline

        # picker - hid curves in plot
        def onpick(event):
            ls_hid = dobj_hidH2S[lab] if lab in dobj_hidH2S.keys() else list()
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
                dobj_hidH2S[core_select] = ls_hid
            fig.canvas.draw()

        # Call click func
        fig.canvas.mpl_connect('pick_event', onpick)

    # update layout
    if scale:
        if trimexact is True:
            min_ = -1 * scale[1] / 10 if scale[0] == 0 else scale[0]
            scale_max = scale[1]
        else:
            min_ = -1 * scale[1] / 100 if scale[0] == 0 else scale[0] * 0.95
            scale_max = scale[1] * 1.05
        scale_min = min_ if min_ < -0.15 else -0.15
        ax.set_xlim(scale_min, scale_max)
        fig.subplots_adjust(bottom=0.2, right=0.95, top=0.85, left=0.15)
    else:
        x_ = ax.get_xlim()
        if x_[1] > 10:
            ax.set_xlim(-2, 10) if x_[0] < -2 else ax.set_xlim(x_[0], 10)
        else:
            ax.set_xlim(-2, x_[1]) if x_[0] < -2 else ax.set_xlim(x_[0], x_[1])
        plt.tight_layout(pad=0.5)
    if show is False:
        sns.despine()
        plt.close(fig)
    else:
        fig.canvas.draw()
    return fig, ax, dobj_hidH2S


def plot_H2SProfile_sample(data_H2S, core, sample, col, grp_label, dunit, dobj_hidH2S, fs_, ls='-.', scale=None,
                           fig=None, ax=None, show=True, trimexact=False):
    plt.ioff()
    para = 'total sulfide zero corr_µmol/L' if 'total sulfide zero corr_µmol/L' in data_H2S[sample].columns else col
    unit = dunit['total sulfide'] if 'total sulfide' in dunit.keys() else dunit['H2S']

    # initialize figure
    if ax is None:
        fig, ax = plt.subplots(figsize=(3, 4), linewidth=0)
    else:
        if len(fig.axes[0].lines) >= len(data_H2S[core].keys()):
            fig.axes[0].lines[sample].remove()

    ax.set_xlabel('{} / {}'.format(para.split('zero')[0].split('_')[0], unit), fontsize=fs_*0.9)
    ax.set_ylabel('Depth / µm', fontsize=fs_*0.9)

    if show is False:
        [ax.spines[axis].set_linewidth(0.5) for axis in ['top', 'bottom', 'left', 'right']]
        ax.tick_params(labelsize=fs_ * 0.9)

    if core != 0:
        ax.title.set_text('{} depth profile for {} {}'.format(para.split('zero')[0].split('_')[0], grp_label, core))
        ax.axhline(0, lw=.5, color='k')

        lab = int(core.split(' ')[-1]) if isinstance(core, str) else core
        if dobj_hidH2S and lab in dobj_hidH2S.keys():
            alpha_ = .0 if 'sample ' + str(sample) in dobj_hidH2S[lab] else .6
        else:
            alpha_ = .6

        if para not in data_H2S[sample].columns:
            para = data_H2S[sample].filter(like='H2S').columns[0]
        df = data_H2S[sample][para].dropna()

        mark = '.' if ls == '-.' else None
        lw = .75 if ls == '-.' else 1.5
        if sample <= len(ls_col):
            ax.plot(df, df.index, lw=lw, ls=ls, marker=mark, ms=4, color=ls_col[sample-1], alpha=alpha_, pickradius=5,
                    label='sample ' + str(sample))

    # update layout
    if scale:
        if trimexact is True:
            min_ = -1 * scale[1] / 10 if scale[0] == 0 else scale[0]
            scale_max = scale[1]
        else:
            min_ = -1 * scale[1] / 100 if scale[0] == 0 else scale[0] * 0.95
            scale_max = scale[1] * 1.05
        scale_min = min_ if min_ < -0.15 else -0.15
        ax.set_xlim(scale_min, scale_max)
        fig.subplots_adjust(bottom=0.2, right=0.95, top=0.85, left=0.15)
    else:
        plt.tight_layout(pad=0.5)

    if show is False:
        sns.despine()
        plt.close(fig)
    else:
        fig.canvas.draw()
    return fig, ax, dobj_hidH2S


def plot_adjustH2S(core, sample, dfCore, results, col, pH, pH_sample, pH_core, grp_label, ls, fig, ax, ax1=None,
                   scale=None, reset=False):
    # initialize first plot with first core and sample
    fig, ax1, scale = GUI_adjustDepthH2S(core=core, nr=sample, dfCore=dfCore, col=col, scale=scale, fig=fig, ax=ax,
                                         ax1=ax1, pH=pH, pHnr=pH_sample, pH_core=pH_core, grp_label=grp_label, ls=ls,
                                         results=results, reset=reset)
    fig.canvas.draw()
    return fig, ax1, scale


def plot_H2SUpdate(core, nr, df_H2Ss, ddcore, scale, pH, pH_core, pHnr, results, grp_label, fig, ax, ax1=None,
                   trimexact=False):
    # clear coordinate system but keep the labels
    ax.cla()
    if pH:
        ax1.cla()
        ax1.set_xlabel('pH value')
    else:
        ax1 = None
    ax.title.set_text('H2S profile for {} {} - sample {}'.format(grp_label, core, nr))
    ax.set_xlabel('H2S / µmol/L'), ax.set_ylabel('Depth / µm')

    # plotting part
    ax.axhline(0, lw=.5, color='k')
    for en in enumerate(ddcore.keys()):
        if en[1] == nr:
            pos = en[0]

    # identify correct column to plot
    col2 = identify_col2plot_h2s(ls_lookup=df_H2Ss.columns)
    ax.plot(df_H2Ss[col2], df_H2Ss.index, lw=0.75, ls='-.', marker='.', ms=4, color=ls_col[pos], alpha=0.75)

    if pH:
        if 'pH swi depth' in results.keys():
            if core in results['pH swi depth']:
                if isinstance(results['pH swi depth'][core], float):
                    corr = results['pH swi depth'][core]
                else:
                    corr = results['pH swi depth'][core]['Depth (µm)']
            else:
                corr = 0
        else:
            corr = 0
        # correlated pH sample Nr.
        df_pH = results['pH profile raw data']
        if isinstance(pH_core, str):
            pH_core = dbs._findCoreLabel(option1=pH_core, option2=int(pH_core.split(' ')[1]), ls=df_pH.keys())
        ax1.plot(df_pH[pH_core][pHnr]['pH'], df_pH[pH_core][pHnr].index + corr, lw=0.75, ls='--', color='#971EB3',
                 alpha=0.75)

    # general layout
    if scale:
        scale_min = scale[0] if trimexact is True else -1 * scale[1] / 10 if scale[0] == 0 else scale[0] * 0.95
        scale_max = scale[1] if trimexact is True else scale[1] * 1.015
        ax.set_xlim(scale_min, scale_max)
    else:
        scale = ax.get_xlim()
    ax.invert_yaxis()
    sns.despine()
    if pH:
        ax.spines['top'].set_visible(True)
    plt.tight_layout(pad=.5)
    fig.canvas.draw()
    return fig, ax1, scale


def GUI_adjustDepthH2S(core, nr, grp_label, dfCore, col, results, ls, pH=None, pHnr=None, pH_core=None, fig=None,
                       ax=None, ax1=None, show=True, scale=None, reset=False):
    plt.ioff()
    unit = col.split('_')[1]

    # initialize figure plot
    if ax is None:
        fig, ax = plt.subplots(figsize=(5, 3), linewidth=0)
    else:
        ax.cla()
    if pH:
        if ax1 is None:
            ax1 = ax.twiny()
        else:
            ax1.cla()
        ax1.set_xlabel('pH value')
    else:
        ax1 = None

    if core != 0:
        ax.title.set_text('H2S profile for {} {} - sample {}'.format(grp_label, core, nr))
        ax.set_ylabel('Depth / µm'), ax.set_xlabel('H2S / {}'.format(unit))

    # plotting part
    ax.axhline(0, lw=.5, color='k')

    # position in sample list to get the right color
    pos = 0
    for en in enumerate(dfCore.keys()):
        if en[1] == nr:
            pos = en[0]

    # identify the correct column to plot
    col = identify_col2plot_h2s(ls_lookup=dfCore[nr].keys())
    mark = '.' if ls == '-.' else None
    ms = 4 if ls == '-.' else 2
    if ls == '-.':
        lw = 0.15 if reset is True else 0.75
    else:
        lw = 1.5
    ax.plot(dfCore[nr][col], dfCore[nr].index, lw=lw, ls=ls, marker=mark, ms=ms, color=ls_col[pos], alpha=0.75)

    if pH:
        # correlated pH sample Nr. - use the corrected profiles
        if isinstance(pH_core, str):
            pH_core = dbs._findCoreLabel(option1=pH_core, option2=int(pH_core.split(' ')[1]),
                                         ls=results['pH adjusted'].keys())
        if pH_core not in results['pH adjusted'].keys():
            msgBox = QMessageBox()
            msgBox.setIcon(QMessageBox.Information)
            msgBox.setText("Selected pH group not found: {} in {}".format(pH_core, list(results['pH adjusted'].keys())))
            msgBox.setFont(QFont('Helvetica Neue', 11))
            msgBox.setWindowTitle("Warning")
            msgBox.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)

            returnValue = msgBox.exec()
            if returnValue == QMessageBox.Ok:
                pass
        else:
            if pHnr not in results['pH adjusted'][pH_core].keys():
                msgBox = QMessageBox()
                msgBox.setIcon(QMessageBox.Information)
                msgBox.setText("Selected pH group not found: {} in {}".format(pHnr,
                                                                              list(results['pH adjusted'][pH_core].keys())))
                msgBox.setFont(QFont('Helvetica Neue', 11))
                msgBox.setWindowTitle("Warning")
                msgBox.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)

                returnValue = msgBox.exec()
                if returnValue == QMessageBox.Ok:
                    pass
            else:
                ax1.plot(results['pH adjusted'][pH_core][pHnr]['pH'], results['pH adjusted'][pH_core][pHnr].index,
                         lw=0.75, ls='--', color='#971EB3', alpha=0.75)

    # general layout
    if scale:
        scale_min = -1 * scale[1] / 10 if scale[0] == 0 else scale[0] * 0.95
        ax.set_xlim(scale_min, scale[1] * 1.015)
    else:
        scale = ax.get_xlim()
    ax.invert_yaxis()
    sns.despine()
    ax.spines['top'].set_visible(True) if pH else ax.spines['top'].set_visible(False)
    fig.tight_layout(pad=0.5)

    # final adjustment of layout
    plt.close(fig) if show is False else fig.canvas.draw()
    return fig, ax1, scale


def plot_sulfidicFront(df_Front, core_select, grp_label, fig, ax):
    # add average + std to the plot
    if core_select != 0:
        option2 = int(core_select.split(' ')[1]) if isinstance(core_select, str) else 'core ' + str(core_select)
        core_select = dbs._findCoreLabel(option1=core_select, option2=option2, ls=df_Front.keys())

        # statistics
        mean_, std_ = df_Front[core_select].loc['mean'].to_numpy()[0], df_Front[core_select].loc['std'].to_numpy()[0]

        # indicate penetration depth mean + std according to visible curves
        ax.axhline(mean_, ls=':', color='crimson')
        ax.fill_betweenx([mean_ - std_, mean_ + std_], -50, 500, lw=0, alpha=0.5, color='grey')

        # include mean depth in title
        if core_select == 0:
            pass
        else:
            ax.title.set_text('Average sulfidic front for {} {}: {:.0f} ± {:.0f}µm'.format(grp_label, core_select,
                                                                                           mean_, std_))
        # adjust xrange
        x_need = ax.get_xlim()
        if x_need[1] > 10:
            ax.set_xlim(x_need[0], 10)

        # layout
        fig.canvas.draw()