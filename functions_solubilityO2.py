__author__ = 'Silvia E Zieger'
__project__ = 'oxygen solubility depending on T, pressure / salinity'

"""Copyright 2021. All rights reserved.

This software is provided 'as-is', without any express or implied warranty. In no event will the authors be held liable 
for any damages arising from the use of this software.
Permission is granted to anyone to use this software within the scope of reading O2 solubilities from pdf files. 
No permission is granted to use the software for commercial applications, and alter it or redistribute it.

This notice may not be removed or altered from any distribution.
"""

import PyPDF2
import tabula
import pandas as pd


# --------------------------------------------------------------------------------------------------------------------
def read_pdf2table(tab, unit, para):
    if para == tab.columns[0]:
        # Table with salinity in per mill as index and temperature in degC as columns
        df_tab = tab.T.set_index(0).T
        df_tab = df_tab.set_index(unit)

        # check whether each column has only one entry
        ls_split, ls_keys = list(), list()
        for en, i in enumerate(df_tab.columns):
            if type(i) == float:
                pass
            else:
                ls_split.append(en)
                ls_keys.append([float(j) for j in i.split(' ')])

        dspli = dict(map(lambda l:
                         (l, pd.DataFrame(list(map(lambda line: [float(v) for v in line.split(' ')],
                                                   df_tab[df_tab.columns[l]].to_numpy())), columns=ls_keys)), ls_split))
        # create DataFrame from dictionary and format DataFrame
        df_split = pd.concat(dspli, axis=1)
        col_new = [i[1] for i in df_split.columns]
        df_split.columns, df_split.index = col_new, df_tab.index
        df_table = pd.concat([df_split, df_tab.loc[:, df_tab.columns[0 + 1]:]], axis=1)

        # change dtype of index to float
        xnew = df_table.index.astype(float)
        df_table.index = xnew
    else:
        # get the first column (header) that is usually a combination of multiple rows
        k = [float(t) for t in tab[tab.columns[0]].loc[0].split(' ')[1:]]

        # split the entries of the rest split
        ls_split = list()
        for i in tab[tab.columns[0]].loc[1:].index:
            ls_split.append([float(j) for j in tab[tab.columns[0]].loc[i].split(' ')])

        # create DataFrame and update index
        df = pd.DataFrame(ls_split, columns=[unit] + k)
        df = df.set_index(unit)

        # combine first (now split columns) with the rest
        df_crop = tab.loc[:, tab.columns[1]:].T.set_index(0).T
        df_crop.index = df.index

        df_table = pd.concat([df, df_crop], axis=1)
        df_table.index.name = unit

    return df_table


def read_fullpage(file, read_pdf, p):
    # read page from pdf
    tab = tabula.read_pdf(file, pages=p)[0]

    # identity parameter (salinity or pressure) next to temperature
    if '(‰)' in tab.T[0].to_numpy()[0]:
        unit, para, kstop = '(‰)', 'Salinity', 'Units'
    elif '(bar)' in tab.T[0].to_numpy()[0]:
        unit, para, kstop = '(bar)', 'Pressure', 'Values'
    else:
        unit, para, kstop = '', '', ''

    # read table and full text on page
    df = read_pdf2table(tab=tab, unit=unit, para=para)   # starts by 1
    text = read_pdf.getPage(p - 1).extractText()         # starts by 0

    # get the title
    pos1, pos2 = text.index('Gundersen'), text.index(kstop)
    title = text[pos1 + 9:pos2]

    # get the unit and additional information
    if para == 'Salinity':
        pos1, pos2 = text.index('Units'), text.index('Salinity')
        sal = None
    elif para == 'Pressure':
        pos1, pos2 = text.index('Units'), text.index('Pressure')
        sal = text[text.index('calculated at '):text.index('salinity')].split('at ')[1].strip()

    return para, (title, df, text[pos1:pos2], sal)

