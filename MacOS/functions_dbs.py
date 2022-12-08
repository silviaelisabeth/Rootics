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

from PyQt5 import QtCore, QtWidgets
from PyQt5 import QtGui
from PyQt5.QtCore import Qt, QRegExp
from PyQt5.QtGui import *
from PyQt5.QtWidgets import QMessageBox
import matplotlib
import matplotlib.pylab as plt
import seaborn as sns
import numpy as np
import pandas as pd
from mergedeep import merge
from lmfit import Model
from scipy import stats
from datetime import datetime
from os import walk

# global parameter
sns.set_context('paper'), sns.set_style('ticks')

# color list for samples: grey, orange, petrol, green, yellow, light grey, blue
ls_col = list(['#4c5558', '#eb9032', '#21a0a8', '#9ec759', '#f9d220', '#96a6ab', '#1B08AA', '#3D14E1', '#D20D41',
               '#E87392', '#40A64A'])
dcolor = dict({'O2': '#4c5558', 'pH': '#eb9032', 'H2S': '#9ec759', 'EP': '#1B08AA'})

# global variables
coords = dict()


# --------------------------------------------------------------------------------------------------------------------
def checkDatavsPara(sheet_select, par):
    checked = False
    try:
        if sheet_select is None:
            msgBox = QMessageBox()
            msgBox.setIcon(QMessageBox.Information)
            msgBox.setText("No measurement data found for selected parameter {}.  Please,  provide the raw measurement "
                           "file.".format(par))
            msgBox.setFont(QFont('Helvetica Neue', 11))
            msgBox.setWindowTitle("Warning")
            msgBox.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
            msgBox.exec()
        else:
            checked = True
    except:
        msgBox = QMessageBox()
        msgBox.setIcon(QMessageBox.Information)
        msgBox.setText("No measurement data found for selected parameter.  Please,  provide the raw measurement "
                       "file.")
        msgBox.setFont(QFont('Helvetica Neue', 11))
        msgBox.setWindowTitle("Warning")
        msgBox.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
        msgBox.exec()
    return checked


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


def _excludeProfiles(analyt, dignore, ddata):
    # get the deployment (ID) and code information
    hide_nr = dignore[analyt]['deployment'].to_numpy()
    hide_code = dignore[analyt]['code'].to_numpy()

    l = 0
    for en, i in enumerate(list(dict.fromkeys(list(ddata.index)))):
        if i in hide_nr:
            # position of i in hide_nr
            for em, j in enumerate(hide_nr):
                if j == i:
                    k = em
            # double-check code
            chid = _findCoreLabel(option1=hide_code[k], option2=int(hide_code[k].split(' ')[1]),
                                  ls=ddata.loc[i, ddata.columns[0]].to_numpy())
            if chid not in list(dict.fromkeys(list(ddata.loc[i, ddata.columns[0]]))):
                if l == 0:
                    ddata_update = ddata.loc[i]
                else:
                    ddata_update2 = ddata.loc[i]
                    ddata_update = pd.concat([ddata_update, ddata_update2], axis=0)
            l += 1
        else:
            if l == 0:
                ddata_update = ddata.loc[i]
            else:
                ddata_update2 = ddata.loc[i]
                ddata_update = pd.concat([ddata_update, ddata_update2], axis=0)
            l += 1
    return ddata_update


def find_column2plot(unit, df):
    if isinstance(df, pd.Series):
        ls_cols = [l[1] for l in pd.DataFrame(df).columns]
    else:
        ls_cols = df.columns

    if unit == 'µmol/L':
        # test also µmol/l
        col_plot = [c for c in ls_cols if unit in c or 'µmol/l' in c][0]
    elif unit == 'µmol/l':
        # test also µmol/L
        col_plot = [c for c in ls_cols if unit in c or 'µmol/L' in c][0]
    else:
        col_plot = [c for c in ls_cols if unit in c][0]
    return col_plot


# -------------------------------------------------------------------------------------------------------
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
    addstr = now + '_'
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


def load_av_profile(ddata):
    # get columns and index information
    cols = ddata.loc[0].to_numpy()
    ind_label = ddata.loc[1].to_numpy()[0]

    # crop data to relevant range
    ddata = ddata.loc[2:].set_index(ddata.columns[0])

    # set index and columns label
    ddata.index.name = 'Depth' if isinstance(ind_label, type(np.nan)) else ind_label
    ls1 = [val for val in [i[1] for i in enumerate(ddata.columns) if i[0]%2!=1] for _ in (0, 1)]
    ls1_ = list()
    for i in ls1:
        if isinstance(i, str):
            ls1_.append(int(i.split(' ')[-1]))
        else:
            ls1_.append(i)
    ls2 = int(len(ddata.columns)/2) * [cols[1:3][0], cols[1:3][1]]
    ddata.columns = pd.MultiIndex.from_tuples(list(zip(*[ls1_, ls2])))

    # split to dictionary
    dcore_para = dict()
    for k in ddata.columns.levels[0]:
        dcore_para[k] = ddata[k].dropna()

    return dcore_para


def loadMeas4GUI(file):
    # load sheets from excel file
    df_excel = pd.read_excel(file, sheet_name=None)

    # identify sensors used
    dfsens = df_excel['Sensors'][['Type', 'Unit']]

    # check requirements for meta data and correlation (where applicable)
    col = precheckMeta(ls_cols=df_excel.keys())

    # split full dataframe with all profiles into individual samples belonging to certain groups
    dprof = loadProfile(dfsens=dfsens, dfprof=df_excel['Profiles'])

    # additional prep to fit it to the previous version
    dprof = prepAnalytes(dprof=dprof)

    # split full dataset into individual profiles and label them according to sample ID and group (e.g. "core")
    dprofiles = splitIntoSamples(dprof=dprof, df_meta=df_excel[col])

    return dprofiles


def check4LoadingData(stringFile):
    loadData = False
    try:
        if len(stringFile) == 0:
            msgBox = QMessageBox()
            msgBox.setIcon(QMessageBox.Information)
            msgBox.setText("No measurement data found for selected parameter.  Please,  provide the raw measurement "
                           "file.")
            msgBox.setFont(QFont('Helvetica Neue', 11))
            msgBox.setWindowTitle("Warning")
            msgBox.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
            msgBox.exec()
        else:
            loadData = True
    except:
        msgBox = QMessageBox()
        msgBox.setIcon(QMessageBox.Information)
        msgBox.setText("No measurement data found for selected parameter.  Please,  provide the raw measurement "
                       "file.")
        msgBox.setFont(QFont('Helvetica Neue', 11))
        msgBox.setWindowTitle("Warning")
        msgBox.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
        msgBox.exec()
    return loadData


def _loadGlobData(file_str, dcol_label):
    # convert potential str-list into list of strings
    if '[' in file_str:
        ls_file = [i.strip()[1:-1] for i in file_str[1:-1].split(',')]
    else:
        ls_file = list(file_str)

    # get meta data file
    dmeta_ = dict(map(lambda f: (f[0], pd.read_excel(f[1], sheet_name=None)), enumerate(ls_file)))
    dignore = dict()
    for f in dmeta_.keys():
        if 'Metadata' in dmeta_[f].keys():
            dfmeta = dmeta_[f]['Metadata']
        elif 'metadata' in dmeta_[f].keys():
            dfmeta = dmeta_[f]['metadata']
        else:
            print('warning - no meta file found!')
            dfmeta = None

        # get the profiles that shall be excluded
        dignore[f] = dict(map(lambda p: (p, dfmeta[dfmeta[p].isnull()]), dfmeta.columns[2:]))

    # load excel sheet with all measurements
    ls_dsheets = dict(map(lambda f: (f[0], loadMeas4GUI(file=f[1])), enumerate(ls_file)))

    dsheets = ls_dsheets[0]
    for en in range(len(ls_file)-1):
        dsheets = merge(dsheets, ls_dsheets[en+1])

    # get the information how the columns for depth, concentration, and signal are labeled for each analyte
    if bool(dcol_label) is False:
        for a in dsheets.keys():
            dcol_label[a] = list(dsheets[a].columns[2:])
    return dsheets, dignore


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
            if isinstance(results['O2 profile'][c], dict):
                dic[c] = pd.concat(results['O2 profile'][c], axis=1)
            else:
                dic[c] = results['O2 profile'][c]
        dout['O2 profile'] = pd.concat(dic, axis=1)

    # handle penetration depth - results['penetration depth']
    if 'O2 penetration depth' in results.keys():
        df = dict(map(lambda k: (k, pd.DataFrame(dpenStat[k])), dpenStat.keys()))
        ddf = pd.concat(df, axis=1)
        col_new = ddf.columns.levels[0]
        ddf.columns = col_new
        dout['penetration depth'] = ddf

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
    savename = _actualFileName(savePath=savePath, file=file, clabel='output', rlabel='run')

    # actually saving DataFrame to excel
    writer = pd.ExcelWriter(savename)
    for key in dout.keys():
        dout[key].to_excel(writer, sheet_name=key)
    writer.save()
    writer.close()


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
    if isinstance(grp_label, type(None)):
        lsnew = ls
    else:
        for p in ls:
            if grp_label in p:
                lsnew.append(p.split(sep)[1])
            else:
                lsnew.append(p)
    return lsnew


def _findCoreLabel(option1, option2, ls):
    if option1 in ls:
        labCore = option1
    elif option2 in ls:
        labCore = option2
    else:
        labCore = None
    return labCore


def find_col2plot(unit, df):
    if isinstance(unit, str):
        if '/L' in unit or '/l' in unit:
            for c in df.columns:
                if isinstance(c, str):
                    if '/L' in c or '/l' in c:
                        col_plot = c
                else:
                    col_plot = df.columns[0]
    else:
        col_plot = [c for c in df.columns if unit in c][0]
    return col_plot


# --------------------------------------------------------------------------------------------------------------------
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


def _find_unit_in_column(ls_columns, plot_col):
    # find relevant column from list of column labels
    if '/L' in plot_col or '/l' in plot_col:
        col2plot = [c for c in ls_columns if '/L' in c or '/l' in c][0]
    else:
        col2plot = [c for c in ls_columns if plot_col in c][0]

    # -------------------------------------------------
    # extract related unit
    unit = col2plot.split('_')[1] if '_' in col2plot else col2plot.split('(')[1].split(')')[0]
    return col2plot, unit


def _find_unit_in_columns_dic(df_data, plot_col):
    dic_col2plot, unit = dict(), None
    for s in df_data.keys():
        for i in df_data[s].columns:
            if isinstance(plot_col, int):
                if plot_col == i:
                    dic_col2plot[s] = i
                    if plot_col == 0:
                        unit = 'mV'
                    else:
                        if '_' in dic_col2plot[s]:
                            unit = dic_col2plot[s].split('_')[1]
                        else:
                            unit = dic_col2plot[s].split('(')[1].split(')')[0]
            else:
                if '/L' in plot_col or '/l' in plot_col:
                    if 'µmol/l' in i or 'µmol/L' in i:
                        dic_col2plot[s] = i
                else:
                    if plot_col in i:
                        dic_col2plot[s] = i

                if plot_col == 'mV' or plot_col == 0:
                    unit = 'mV'
                else:
                    if '_' in dic_col2plot[s]:
                        unit = dic_col2plot[s].split('_')[1]
                    else:
                        unit = dic_col2plot[s].split('(')[1].split(')')[0]
    return dic_col2plot, unit


def intLab(c):
    cnew = int(c.split(' ')[1]) if isinstance(c, str) else c
    return cnew


def findDataColumn(para, df2check, searchK=None):
    if para == 'O2':
        if isinstance(df2check, pd.Series):
            data = df2check
        else:
            col_label = [c for c in df2check.keys() if 'µmol/l' in c or 'µmol/L' in c or 'mean' in c][0]
            data = df2check[col_label] if col_label else df2check
    elif para == 'pH':
        col_label = None
        if isinstance(df2check, pd.Series):
            data = df2check
        else:
            data = df2check[col_label] if col_label else df2check
    elif para == 'H2S':
        core = _findCoreLabel(option1=searchK, option2='core {}'.format(searchK), ls=list(df2check.keys()))
        if isinstance(df2check[core], pd.Series):
            data = df2check[core]
        else:
            col = None
            for c in df2check[core].keys():
                if c in ['total sulfide', 'H2S', 'mean']:
                    if 'sulfide' in c:
                        col = 'total sulfide zero corr_µmol/L'
                    elif 'H2S' in c:
                        col = 'H2S_µM'
                    else:
                        col = 'mean'
                else:
                    pass
            data = df2check[core][col]
    else:
        if isinstance(df2check, pd.Series):
            data = df2check
        else:
            col_label = [c for c in df2check.keys() if 'mV' in c or 'mean' in c][0]
            data = df2check[col_label] if col_label else df2check
    return pd.DataFrame(data)


# --------------------------------------------------------------------------------------------------------------------
def layoutMainFigure(fig, dyrange, dunit):
    ls_axes = fig.axes
    if len(dyrange) > 1:
        if min(dyrange) < 0:
            [axes.set_ylim(min(dyrange)*1.25, max(dyrange)*1.25) for axes in ls_axes]
        else:
            [axes.set_ylim(min(dyrange)*.75, max(dyrange)*1.25) for axes in ls_axes]
        ls_axes[0].invert_yaxis()

    # adjust final layout of figure
    fig.tight_layout(pad=1.) if len(dunit) == 1 else fig.tight_layout(pad=1.15)
    fig.canvas.draw()


def layout4Axes(fs_, dcolor, dunit, axJ2=None, axJ3=None, para2=None, para3=None):
    if axJ3:
        if 'H2S' in para3:
            xlabel = 'total sulfide / µmol/L' if 'total sulfide' in dunit.keys() else 'H2S / µmol/L'
        else:
            xlabel = para3 + ' / {}'.format(dunit[para3])
        axJ3.set_xlabel(xlabel, fontsize=fs_, color=dcolor[para3], labelpad=15)
        makePatchSpinesInVis(ax=axJ3)

    if axJ2:
        # check which analyte from H2S-project is used
        if 'H2S' in para2:
            xlabel = 'total sulfide / µmol/L' if 'total sulfide' in dunit.keys() else 'H2S / µmol/L'
        else:
            xlabel = para2 + ' / {}'.format(dunit[para2])
        axJ2.set_xlabel(xlabel, fontsize=fs_, color=dcolor[para2])

    # make positioning of (additional) axes right
    if axJ2:
        axJ2.spines['bottom'].set_position(('outward', 36))
        axJ2.xaxis.set_ticks_position('bottom'), axJ2.xaxis.set_label_position('bottom')
    if axJ3:
        axJ3.spines["top"].set_position(("axes", 1.25))
        axJ3.spines["top"].set_visible(True), axJ3.spines["bottom"].set_visible(True)


def templateFigure(figJ, axJ, axJ1, fs_, dcolor, dunit, tabcorr, run=1):
    # use always 4 axes but remove the ones that are not needed. So, you make sure that the same parameter is used the
    # same way
    ls_axes = figJ.axes
    if isinstance(tabcorr, type(None)):
        axisLabel_op1(ls_axes=ls_axes, ls_para=['analyte'], dunit=dunit, axJ=axJ, fs_=fs_, dcolor=dcolor)
    else:
        ls_para_plot = sorted(list(tabcorr.replace('--', np.nan).T.dropna().index))
        # layout depending on the amount and type of parameters to plot in a joint graph
        if len(ls_para_plot) == 1:
            axisLabel_op1(ls_axes=ls_axes, ls_para=ls_para_plot, dunit=dunit, axJ=axJ, fs_=fs_, dcolor=dcolor)
        elif len(ls_para_plot) == 2:
            axisLabel_op2(ls_axes=ls_axes, ls_para=ls_para_plot, dunit=dunit, axJ=axJ, axJ1=axJ1, dcolor=dcolor,
                          fs_=fs_)
        elif len(ls_para_plot) == 3:
            axisLabel_op3(ls_axes=ls_axes, ls_para=ls_para_plot, dunit=dunit, axJ=axJ, axJ1=axJ1, dcolor=dcolor,
                          fs_=fs_,)
        else:
            axisLabel_op4(ls_axes=ls_axes, dunit=dunit, axJ=axJ, axJ1=axJ1,  fs_=fs_, dcolor=dcolor)
    # layout and final drawing
    axJ.set_ylabel('Depth / µm'), axJ.invert_yaxis()

    if run == 1:
        figJ.tight_layout(pad=1.)
    figJ.canvas.draw()


def adjust_axes(ls_jPlot, figProf):
    if len(ls_jPlot) == 4:
        figProf.subplots_adjust(bottom=0.25, top=0.72, left=0.15, right=0.95)
    elif len(ls_jPlot) == 3:
        figProf.subplots_adjust(bottom=0.25, top=0.88, left=0.15, right=0.95)
    elif len(ls_jPlot) == 2:
        figProf.subplots_adjust(bottom=0.15, top=0.88, left=0.15, right=0.95)
    elif len(ls_jPlot) == 1:
        figProf.subplots_adjust(bottom=0.15, top=0.95, left=0.15, right=0.95)
    figProf.canvas.draw()


def axisLabel(para, dunit):
    if para == 'O2':
        label = 'dissolved O2 / {}'.format(dunit['O2'])
    elif para == 'pH':
        label = 'pH value'
    elif para == 'H2S':
        label = 'total sulfide / µmol/L' if 'total sulfide' in dunit.keys() else 'H2S / µmol/L'
    elif para == 'EP':
        label = 'EP / mV'
    else:
        label = None
    return label


def axisLabel_op1(ls_axes, ls_para, dunit, axJ, fs_, dcolor):
    # bottom axis only
    if 'O2' in ls_para[0]:
        label = 'dissolved $O_2$ / {}'.format(dunit['O2'])
    elif 'pH' in ls_para[0] or 'analyte' in ls_para[0]:
        label = ls_para[0]
    else:
        label = ls_para[0] + ' / {}'.format(dunit[ls_para[0]])
    ls_axes[0].set_xlabel(label, fontsize=fs_, color=dcolor['O2'])

    axJ.spines["bottom"].set_visible(True), axJ.spines["top"].set_visible(True)
    ls_axes[-1].set_axis_off()


def axisLabel_op2(ls_axes, ls_para, dunit, axJ, axJ1, fs_, dcolor):
    for p in enumerate(ls_para):
        if 'O2' in p[1]:
            label = 'dissolved $O_2$ / {}'.format(dunit['O2'])
        elif 'pH' in p[1]:
            label = 'pH'
        else:
            label = p[1] + ' / {}'.format(dunit[p[1]])
        ls_axes[p[0]].set_xlabel(label, fontsize=fs_, color=dcolor[p[1]])
        axJ.spines["bottom"].set_visible(True), axJ.spines["top"].set_visible(True)
        axJ1.spines["bottom"].set_visible(True), axJ1.spines["top"].set_visible(True)


def axisLabel_op3(ls_axes, ls_para, dunit, axJ, axJ1, fs_, dcolor):
    if sorted(ls_para) == sorted(['O2', 'pH', 'H2S']) or sorted(ls_para) == sorted(['O2', 'pH', 'EP']):
        # order · bottom: O2 and H2S, top: pH
        ls_axes[0].set_xlabel('dissolved $O_2$ / {}'.format(dunit['O2']), fontsize=fs_, color=dcolor['O2'])
        ls_axes[1].set_xlabel('pH', fontsize=fs_, color=dcolor['pH'])

        # add additional axis
        if len(ls_axes) <= 2:
            axJ2 = axJ.twiny()
            layout4Axes(fs_=fs_, dcolor=dcolor, dunit=dunit, axJ2=axJ2, para2=sorted(ls_para)[0])
        axJ.spines["bottom"].set_visible(True), axJ.spines["top"].set_visible(True)
        axJ1.spines["bottom"].set_visible(True), axJ1.spines["top"].set_visible(True)
    elif sorted(ls_para) == sorted(['O2', 'H2S', 'EP']):
        # order · bottom: O2 and H2S, top: EP
        ls_axes[0].set_xlabel('dissolved $O_2$ / {}'.format(dunit['O2']), fontsize=fs_, color=dcolor['O2'])
        ls_axes[1].set_xlabel('EP / {}'.format(dunit['EP']), fontsize=fs_, color=dcolor['EP'])

        # add additional axis
        if len(ls_axes) <= 2:
            axJ2 = axJ.twiny()
            layout4Axes(fs_=fs_, dcolor=dcolor, dunit=dunit, axJ2=axJ2, para2='H2S')
        axJ.spines["bottom"].set_visible(True), axJ.spines["top"].set_visible(True)
        axJ1.spines["bottom"].set_visible(True), axJ1.spines["top"].set_visible(True)
    else:
        # order · bottom: H2S and EP, top: pH
        xlabel = 'total sulfide / µmol/L' if 'total sulfide' in dunit.keys() else 'H2S / µmol/L'
        ls_axes[0].set_xlabel(xlabel, fontsize=fs_, color=dcolor['H2S'])
        ls_axes[1].set_xlabel('pH', fontsize=fs_, color=dcolor['pH'])

        # add additional axis
        if len(ls_axes) <= 2:
            axJ2 = axJ.twiny()
            layout4Axes(fs_=fs_, dcolor=dcolor, dunit=dunit, axJ2=axJ2, para2='EP')
        axJ.spines["bottom"].set_visible(True), axJ.spines["top"].set_visible(True)
        axJ1.spines["bottom"].set_visible(True), axJ1.spines["top"].set_visible(True)


def axisLabel_op4(ls_axes, dunit, axJ, axJ1, fs_, dcolor):
    # bottom axes: O2 (axis0) and H2S (axis2) | top axes: pH (axis1) and EP (axis3)
    ls_axes[0].set_xlabel('dissolved $O_2$ / {}'.format(dunit['O2']), fontsize=fs_, color=dcolor['O2'])
    ls_axes[1].set_xlabel('pH', fontsize=fs_, color=dcolor['pH'])

    # add two more axes
    if len(ls_axes) <= 2:
        axJ2, axJ3 = axJ.twiny(), axJ.twiny()
        layout4Axes(fs_=fs_, dcolor=dcolor, dunit=dunit, axJ2=axJ2, axJ3=axJ3, para2='H2S', para3='EP')

    axJ.spines["top"].set_visible(True), axJ.spines["bottom"].set_visible(True)
    axJ1.spines["top"].set_visible(True), axJ1.spines["bottom"].set_visible(True)


def removeIdleAxes(ls_jPlot, ls_axes):
    if 'O2' not in ls_jPlot:
        ls_axes[0].set_axis_off()
    if 'pH' not in ls_jPlot:
        ls_axes[1].set_axis_off()
    if 'EP' not in ls_jPlot:
        ls_axes[2].set_axis_off()
    if 'H2S' not in ls_jPlot:
        ls_axes[3].set_axis_off()


def plot_ProfileUpdate(data, para, dunit, marker='o', color=None, figProf=None, axProf=None):
    lw, ls = 1.5 if marker is None else 0.75, '-' if marker is None else '-.'
    if axProf:
        # refer to additional dialog window with single profiles
        axProf.cla()
        axProf.plot(data[data.columns[0]].values, data.index, lw=lw, ls=ls, marker=marker, fillstyle='none', ms=4,
                    color=color)
        axProf.axhline(0, color='k', lw=0.5)

        # label axes
        axProf.set_ylabel('Depth / µm'), axProf.set_xlabel(para + '/' + str(dunit[para]))
        # set layout
        figProf.tight_layout(pad=1.15), axProf.invert_yaxis()
        figProf.canvas.draw()


def plot_mainProfUpdate(sval, ls_jPlot, dav, fs_, dcolor, tabcorr, dunit, figProf=None, axJ=None, axJ1=None):
    if figProf and axJ and axJ1:
        # clear all previous plots in figure
        [ax.cla() for ax in figProf.axes]

        # sorted parameters: EP, H2S, O2, pH
        ls_jPlot = sorted(list(dict.fromkeys(ls_jPlot)))
        # create a template of the figure including required additional axes
        templateFigure(figJ=figProf, axJ=axJ, axJ1=axJ1, run=2, fs_=fs_, dunit=dunit, dcolor=dcolor, tabcorr=tabcorr)
        ls_axes = figProf.axes

        # fill the axes with averaged profiles
        for en, para in enumerate(ls_jPlot):
            # find correct position of parameter on coordinate system (separate function)
            if len(ls_jPlot) == 4:
                # all 4 parameter: # bottom axes: O2 (axis0) and H2S (axis2) | top axes: pH (axis1) and EP (axis3)
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

            pkeys = tabcorr[para].to_numpy()
            colK = _findCoreLabel(option1=pkeys[sval], option2='core {}'.format(pkeys[sval]), ls=list(dav[para].keys()))
            data = dav[para][colK]

            # exclude parameter from the index upon first adjustment
            if para in data.index:
                data = data.loc[:data.index[list(data.index).index(para) - 1]]

            ls_axes[pos].plot(data['mean'].values, data.index, lw=1.5, color=dcolor[para])
            ls_axes[pos].xaxis.label.set_color(dcolor[para]), ls_axes[pos].tick_params(axis='x', colors=dcolor[para])
            ls_axes[pos].axhline(0, color='k', lw=0.5)

            # make it a pretty layout
            if pos == 2:
                layout4Axes(fs_=fs_, dcolor=dcolor, dunit=dunit, axJ2=ls_axes[pos], para2=para)
            elif pos == 3:
                layout4Axes(fs_=fs_, dcolor=dcolor, dunit=dunit, axJ3=ls_axes[pos], para3=para)

        # set depth axis in the right direction
        yrange = sorted([ax.get_ylim() for ax in figProf.axes][0], reverse=True)
        [ax.set_ylim(yrange[0], yrange[1]) for ax in figProf.axes]

        # adjust layout depending on the amount of axes
        adjust_axes(ls_jPlot=ls_jPlot, figProf=figProf)
        [ax.set_ylabel('Depth / µm', fontsize=fs_, color='k') for ax in figProf.axes]
        figProf.canvas.draw()


def makePatchSpinesInVis(ax):
    ax.set_frame_on(True)
    ax.patch.set_visible(False)
    for sp in ax.spines.values():
        sp.set_visible(False)