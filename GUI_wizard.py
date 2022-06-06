__author__ = 'Silvia E Zieger'
__project__ = 'soil profile analysis'

"""Copyright 2021. All rights reserved.

This software is provided 'as-is', without any express or implied warranty. In no event will the authors be held liable 
for any damages arising from the use of this software.
Permission is granted to anyone to use this software within the scope of evaluating multi-analyte sensing. No permission
is granted to use the software for commercial applications, and alter it or redistribute it.

This notice may not be removed or altered from any distribution.
"""

from PyQt5 import QtCore, QtWidgets
from PyQt5 import QtGui
from PyQt5.QtWidgets import (QCheckBox, QComboBox, QFileDialog, QFrame, QGridLayout, QGroupBox, QHBoxLayout, QLabel,
                             QLineEdit, QDialog, QMessageBox, QPushButton, QSlider, QVBoxLayout, QWidget, QWizard,
                             QWizardPage, QTabWidget, QTableWidget, QTableWidgetItem)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import *
import numpy as np
import seaborn as sns
import pandas as pd
from lmfit import Model
import os
import re
from mergedeep import merge
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT, FigureCanvasQTAgg

import functions_dbs as dbs
import function_salinity as sal

# global parameter
lim, lim_min, steps = 150, -1, 0.5
convC2K = 273.15                    # temperature conversion from degC into Kelvin
gof_accept = 10.                    # acceptable goodness of fit to result to reasonable depth profiles (SWI correction)
gof_top = 3.                        # excellent goodness of fit to result to reasonable depth profiles (SWI correction)
ls_allData = ['meta data', 'raw data', 'fit_mV', 'adjusted data', 'penetration depth']
grp_label = None                    # global definition of group label

# color list for samples: grey, orange, petrol, green, yellow, light grey, blue
ls_col = list(['#4c5558', '#eb9032', '#21a0a8', '#f9d220', '#9ec759', '#96a6ab', '#1B08AA', '#40A64A', '#D20D41',
               '#E87392'])
ls_figtype = ['png']
dpi = 300
fs_font, fs_ = 10, 10

# plot style / layout
sns.set_context('paper'), sns.set_style('ticks')

# global variables for individual projects
dcol_label, results, dout, dav, tabcorr = dict(), dict(), dict(), dict(), None

# O2 project
core_select, userCal, ret = None, None, None
dobj_hid, dO2_core, dpen_glob = dict(), dict(), dict()
# pH project
scalepH = dict()
# H2S project
dobj_hidH2S, scaleh2s = dict(), dict()
sFront = 10                            # sulfidic front defined as percentage above the base value (in the water column)
# EP project
dobj_hidEP, scaleEP = dict(), dict()

# wizard architecture - how are the pages arranged?
wizard_page_index = {"IntroPage": 0, "o2Page": 1, "phPage": 2, "h2sPage": 3, "epPage": 4, "charPage": 5, "averageLP": 6,
                    "joint plots": 7, "final page": 8}


# !!! TODO: clean hidden code and unnecessary functions
# !!! TODO: make smaller functions and store them in library py file - checked: intro, o2
# !!! TODO: clean warnings marked by pycharm
# !!! TODO: write the guideline - update the subtitle accordingly and avoid the "black box" image
# !!! TODO: make the layout / fontsize of text, buttons,... all the same
# !!! TODO: combine similar functions / plots of different projects
# !!! TODO: split into different py-projects and only load the page --- makes it more readable

class QIComboBox(QComboBox):
    def __init__(self):
        super(QIComboBox, self).__init__()


class MagicWizard(QWizard):
    def __init__(self):
        super(MagicWizard, self).__init__()
        self.introPage = IntroPage()
        self.setPage(wizard_page_index["IntroPage"], self.introPage)
        self.o2_project = o2Page()
        self.setPage(wizard_page_index["o2Page"], self.o2_project)
        self.ph_project = phPage()
        self.setPage(wizard_page_index["phPage"], self.ph_project)
        self.h2s_project = h2sPage()
        self.setPage(wizard_page_index["h2sPage"], self.h2s_project)
        self.ep_project = epPage()
        self.setPage(wizard_page_index["epPage"], self.ep_project)
        self.char_project = charPage()
        self.setPage(wizard_page_index["charPage"], self.char_project)
        self.avergaeLP_project = avProfilePage()
        self.setPage(wizard_page_index["averageLP"], self.avergaeLP_project)
        self.jointPlot_project = jointPlotPage()
        self.setPage(wizard_page_index["joint plots"], self.jointPlot_project)
        self.finalPage = FinalPage()
        self.setPage(wizard_page_index["final page"], self.finalPage)

        # set start page
        self.setStartId(wizard_page_index["IntroPage"])

        # GUI layout
        self.setWindowTitle("Guide through the forest")
        self.setGeometry(50, 50, 200, 200)

        # define Wizard style and certain options
        self.setWizardStyle(QWizard.MacStyle)
        self.setOptions(QtWidgets.QWizard.NoCancelButtonOnLastPage | QtWidgets.QWizard.HaveFinishButtonOnEarlyPages)
        # !!!TODO: enable logo in Subtitle
        # logo_image = QImage('Figure4icon.png')
        # self.setPixmap(QWizard.LogoPixmap, QPixmap.fromImage(logo_image))

        # add a background image
        path = os.path.join('/Users/au652733/Python/Project_CEMwizard/Pictures', 'logo_v1.png')
        pixmap = QtGui.QPixmap(path)
        pixmap = pixmap.scaled(400, 400, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
        self.setPixmap(QWizard.BackgroundPixmap, pixmap)


class IntroPage(QWizardPage):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle("InfoPage")
        self.setSubTitle("Enter the path to your measurement file and select which of the parameters should be "
                         "analyzed.\nWe will then guide you through the analysis.\n")
        # create layout
        self.initUI()

        # connect checkbox and load file button with a function
        self.load_button.clicked.connect(self.load_data)
        # self.OutPut_box.stateChanged.connect(self.softwareFile)
        self.save_button.clicked.connect(self.save_path)
        self.set_button.clicked.connect(self.save_settings)
        self.h2s_box.stateChanged.connect(self.total_sulfide)
        self.ph_box.stateChanged.connect(self.pH_check)
        self.o2_box.stateChanged.connect(self.parameter_selection)
        self.h2s_box.stateChanged.connect(self.parameter_selection)
        self.ph_box.stateChanged.connect(self.parameter_selection)
        self.ep_box.stateChanged.connect(self.parameter_selection)

        # when all conditions are met, enable NEXT button:
        self.fname, self.fsave, self.OutPut, self.ls_para = QLineEdit(), QLineEdit(), QLineEdit(), QLineEdit()
        self.pHfromo2 = QLineEdit("False")
        self.registerField("Data*", self.fname)
        self.registerField("SoftwareFile", self.OutPut)
        self.registerField("Storage path*", self.fsave)
        self.registerField('parameter selected*', self.ls_para)
        self.registerField('saving parameters', self.ls_saveOp)
        self.registerField('SWI pH as o2', self.pHfromo2)
        results['salinity PSU'], results['temperature degC'] = 0, 25

    def initUI(self):
        # checkbox for which parameters should be included; path for measurement file
        self.o2_box = QCheckBox('Oxygen O2', self)
        self.ph_box = QCheckBox('pH', self)
        self.h2s_box = QCheckBox('total sulfide ΣS2- / H2S', self)
        self.ep_box = QCheckBox('EP', self)
        self.o2_box.setFont(QFont('Helvetica Neue', 12)), self.ph_box.setFont(QFont('Helvetica Neue', 12)),
        self.h2s_box.setFont(QFont('Helvetica Neue', 12)), self.ep_box.setFont(QFont('Helvetica Neue', 12))

        # path for measurement file (csv)
        self.load_button = QPushButton('Load meas. file', self)
        self.load_button.setFixedWidth(150), self.load_button.setFont(QFont('Helvetica Neue', fs_font))
        self.inputFileLineEdit = QLineEdit(self)
        self.inputFileLineEdit.setValidator(QtGui.QDoubleValidator())
        self.inputFileLineEdit.setFixedWidth(300), self.inputFileLineEdit.setAlignment(Qt.AlignRight)
        self.inputFileLineEdit.setFont(QFont('Helvetica Neue', int(0.9*fs_font)))
        # self.OutPut_box = QCheckBox('output file', self)

        # directory to store files
        self.save_button = QPushButton('Storage path', self)
        self.save_button.setFixedWidth(150), self.save_button.setFont(QFont('Helvetica Neue', fs_font))
        self.inputSaveLineEdit = QLineEdit(self)
        self.inputSaveLineEdit.setValidator(QtGui.QDoubleValidator())
        self.inputSaveLineEdit.setFixedWidth(300), self.inputSaveLineEdit.setAlignment(Qt.AlignRight)
        self.inputSaveLineEdit.setFont(QFont('Helvetica Neue', int(0.9*fs_font)))

        # saving options
        self.set_button = QPushButton('Settings', self)
        self.set_button.setFixedWidth(150), self.set_button.setFont(QFont('Helvetica Neue', fs_font))

        # pre-define list of save options
        self.ls_saveOp = QLineEdit()
        self.ls_saveOp.setText(','.join(['meta data', 'raw data', 'fit_mV', 'adjusted data', 'penetration depth']))
        # creating main window (GUI)
        w = QWidget()
        # create layout grid
        mlayout = QVBoxLayout(w)
        vbox_top, vbox_middle, vbox_bottom = QHBoxLayout(), QHBoxLayout(), QHBoxLayout()
        mlayout.addLayout(vbox_top), mlayout.addLayout(vbox_middle), mlayout.addLayout(vbox_bottom)

        meas_settings = QGroupBox("Parameter selection for analysis")
        grid_load = QGridLayout()
        meas_settings.setFixedHeight(100)
        meas_settings.setFont(QFont('Helvetica Neue', 12))
        vbox_top.addWidget(meas_settings)
        meas_settings.setLayout(grid_load)

        # include widgets in the layout
        grid_load.addWidget(self.o2_box, 0, 0)
        grid_load.addWidget(self.ph_box, 1, 0)
        grid_load.addWidget(self.h2s_box, 0, 3)
        grid_load.addWidget(self.ep_box, 1, 3)

        meas_file = QGroupBox("Define directories")
        grid_file = QGridLayout()
        meas_file.setFixedHeight(120)
        meas_file.setFont(QFont('Helvetica Neue', 12))
        vbox_middle.addWidget(meas_file)
        meas_file.setLayout(grid_file)

        # include widgets in the layout
        grid_file.addWidget(self.load_button, 0, 0)
        grid_file.addWidget(self.inputFileLineEdit, 0, 1)
        # grid_file.addWidget(self.OutPut_box, 0, 2)
        grid_file.addWidget(self.save_button, 1, 0)
        grid_file.addWidget(self.inputSaveLineEdit, 1, 1)
        grid_file.addWidget(self.set_button, 2, 0)
        self.setLayout(mlayout)

    def load_data(self):
        # load all files at a time that shall be analyzed together
        fname, filter = QFileDialog.getOpenFileNames(self, "Select specific excel file for measurement analysis",
                                                     "Text files (*.xls *.csv *xlsx)")
        self.fname.setText(str(fname))
        if fname:
            self.inputFileLineEdit.setText(str(fname))
            self.fname.setText(str(fname))

    def save_path(self):
        fsave = QtWidgets.QFileDialog.getExistingDirectory(self, 'Select Folder')
        self.fsave.setText(fsave)
        if fsave:
            self.inputSaveLineEdit.setText(fsave)
            self.fsave.setText(fsave)

    def save_settings(self):
        # open a pop up window with options to select what shall be saved
        global wSet
        wSet = SettingWindow(self.ls_saveOp)
        if wSet.isVisible():
            pass
        else:
            wSet.show()

    def total_sulfide(self):
        if self.h2s_box.isChecked() is True:
            self.ph_box.setChecked(True)

    def pH_check(self):
        if self.h2s_box.isChecked() is True and self.ph_box.isChecked() is False:
            msgBox = QMessageBox()
            msgBox.setIcon(QMessageBox.Information)
            msgBox.setText("Total sulfide ΣS2- can only be calculated, when the pH is provided as well. Otherwise you"
                           " will only get the H2S concentration.")
            msgBox.setFont(QFont('Helvetica Neue', 11))
            msgBox.setWindowTitle("Warning")
            msgBox.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)

            returnValue = msgBox.exec()
            if returnValue == QMessageBox.Ok:
                pass

            # remove all pH information from results
            ls_remove = list()
            [ls_remove.append(k) for k in results.keys() if 'pH' in k]
            # delete a keys not in that list regardless of whether it is in the dictionary
            [results.pop(i, None) for i in ls_remove]

    def parameter_selection(self):
        ls_para = list()
        if self.o2_box.isChecked() is True:
            self.pHfromo2.setText('True')
            ls_para.append('o2')
        if self.ph_box.isChecked() is True:
            ls_para.append('ph')
        if self.h2s_box.isChecked() is True:
            ls_para.append('h2s')
        if self.ep_box.isChecked() is True:
            ls_para.append('ep')
        self.ls_para.setText(','.join(ls_para))

    def nextId(self) -> int:
        ls_para = list(self.field('parameter selected').split(','))
        if self.field('parameter selected'):
            if 'o2' in self.field('parameter selected'):
                return wizard_page_index["o2Page"]
            else:
                return wizard_page_index["{}Page".format(ls_para[0])]
        else:
            return wizard_page_index["IntroPage"]


class SettingWindow(QDialog):
    def __init__(self, ls_saveOp):
        super().__init__()
        global dout
        dout = dict()
        self.ls_saveOp = ls_saveOp
        self.initUI()

        # when checkbox selected, save information in registered field
        self.meta_box.stateChanged.connect(self.saveoption_selected)
        self.rdata_box.stateChanged.connect(self.saveoption_selected)
        self.fit_box.stateChanged.connect(self.saveoption_selected)
        self.adj_box.stateChanged.connect(self.saveoption_selected)
        self.pen_box.stateChanged.connect(self.saveoption_selected)
        self.swiRaw_box.stateChanged.connect(self.saveoption_selected)
        self.swiF_box.stateChanged.connect(self.saveoption_selected)
        self.fitF_box.stateChanged.connect(self.saveoption_selected)
        self.penF_box.stateChanged.connect(self.saveoption_selected)

        # connect checkbox and load file button with a function
        self.close_button.clicked.connect(self.close_window)

    def initUI(self):
        self.setWindowTitle("Saving options")
        self.setGeometry(650, 180, 300, 200)

        # close window button
        self.close_button = QPushButton('OK', self)
        self.close_button.setFixedWidth(100), self.close_button.setFont(QFont('Helvetica Neue', fs_font))

        # checkboxes for possible data tables and figures to save
        self.meta_box = QCheckBox('Meta data', self)
        self.meta_box.setChecked(True)
        self.rdata_box = QCheckBox('Raw data', self)
        self.rdata_box.setChecked(True)
        self.fit_box = QCheckBox('Fit data', self)
        self.fit_box.setChecked(True)
        self.adj_box = QCheckBox('Adjusted data', self)
        self.adj_box.setChecked(True)
        self.pen_box = QCheckBox('Penetration depth', self)
        self.pen_box.setChecked(True)

        self.swiRaw_box = QCheckBox('Raw profile', self)
        self.swiRaw_box.setChecked(False)
        self.swiF_box = QCheckBox('Adjusted profile', self)
        self.swiF_box.setChecked(False)
        self.fitF_box = QCheckBox('Fit plot', self)
        self.fitF_box.setChecked(False)
        self.penF_box = QCheckBox('Penetration depth', self)
        self.penF_box.setChecked(False)

        # creating window layout
        mlayout2 = QVBoxLayout()
        vbox2_top, vbox2_middle, vbox2_bottom = QHBoxLayout(), QHBoxLayout(), QHBoxLayout()
        mlayout2.addLayout(vbox2_top), mlayout2.addLayout(vbox2_middle), mlayout2.addLayout(vbox2_bottom)

        data_settings = QGroupBox("Data tables")
        grid_data = QGridLayout()
        data_settings.setFont(QFont('Helvetica Neue', 12))
        vbox2_top.addWidget(data_settings)
        data_settings.setLayout(grid_data)

        # include widgets in the layout
        grid_data.addWidget(self.meta_box, 0, 0)
        grid_data.addWidget(self.rdata_box, 1, 0)
        grid_data.addWidget(self.fit_box, 2, 0)
        grid_data.addWidget(self.adj_box, 3, 0)
        grid_data.addWidget(self.pen_box, 5, 0)

        fig_settings = QGroupBox("Figures")
        grid_fig = QGridLayout()
        fig_settings.setFont(QFont('Helvetica Neue', 12))
        vbox2_middle.addWidget(fig_settings)
        fig_settings.setLayout(grid_fig)

        # include widgets in the layout
        grid_fig.addWidget(self.swiRaw_box, 0, 0)
        grid_fig.addWidget(self.swiF_box, 1, 0)
        grid_fig.addWidget(self.fitF_box, 2, 0)
        grid_fig.addWidget(self.penF_box, 4, 0)

        ok_settings = QGroupBox("")
        grid_ok = QGridLayout()
        ok_settings.setFont(QFont('Helvetica Neue', 12))
        vbox2_bottom.addWidget(ok_settings)
        ok_settings.setLayout(grid_ok)

        # include widgets in the layout
        grid_ok.addWidget(self.close_button, 0, 0)

        # add everything to the window layout
        self.setLayout(mlayout2)

    def saveoption_selected(self):
        ls_setSave = list()
        # settings for data points
        if self.meta_box.isChecked() is True:
            ls_setSave.append('meta data')
        if self.rdata_box.isChecked() is True:
            ls_setSave.append('raw data')
        if self.fit_box.isChecked() is True:
            ls_setSave.append('fit_mV')
            ls_setSave.append('derivative_mV')
        if self.adj_box.isChecked() is True:
            ls_setSave.append('adjusted data')
        if self.pen_box.isChecked() is True:
            ls_setSave.append('penetration depth')
        # figures
        if self.swiRaw_box.isChecked() is True:
            ls_setSave.append('fig raw')
        if self.swiF_box.isChecked() is True:
            ls_setSave.append('fig adjusted')
        if self.fitF_box.isChecked() is True:
            ls_setSave.append('fig fit')
        if self.penF_box.isChecked() is True:
            ls_setSave.append('fig penetration')
        # update QLineEdit for information transfer
        self.ls_saveOp.setText(','.join(ls_setSave))

    def close_window(self):
        self.hide()


# -----------------------------------------------
class o2Page(QWizardPage):
    def __init__(self, parent=None):
        super(o2Page, self).__init__(parent)
        self.setTitle("O2 depth profile")
        self.setSubTitle("Please enter the required parameters. The O2 depth profile will be determined accordingly."
                         " \nTo start the analysis,  press CONTINUE. \n")

        # general layout
        self.initUI()

        # define certain parameter potentially used for saving
        self.typeCalib = None
        self.dfig_out = dict()
        self.dcore_pen = dict()

        # connect checkbox and load file button with a function
        self.dtab_sal, self.count = None, 0
        self.salcon_button.clicked.connect(self.conductivity_converterO2)
        self.slider.valueChanged.connect(self.label_core_select)
        self.continue_button.clicked.connect(self.continue_process)
        self.save_button.clicked.connect(self.save)
        self.reset_button.clicked.connect(self.reset_o2page)

    def initUI(self):
        # plot window, side panel for user input, and continue button
        temperature_label, temperature_unit_label = QLabel(self), QLabel(self)
        temperature_label.setText('Temperature'), temperature_unit_label.setText('degC')
        self.temperature_edit = QLineEdit(self)
        self.temperature_edit.setValidator(QDoubleValidator()), self.temperature_edit.setAlignment(Qt.AlignRight)
        self.temperature_edit.setText(str(results['temperature degC']))

        salinity_label, salinity_unit_label = QLabel(self), QLabel(self)
        salinity_label.setText('Salinity'), salinity_unit_label.setText('PSU')
        self.salinity_edit = QLineEdit(self)
        self.salinity_edit.setValidator(QDoubleValidator()), self.salinity_edit.setAlignment(Qt.AlignRight)
        self.salinity_edit.setText(str(results['salinity PSU']))

        pene2_label, pene2_unit_label = QLabel(self), QLabel(self)
        pene2_label.setText('Sensor LoD'), pene2_unit_label.setText('µmol/L')
        self.pene2_edit = QLineEdit(self)
        self.pene2_edit.setValidator(QDoubleValidator()), self.pene2_edit.setAlignment(Qt.AlignRight)
        self.pene2_edit.setText('2.5')
        self.pene2_edit.editingFinished.connect(self.updatePene)

        # storage for comparison
        self.salcon_button = QPushButton('Converter', self)
        self.salcon_button.setFixedWidth(100), self.salcon_button.setFont(QFont('Helvetica Neue', fs_font))
        self.O2_penetration = float(self.pene2_edit.text())
        self.continue_button = QPushButton('Continue', self)
        self.continue_button.setFixedWidth(100), self.continue_button.setFont(QFont('Helvetica Neue', fs_font))
        self.save_button = QPushButton('Save', self)
        self.save_button.setFixedWidth(100), self.save_button.setFont(QFont('Helvetica Neue', fs_font))
        self.reset_button = QPushButton('Reset', self)
        self.reset_button.setFixedWidth(100), self.reset_button.setFont(QFont('Helvetica Neue', fs_font))
        self.checkFit_button = QPushButton('Check fit', self)
        self.checkFit_button.setFixedWidth(100), self.checkFit_button.setFont(QFont('Helvetica Neue', fs_font))
        self.checkFit_button.setEnabled(False)

        # Slider for different cores and label on the right
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setMinimumWidth(350), self.slider.setFixedHeight(20)
        self.sld_label = QLabel()
        self.sld_label.setFixedWidth(55)
        self.sld_label.setText('group: --')

        # creating window layout
        w1 = QWidget()
        mlayout1 = QVBoxLayout(w1)
        vbox1_left, vbox1_middle, vbox1_right = QHBoxLayout(), QHBoxLayout(), QHBoxLayout()
        mlayout1.addLayout(vbox1_left), mlayout1.addLayout(vbox1_middle), mlayout1.addLayout(vbox1_right)

        para_settings = QGroupBox("Input for O2 analysis")
        grid_load = QGridLayout()
        para_settings.setFont(QFont('Helvetica Neue', 12)), para_settings.setFixedHeight(150)
        para_settings.setMinimumWidth(600)
        vbox1_left.addWidget(para_settings)
        para_settings.setLayout(grid_load)

        # include widgets in the layout
        grid_load.addWidget(temperature_label, 0, 0)
        grid_load.addWidget(self.temperature_edit, 0, 1)
        grid_load.addWidget(temperature_unit_label, 0, 2)
        grid_load.addWidget(salinity_label, 1, 0)
        grid_load.addWidget(self.salinity_edit, 1, 1)
        grid_load.addWidget(salinity_unit_label, 1, 2)
        grid_load.addWidget(self.salcon_button, 1, 3)
        grid_load.addWidget(pene2_label, 2, 0)
        grid_load.addWidget(self.pene2_edit, 2, 1)
        grid_load.addWidget(pene2_unit_label, 2, 2)
        grid_load.addWidget(self.checkFit_button, 4, 1)
        grid_load.addWidget(self.continue_button, 4, 0)
        grid_load.addWidget(self.reset_button, 4, 2)
        grid_load.addWidget(self.save_button, 4, 3)

        # draw additional "line" to separate parameters from plots and to separate navigation from rest
        vline = QFrame()
        vline.setFrameShape(QFrame.HLine | QFrame.Raised)
        vline.setLineWidth(2)
        vbox1_middle.addWidget(vline)

        # plotting area
        self.figO2, self.axO2 = plt.subplots(figsize=(3, 4))
        self.canvasO2 = FigureCanvasQTAgg(self.figO2)
        self.axO2.set_xlabel('O2 / mV'), self.axO2.set_ylabel('Depth / µm')
        self.axO2.invert_yaxis()
        self.figO2.subplots_adjust(bottom=0.2, right=0.95, top=0.9, left=0.15)
        sns.despine()

        O2_group = QGroupBox("O2 depth profile")
        # O2_group.setMinimumWidth(200), \
        O2_group.setMinimumHeight(300)
        grid_o2 = QGridLayout()

        # add GroupBox to layout and load buttons in GroupBox
        vbox1_right.addWidget(O2_group)
        O2_group.setLayout(grid_o2)
        grid_o2.addWidget(self.slider, 1, 0)
        grid_o2.addWidget(self.sld_label, 1, 1)
        grid_o2.addWidget(self.canvasO2, 2, 0)
        self.setLayout(mlayout1)

    def label_core_select(self, value):
        if self.count == 0:
            return
        else:
            self.sld_label.setText('{}: {}'.format(self.ls_colname[0], value))

    def conductivity_converterO2(self):
        # open dialog window for conductivity -> salinity conversion
        global wConv
        wConv = SalConvWindowO2(self.temperature_edit, self.salinity_edit)
        if wConv.isVisible():
            pass
        else:
            wConv.show()

    def pre_check_calibration(self):
        # minimal dissolved O2 is assumed to be 0%air
        self.o2_dis = dbs.dissolvedO2_calc(T=float(self.temperature_edit.text()),
                                           salinity=float(self.salinity_edit.text()))

    def User4Calibration(self, ):
        global userCal
        if userCal:
            pass
        else:
            userCal = QMessageBox.question(self, 'Calibration', 'Shall we use the calibration from the measurement '
                                                                'file? \nIf not,  the sensor will be recalibrated based'
                                                                ' on the given temperature & salinity.',
                                           QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)

        if userCal == QMessageBox.Yes:
            # define for output metadata
            self.typeCalib = 'internal calibration from measurement file'

            # calibration from excel file
            dO2_core.update(dbs.O2rearrange(df=self.ddata_shift, unit='µmol/L'))
            results['O2 profile'] = dO2_core

            # continue with the process - first execute without any click
            self.continue_processII()
            # update process that shall be executed when button is clicked
            self.continue_button.disconnect()
            self.continue_button.clicked.connect(self.continue_processII)

        elif userCal == QMessageBox.No:
            global ret
            if ret:
                pass
            else:
                msgBox1 = QMessageBox()
                msgBox1.setIcon(QMessageBox.Question)
                msgBox1.setFont(QFont('Helvetica Neue'))
                msgBox1.setWindowTitle('Recalibration')
                msgBox1.setText('Shall we do the calibration core by core or should we apply one calibration to all '
                                'samples?')
                msgBox1.addButton('group by group', msgBox1.ActionRole)
                msgBox1.addButton('apply to all', msgBox1.ActionRole)

                ret = msgBox1.exec()

            global lim, lim_min
            if ret == 0:
                # define for output metadata
                self.typeCalib = 'recalibration core by core'

                # calibration core by core
                dO2_core.update(dbs.O2converter4conc(data_shift=self.ddata_shift, lim_min=lim_min, lim=lim,
                                                     o2_dis=self.o2_dis, unit='µmol/L'))

                # results['O2 profile'] = dO2_core
                for c in dO2_core.keys():
                    for i in dO2_core[c].columns:
                        # get the right columns:
                        for k in results['O2 profile'][c][i[0]].columns:
                            if 'M' in k or 'mol' in k:
                                col2sub = k
                        results['O2 profile'][c][i[0]][col2sub] = dO2_core[c][i].dropna().to_numpy()

                # continue with the process - first execute without any click
                self.continue_processII()
                # update process that shall be executed when button is clicked
                self.continue_button.disconnect()
                self.continue_button.clicked.connect(self.continue_processII)
            else:
                # open window (QDialog) to identify the core that shall be used
                global wCore
                wCore = CalibCore(self.ls_core)
                if wCore.isVisible():
                    pass
                else:
                    wCore.show()

                # pause until we have a core selected
                try:
                    if core_select:
                        # do not show the selection window anymore but continue the process
                        wCore.hide()
                    else:
                        userCal, ret = QMessageBox.No, 1
                        # open window (QDialog) to identify the core that shall be used
                        wCore = CalibCore(self.ls_core)

                    # continue with the process - first execute without any click
                    self.continue_processI()
                    # update process that shall be executed when button is clicked
                    self.continue_button.disconnect()
                    self.continue_button.clicked.connect(self.continue_processI)
                except:
                    userCal, ret = QMessageBox.No, 1
                    wCore = CalibCore(self.ls_core)
                    if core_select:
                        wCore.hide()
                        # continue with the process - first execute without any click
                        self.continue_processI()
                        # update process that shall be executed when button is clicked
                        self.continue_button.disconnect()
                        self.continue_button.clicked.connect(self.continue_processI)

    def load_O2data(self):
        # raw measurement file pre-processed and saved per default as rawData file
        dsheets, dignore = _loadGlobData(file_str=self.field("Data"))
        for k in dignore.keys():
            if 'O2' in dignore[k].keys():
                l = k

        # pre-check whether O2_all in sheet names
        sheet_select = dbs.sheetname_check(dsheets, para='O2')
        checked = checkDatavsPara(sheet_select, par='O2')

        if checked is True:
            #  prepare file depending on the type
            ddata = dsheets[sheet_select].set_index('Nr')

            # remove excluded profiles
            ddata_update = _excludeProfiles(analyt='O2', dignore=dignore[l], ddata=ddata)

            global grp_label
            if grp_label is None:
                grp_label = ddata_update.columns[0]
        else:
            # reset page as nothing was found
            self.reset_o2page()
            return None, None
        return ddata_update, sheet_select, checked

    def continue_process(self):
        # store relevant information
        results['temperature degC'] = float(self.temperature_edit.text())
        results['salinity PSU'] = float(self.salinity_edit.text())

        if self.count == 0:
            # determine min/max dissolved O2 according to set temperature and salinity
            self.pre_check_calibration()

            # update subtitle for progress report
            self.setSubTitle("The analysis starts with the correction of the surface-water interface (SWI).  If the "
                             "correction looks good,  press CONTINUE.  Otherwise,  press CHECK FIT for adjustments. \n")
            # load data from excel sheet depending on the type (measurement file or prepared file)
            ddata, sheet_select, checked = self.load_O2data()

            if checked is True:
                # sigmoidal fit
                [self.ls_core, self.ls_colname, self.gmod, self.dic_dcore,
                 self.dic_deriv, self.dfit] = self.sigmoidalFit(ddata=ddata, sheet_select=sheet_select)

                # update group label
                self.sld_label.setText('{}: {}'.format(self.ls_colname[0], min(self.ls_core)))

                # baseline shift
                self.baselineShift()

                # enable button to click and investigate the derivative / fit
                self.checkFit_button.setEnabled(True)
                self.checkFit_button.clicked.connect(self.checkFitWindow)

                # enable next step in O2 analysis
                self.count += 1

        elif self.count == 1:
            # update subtitle for progress report
            self.setSubTitle("Depth correction (SWI) done.  Now,  continue with calibration. \n \n")

            # get user input on calibration - convert O2 potential into concentration
            self.User4Calibration()

    def sigmoidalFit(self, ddata, sheet_select):
        # pre-set of parameters
        gmod = Model(dbs._gompertz_curve_adv)

        # ----------------------------------------------------------------------------------
        # list all available cores for O2 sheet
        ls_core = list(dict.fromkeys(ddata[ddata.columns[0]]))

        # import all measurements for given parameter
        [dic_dcore, ls_nr,
         ls_colname] = dbs.load_measurements(dsheets=ddata, ls_core=ls_core, para=sheet_select)
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
        dfit, dic_deriv = dbs.fit_baseline(ls_core=ls_core, ls_nr=ls_nr, dic_dcore=dic_dcore, steps=steps, gmod=gmod,
                                           adv=True)
        results['O2 fit'], results['O2 derivative'] = dfit, dic_deriv

        return ls_core, ls_colname, gmod, dic_dcore, dic_deriv, dfit

    def baselineShift(self):
        # baseline shift of all samples (of all cores)
        self.ddata_shift = dict()
        self.ddata_shift = dbs.baseline_shift(dic_dcore=results['O2 profile'], dfit=self.dfit)
        results['O2 SWI corrected'], results['O2 profile'] = self.ddata_shift, self.ddata_shift

        # plot baseline corrected depth profiles
        fig0 = dbs.GUI_baslineShift(data_shift=self.ddata_shift, core=min(self.ls_core), ls_core=self.ls_core,
                                    fig=self.figO2, ax=self.axO2, plot_col='mV', grp_label=self.ls_colname[0])

        # slider initialized to first core
        self.slider.setMinimum(int(min(self.ls_core))), self.slider.setMaximum(int(max(self.ls_core)))
        self.slider.setValue(int(min(self.ls_core)))
        self.sld_label.setText('{}: {}'.format(self.ls_colname[0], int(min(self.ls_core))))

        # when slider value change (on click), return new value and update figure plot
        self.slider.valueChanged.connect(self.slider_update)

        # in case the FitWindow is open -> update figFit according to selected sliderValue
        self.slider.sliderReleased.connect(self.wFit_update)
        self.figO2.canvas.draw()

    def continue_processI(self):
        # possible responses include either "core" or only the number -> find pattern with re
        dO2_core.update(dbs.O2calc4conc_one4all(core_sel=int(core_select), lim_min=lim_min, lim=lim, unit='µmol/L',
                                                o2_dis=self.o2_dis, data_shift=self.ddata_shift))
        results['O2 profile'] = dO2_core

        # define for output metadata
        self.typeCalib = 'recalibration one core ' + str(core_select) + ' to all'

        # continue with the process - first execute without any click
        self.continue_processII()
        self.continue_button.disconnect()
        self.continue_button.clicked.connect(self.continue_processII)

    def continue_processII(self):
        if self.count == 1:
            # determine penetration depth according to given O2 concentration
            self.O2_penetration = float(self.pene2_edit.text())
            [self.dcore_pen,
             dcore_fig] = GUI_calcO2penetration(unit='µmol/L', steps=steps, gmod=self.gmod,
                                                O2_pen=float(self.pene2_edit.text()))
            results['O2 penetration depth'] = self.dcore_pen

            # update subtitle for progress report
            self.setSubTitle("For each core,  select all samples to be considered for calculation of the average "
                             "penetration depth. Then press CONTINUE.\n")

            # slider initialized to first core
            self.slider.setValue(int(min(self.ls_core)))
            self.sld_label.setText('{}: {}'.format(self.ls_colname[0], int(min(self.ls_core))))

            # initialize first plot with first core
            fig1 = GUI_O2depth(core=int(min(self.ls_core)), ls_core=self.ls_core, dcore_pen=self.dcore_pen,
                               dobj_hid=dobj_hid, ax=self.axO2, fig=self.figO2)
            # when slider value change (on click), return new value and update figure plot
            self.slider.valueChanged.connect(self.slider_update1)
            self.figO2.canvas.draw()

            # enable next step in O2 analysis
            results['O2 hidden objects'] = dobj_hid
            self.count += 1

        elif self.count == 2:
            # update subtitle for progress report
            self.setSubTitle("Calibration done.  For each core, the average penetration depth is determined "
                             "considering only the selected samples... End of analysis.\n")

            self._CalcPenetration()
            # disable continue button at the end of this analysis and reset status to 0
            self.count += 1
            self.continue_button.setEnabled(False)

    def _CalcPenetration(self):
        # double check, whether definition of penetration depth has changed
        if self.O2_penetration != float(self.pene2_edit.text()):
            [self.dcore_pen,
             dcore_fig] = GUI_calcO2penetration(unit='µmol/L', steps=steps, O2_pen=float(self.pene2_edit.text()),
                                                gmod=self.gmod)

        # slider initialized to first core
        self.slider.setValue(int(min(self.ls_core)))
        self.sld_label.setText('{}: {}'.format(self.ls_colname[0], int(min(self.ls_core))))

        # initialize first plot with first core
        fig2, mean_ = GUI_penetration_av(core=int(min(self.ls_core)), ls_core=self.ls_core,
                                         dcore_pen=self.dcore_pen, fig=self.figO2, ax=self.axO2)

        if np.nan in mean_:
            self.setSubTitle("WARNING! It was not possible to determine the average penetration depth. Maybe, try "
                             "a higher O2 concentration.")

        # when slider value change (on click), return new value and update figure plot
        self.slider.valueChanged.disconnect(self.slider_update1)
        self.slider.valueChanged.connect(self.slider_update2)
        self.figO2.canvas.draw()

    def updatePene(self):
        if self.count == 0:  # only in the last step, count is set to 0
            print('update calculation of penetration depth')
            self._CalcPenetration()

    def wFit_update(self):
        if self.ls_core:
            # allow only discrete values according to existing cores
            core_select = min(self.ls_core, key=lambda x: abs(x - self.slider.value()))

            # if FitWindow is visible --> update figFit according to selected core
            global wFit
            try:
                wFit.isVisible()
                wFit = FitWindow(core_select, self.count, self.ls_core, results['O2 profile'], self.dfit, self.dic_deriv,
                                 self.ddata_shift[self.ls_colname[-1]], self.figO2, self.axO2)
            except:
                pass

    def slider_update(self):
        if self.ls_core:
            # allow only discrete values according to existing cores
            core_select = min(self.ls_core, key=lambda x: abs(x - self.slider.value()))

            # update slider position and label
            self.slider.setValue(int(core_select))
            self.sld_label.setText('{}: {}'.format(self.ls_colname[0], core_select))

            # update plot according to selected core
            fig0 = dbs.GUI_baslineShift(data_shift=self.ddata_shift, core=core_select, ls_core=self.ls_core,
                                        fig=self.figO2, ax=self.axO2, plot_col='mV', grp_label=grp_label)
            self.figO2.canvas.draw()

    def slider_update1(self):
        # pre-check whether count status is >= 1:
        if self.count == 0:
            return
        else:
            # allow only discrete values according to existing cores
            core_select = min(self.ls_core, key=lambda x: abs(x - self.slider.value()))

            # update slider position and label
            self.slider.setValue(int(core_select))
            self.sld_label.setText('{}: {}'.format(self.ls_colname[0], core_select))

            # update plot according to selected core
            fig1 = GUI_O2depth(core=core_select, ls_core=self.ls_core, dcore_pen=self.dcore_pen, dobj_hid=dobj_hid,
                               ax=self.axO2, fig=self.figO2)
            self.figO2.canvas.draw()

    def slider_update2(self):
        # allow only discrete values according to existing cores
        core_select = min(self.ls_core, key=lambda x: abs(x - self.slider.value()))

        # update slider position and label
        self.slider.setValue(int(core_select))
        self.sld_label.setText('{}: {}'.format(self.ls_colname[0], core_select))

        # update plot according to selected core
        fig2, mean_ = GUI_penetration_av(core=core_select, ls_core=self.ls_core, dcore_pen=self.dcore_pen,
                                         fig=self.figO2, ax=self.axO2)
        self.figO2.canvas.draw()

    def checkFitWindow(self):
        global wFit
        wFit = FitWindow(self.slider.value(), self.count, self.ls_core, results['O2 profile'], self.dfit, self.dic_deriv,
                         self.ddata_shift, self.figO2, self.axO2)
        if wFit.isVisible():
            pass
        else:
            wFit.show()

    def save_data(self, analyte):
        # make a project folder for the specific analyte if it doesn't exist
        save_path = self.field("Storage path") + '/' + analyte + '_project/'
        if not os.path.exists(save_path):
            os.makedirs(save_path)

        ls_saveData = list()
        [ls_saveData.append(i) for i in self.field('saving parameters').split(',') if 'fig' not in i]
        if len(ls_saveData) > 0:
            # all keys that shall be removed
            ls_removeKey = list()
            [ls_removeKey.append(i) for i in ls_allData if i not in ls_saveData]
            if 'fit_mV' in ls_removeKey:
                ls_removeKey.append('derivative_mV')

            # delete a keys not in that list regardless of whether it is in the dictionary
            [dout.pop(i, None) for i in ls_removeKey]

            # save to excel sheets
            dbs.save_rawExcel(dout=dout, file=self.field("Data"), savePath=save_path)

    def save_figraw(self, save_path, dfigRaw):
        # find the actual running number
        save_folder = dbs._actualFolderName(savePath=save_path, cfolder='rawProfile', rlabel='run')
        if not os.path.exists(save_folder):
            os.makedirs(save_folder)

        for f in dfigRaw.keys():
            for t in ls_figtype:
                name = save_folder + 'rawDepthprofile_core-{}.'.format(f) + t
                dfigRaw[f].savefig(name, bbox_inches='tight', pad_inches=0.1, dpi=dpi)

    def save_figdepth(self, save_path, dfigBase):
        # find the actual running number
        save_folder = dbs._actualFolderName(savePath=save_path, cfolder='DepthProfile', rlabel='run')
        if not os.path.exists(save_folder):
            os.makedirs(save_folder)

        for f in dfigBase.keys():
            for t in ls_figtype:
                name = save_folder + 'Depthprofile_core-{}_SWI_corrected.'.format(f) + t
                dfigBase[f].savefig(name, bbox_inches='tight', pad_inches=0.1, dpi=dpi)

    def save_figFit(self, save_path, dfigFit):
        # find the actual running number
        save_folder = dbs._actualFolderName(savePath=save_path, cfolder='Fit', rlabel='run')
        if not os.path.exists(save_folder):
            os.makedirs(save_folder)

        for f in dfigFit.keys():
            for ff in dfigFit[f].keys():
                for t in ls_figtype:
                    name = save_folder + 'Fit_core-{}_sample-{}.'.format(f, ff) + t
                    dfigFit[f][ff].savefig(name, bbox_inches='tight', pad_inches=0.1, dpi=dpi)

    def save_figPen(self, save_path, dfigPen):
        # find the actual running number
        save_folder = dbs._actualFolderName(savePath=save_path, cfolder='PenetrationDepth', rlabel='run')
        if not os.path.exists(save_folder):
            os.makedirs(save_folder)

        for f in dfigPen.keys():
            for t in ls_figtype:
                name = save_folder + 'PenetrationDepth_core-{}.'.format(f) + t
                dfigPen[f].savefig(name, bbox_inches='tight', pad_inches=0.1, dpi=dpi)

    def save_figure(self, analyte):
        ls_saveFig = list()
        [ls_saveFig.append(i) for i in self.field('saving parameters').split(',') if 'fig' in i]
        if len(ls_saveFig) > 0:
            save_path = self.field("Storage path") + '/Graphs/'
            # make folder "Graphs" if it doesn't exist
            if not os.path.exists(save_path):
                os.makedirs(save_path)

            # make a project folder for the specific analyte if it doesn't exist
            save_path = save_path + analyte + '_project/'
            if not os.path.exists(save_path):
                os.makedirs(save_path)

            # generate images of all all samples (don't plot them)
            [dfigRaw, dfigBase, dfigFit,
             dfigPen] = figures4saving(ls_core=self.ls_core, draw=results['O2 raw data'], ddcore=results['O2 profile'],
                                       deriv=self.dic_deriv, ddata_shift=self.ddata_shift, dfit=self.dfit,
                                       dcore_pen=self.dcore_pen)
            # Depth profiles
            if 'fig raw' in ls_saveFig:
                self.save_figraw(save_path=save_path, dfigRaw=dfigRaw)
            if 'fig adjusted' in ls_saveFig:
                self.save_figdepth(save_path=save_path, dfigBase=dfigBase)
            # Fit profiles
            if 'fig fit' in ls_saveFig:
                if dfigFit:
                    self.save_figFit(save_path=save_path, dfigFit=dfigFit)
            # Penetration depth
            if 'fig penetration' in ls_saveFig:
                if dfigPen:
                    self.save_figPen(save_path=save_path, dfigPen=dfigPen)

    def save(self):
        global dout, dpen_glob
        # preparation - make own function out at the end
        dout = dbs.prep4saveRes(dout=dout, results=results, typeCalib=self.typeCalib, o2_dis=self.o2_dis,
                                temperature=float(self.temperature_edit.text()), pene2=float(self.pene2_edit.text()),
                                salinity=float(self.salinity_edit.text()), dpenStat=dpen_glob)

        # extract saving options for data / figures - according to user input
        self.save_data(analyte='O2')
        self.save_figure(analyte='O2')

        # Information that saving was successful
        msgBox = QMessageBox()
        msgBox.setIcon(QMessageBox.Information)
        msgBox.setText("Selected data are saved successfully.")
        msgBox.setFont(QFont('Helvetica Neue', 11))
        msgBox.setWindowTitle("Successful")
        msgBox.setStandardButtons(QMessageBox.Ok)

        returnValue = msgBox.exec()
        if returnValue == QMessageBox.Ok:
            pass

    def reset_o2page(self):
        global core_select, userCal, ret, dpen_glob
        core_select, userCal, ret, dpen_glob = None, None, None, dict()

        # empty results
        if 'O2 profile' in results.keys():
            results.pop('O2 profile')
        if 'O2 raw data' in results.keys():
            results.pop('O2 raw data')
        if 'O2 fit' in results.keys():
            results.pop('O2 fit')
            results.pop('O2 derivative')
        if 'O2 SWI corrected' in results.keys():
            results.pop('O2 SWI corrected')
        if 'O2 penetration depth' in results.keys():
            results.pop('O2 penetration depth')
        if 'O2 hidden objects' in results.keys():
            results.pop('O2 hidden objects')

        self.salinity_edit.setText(str(results['salinity PSU']))
        self.temperature_edit.setText(str(results['temperature degC']))

        if self.count != 0:
            self.setSubTitle("Start all over again. New attempt, new chances. \nLoad calibration, update parameters if "
                             "required, and press CONTINUE. \n")

            # reset count and reset slider and continue button / status
            self.count = 0
            self.slider.setValue(int(min(self.ls_core)))
            self.sld_label.setText('group: --')
            self.slider.disconnect()
            self.slider.valueChanged.connect(self.slider_update)
            self.continue_button.disconnect()
            self.continue_button.clicked.connect(self.continue_process)
            self.continue_button.setEnabled(True)
            self.checkFit_button.setEnabled(False)

            # clear data
            self.pene2_edit.setText('2.5')
            self.O2_penetration = float(self.pene2_edit.text())
            self.o2_dis, self.dtab_sal = None, None
            self.ls_core, self.data_shift = None, dict()
            dobj_hid.clear()
            dpen_glob.clear()
            dO2_core.clear()

            # clear figure
            self.axO2.cla()
            self.axO2.title.set_text('')
            self.axO2.set_xlabel('O2 / mV'), self.axO2.set_ylabel('Depth / µm')
            self.axO2.invert_yaxis()
            self.figO2.subplots_adjust(bottom=0.2, right=0.95, top=0.9, left=0.15)
            sns.despine()
            self.figO2.canvas.draw()

    def nextId(self) -> int:
        self.ls_page = list(self.field('parameter selected').split(','))
        self.ls_page.remove('o2')
        if len(self.ls_page) != 0:
            if 'ph' in self.field('parameter selected'):
                return wizard_page_index["phPage"]
            else:
                return wizard_page_index["{}Page".format(self.ls_page[0])]
        else:
            return wizard_page_index["charPage"]


class FitWindow(QDialog):
    def __init__(self, sliderValue, cstatus, ls_core, dfCore, dfFit, dfDeriv, data_shift, figO2, axO2):
        super().__init__()
        self.initUI()

        if cstatus > 2:
            self.update_button.setEnabled(False)
            self.adjust_button.setEnabled(False)

        # return current core - and get the samples to plot (via slider selection)
        self.Core = min(ls_core, key=lambda x: abs(x - sliderValue))

        # get the transmitted data
        self.dShift, self.figO2, self.axO2 = data_shift, figO2, axO2
        self.dfCore, self.FitCore, self.DerivCore = dfCore[self.Core], dfFit[self.Core], dfDeriv[self.Core]

        # generate an independent dictionary of cores in case of updateFit is used
        self.dfCoreFit, self.dShiftFit = dict(), dict()
        for c in self.dfCore.keys():
            df_c = pd.DataFrame(np.array(self.dfCore[c]), index=self.dfCore[c].index, columns=self.dfCore[c].columns)
            self.dfCoreFit[c] = df_c

        for c in self.dShift.keys():
            dicS = dict()
            for s in self.dShift[c].keys():
                df_s = pd.DataFrame(np.array(self.dShift[c][s]), index=self.dShift[c][s].index,
                                    columns=self.dShift[c][s].columns)
                dicS[s] = df_s
            self.dShiftFit[c] = dicS

        # plot all samples from current core
        fig3 = plot_Fitselect(core=self.Core, sample=min(self.FitCore.keys()), dfCore=self.dfCore, dfFit=self.FitCore,
                              dfDeriv=self.DerivCore, fig=self.figFit, ax=self.axFit, ax1=self.ax1Fit)
        # connect onclick event with function
        self.ls_out, self.ls_cropx = list(), list()
        self.figFit.canvas.mpl_connect('button_press_event', self.onclick_updateFit)

        # update slider range to number of samples and set to first sample
        self.slider1.setMinimum(int(min(self.FitCore.keys()))), self.slider1.setMaximum(int(max(self.FitCore.keys())))
        self.slider1.setValue(int(min(self.FitCore.keys())))
        self.sld1_label.setText('sample: ' + str(int(min(self.FitCore.keys()))))
        self.chi2.setText('Goodness of fit (reduced χ2): ' + str(round(self.FitCore[int(min(self.FitCore.keys()))][0].redchi, 2)))

        # when slider value change (on click), return new value and update figure plot
        self.slider1.valueChanged.connect(self.slider1_update)
        self.figFit.canvas.draw()

        # connect checkbox and load file button with a function
        self.update_button.clicked.connect(self.updateFit)
        self.adjust_button.clicked.connect(self.adjustData)
        self.save1_button.clicked.connect(self.save_fit)
        self.close_button.clicked.connect(self.close_window)

    def initUI(self):
        self.setWindowTitle("Check fit for depth correction")
        self.setGeometry(650, 50, 600, 300) # x-position, y-position, width, height

        # add description about how to use this window (slider, outlier detection, cropping area)
        self.msg = QLabel("Use the slider to switch between samples belonging to the selected core. \nYou have the "
                          "following options to improve the fit: \n- Trim fit range: press CONTROL/COMMAND + select "
                          "min/max \n- Remove outliers: press SHIFT + select individual points \n\nAt the end,  update"
                          " the fit by pressing the button UPDATE FIT")

        self.msg.setWordWrap(True)

        self.close_button = QPushButton('Fit OK', self)
        self.close_button.setFixedWidth(100)
        self.update_button = QPushButton('update fit', self)
        self.update_button.setFixedWidth(100)
        self.adjust_button = QPushButton('adjust data', self)
        self.adjust_button.setFixedWidth(100)
        self.save1_button = QPushButton('Save', self)
        self.save1_button.setFixedWidth(100)

        # Slider for different cores and label on the right
        self.slider1 = QSlider(Qt.Horizontal)
        self.slider1.setMinimumWidth(350), self.slider1.setFixedHeight(20)
        self.sld1_label = QLabel()
        self.sld1_label.setFixedWidth(70)
        self.sld1_label.setText('sample: --')

        self.chi2_bx = QLabel(self)
        self.chi2_bx.setFixedWidth(75)
        self.chi2 = QLabel()
        self.chi2.setText('Goodness of fit (reduced χ2): --')
        self.chi2.setAlignment(Qt.AlignLeft)

        # creating window layout
        mlayout2 = QVBoxLayout()
        vbox2_top, vbox2_bottom = QHBoxLayout(), QHBoxLayout()
        vbox2_middle, vbox2_middle1 = QHBoxLayout(), QHBoxLayout()
        mlayout2.addLayout(vbox2_top), mlayout2.addLayout(vbox2_middle)
        mlayout2.addLayout(vbox2_middle1), mlayout2.addLayout(vbox2_bottom)

        # plotting area
        self.figFit, self.axFit = plt.subplots(figsize=(5, 3))
        self.ax1Fit = self.axFit.twinx()
        self.figFit.set_facecolor("none")
        self.canvasFit = FigureCanvasQTAgg(self.figFit)
        self.naviFit = NavigationToolbar2QT(self.canvasFit, self)
        self.axFit.set_xlabel('Depth / µm'), self.axFit.set_ylabel('O2 / mV')
        self.ax1Fit.set_ylabel('1st derivative', color='#0077b6')

        self.axFit.invert_yaxis()
        self.figFit.subplots_adjust(bottom=0.2, right=0.95, top=0.9, left=0.15)
        sns.despine()

        # add items to the layout grid
        # top part
        MsgGp = QGroupBox()
        MsgGp.setFont(QFont('Helvetica Neue', 12))
        # MsgGp.setMinimumWidth(300)
        gridMsg = QGridLayout()
        vbox2_top.addWidget(MsgGp)
        MsgGp.setLayout(gridMsg)

        # add GroupBox to layout and load buttons in GroupBox
        gridMsg.addWidget(self.msg, 1, 0)

        # in-between for chi-2
        ChiGp = QGroupBox()
        ChiGp.setFont(QFont('Helvetica Neue', 12))
        ChiGp.setFixedHeight(50)
        gridChi = QGridLayout()
        vbox2_middle.addWidget(ChiGp)
        ChiGp.setLayout(gridChi)

        # add GroupBox to layout and load buttons in GroupBox
        gridChi.addWidget(self.chi2_bx, 1, 0)
        gridChi.addWidget(self.chi2, 1, 1)

        # middle part
        FitGp = QGroupBox("Sigmoidal fit and 1st derivative")
        FitGp.setFont(QFont('Helvetica Neue', 12))
        FitGp.setMinimumWidth(350), FitGp.setMinimumHeight(450)
        gridFit = QGridLayout()
        vbox2_middle1.addWidget(FitGp)
        FitGp.setLayout(gridFit)

        # add GroupBox to layout and load buttons in GroupBox
        gridFit.addWidget(self.slider1, 1, 0)
        gridFit.addWidget(self.sld1_label, 1, 1)
        gridFit.addWidget(self.canvasFit, 2, 0)
        gridFit.addWidget(self.naviFit, 3, 0)

        # bottom part
        BtnGp = QGroupBox()
        # BtnGp.setMinimumWidth(300), \
        BtnGp.setFixedHeight(45)
        gridBtn = QGridLayout()
        vbox2_bottom.addWidget(BtnGp)
        vbox2_bottom.setAlignment(self, Qt.AlignLeft | Qt.AlignTop)
        BtnGp.setLayout(gridBtn)
        gridBtn.addWidget(self.close_button, 1, 0)
        gridBtn.addWidget(self.update_button, 1, 1)
        gridBtn.addWidget(self.adjust_button, 1, 2)
        gridBtn.addWidget(self.save1_button, 1, 3)

        # add everything to the window layout
        self.setLayout(mlayout2)

    def onclick_updateFit(self, event):
        modifiers = QtWidgets.QApplication.keyboardModifiers()
        if modifiers == Qt.ControlModifier:
            # change selected range when control is pressed on keyboard
            # in case there are more than 2 points selected -> clear list and start over again
            if len(self.ls_cropx) >= 2:
                self.ls_cropx.clear()
            self.ls_cropx.append(event.xdata)

            # mark range in grey
            self._markVLine()

        if modifiers == Qt.ShiftModifier:
            # mark outlier when shift is pressed on keyboard
            self.ls_out.append(event.xdata)

    def _markVLine(self):
        # in case too many boundaries are selected, use the minimal/maximal values
        if len(self.ls_cropx) > 2:
            ls_crop = [min(self.ls_cropx), max(self.ls_cropx)]
        else:
            ls_crop = sorted(self.ls_cropx)

        # current core, current sample
        c, s = self.Core, int(self.sld1_label.text().split(' ')[-1])

        # span grey area to mark outside range
        if len(ls_crop) == 1:
            sub = (self.dfCore[s].index[0] - ls_crop[-1], self.dfCore[s].index[-1] - ls_crop[-1])
            if np.abs(sub[0]) < np.abs(sub[1]):
                self.axFit.axvspan(self.dfCore[s].index[0], ls_crop[-1], color='gray', alpha=0.3)  # left outer side
            else:
                self.axFit.axvspan(ls_crop[-1], self.dfCore[s].index[-1], color='gray', alpha=0.3)  # right outer side
        else:
            if ls_crop[-1] < ls_crop[0]:
                self.axFit.axvspan(self.dfCore[s].index[0], ls_crop[-1], color='gray', alpha=0.3)  # left outer side
            else:
                self.axFit.axvspan(ls_crop[-1], self.dfCore[s].index[-1], color='gray', alpha=0.3)  # left outer side

        # draw vertical line to mark boundaries
        [self.axFit.axvline(x, color='k', ls='--', lw=0.5) for x in ls_crop]

        self.figFit.canvas.draw()

    def cropDF(self, s, df):
        if self.ls_cropx:
            # in case there was only 1 point selected -> extend the list to the other end
            if len(self.ls_cropx) == 1:
                sub = (df[s].index[0] - self.ls_cropx[0], df[s].index[-1] - self.ls_cropx[0])
                if np.abs(sub[0]) < np.abs(sub[1]):
                    self.ls_cropx = [self.ls_cropx[0], df[s].index[-1]]
                else:
                    self.ls_cropx = [df[s].index[0], self.ls_cropx[0]]

            # actually crop the depth profile to the area selected.
            # In case more than 2 points have been selected, choose the outer ones
            dcore_crop = df[s].loc[min(self.ls_cropx): max(self.ls_cropx)]
        else:
            dcore_crop = df[s]
        return dcore_crop

    def popOutlier(self, dcore_crop):
        ls_pop = [min(dcore_crop.index.to_numpy(), key=lambda x: abs(x - self.ls_out[p]))
                    for p in range(len(self.ls_out))]

        # drop in case value is still there
        for p in ls_pop:
            if p in dcore_crop.index:
                dcore_crop.drop(p, inplace=True)

        return dcore_crop

    def reFit(self, dcore_crop):
        gmod = Model(dbs._gompertz_curve_adv)
        res, df_fit_crop, df_fitder = dbs.baseline_finder_DF(dic_dcore=dcore_crop, steps=steps, model=gmod, adv=True)

        # update red.chi2
        self.chi2.setText('Goodness of fit (reduced χ2): ' + str(round(res.redchi, 3)))
        return df_fit_crop, df_fitder

    def adjustData(self):
        # it actually adjusts the data in the profile while update fit only uses these data for calculating the swi
        # but does not trim or remove data from the original profile

        # current core, current sample
        c, s = self.Core, int(self.sld1_label.text().split(' ')[-1])

        # crop dataframe to selected range
        dcore_crop = self.cropDF(s=s, df=self.dfCore)

        # pop outliers from depth profile
        if self.ls_out:
            dcore_crop = self.popOutlier(dcore_crop=dcore_crop)

        # re-do fitting - curve fit and baseline finder
        df_fit_crop, df_fitder = self.reFit(dcore_crop=dcore_crop)

        # re-draw fit plot
        fig3 = plot_FitUpdate(core=self.Core, nr=s, dic_dcore=dcore_crop, dfit=df_fit_crop, dic_deriv=df_fitder,
                              ax1=self.ax1Fit, ax=self.axFit, fig=self.figFit)
        self.figFit.canvas.draw()

        # exchange the updated depth profile to the dictionary (to plot all)
        self.dShift[c][s] = pd.DataFrame(np.array(dcore_crop), index=dcore_crop.index - df_fitder.idxmin().values[0],
                                         columns=dcore_crop.columns)
        # plot baseline corrected depth profiles for special sample
        fig0 = dbs.GUI_baslineShiftCore(data_shift=self.dShift[c], core_select=self.Core, plot_col='mV', fig=self.figO2,
                                        ax=self.axO2, grp_label=grp_label)
        self.figO2.canvas.draw()

    def updateFit(self):
        # only uses data for calculating the swi (applying trim, mark outliers, etc.) but does not trim or remove
        # data from the original profile (NO OVERWRITING) while adjust data actually adjusts data in the profile

        # current core, current sample
        c, s = self.Core, int(self.sld1_label.text().split(' ')[-1])

        # crop dataframe to selected range
        dcore_crop = self.cropDF(s=s, df=self.dfCoreFit)
        self.ls_cropx = list()

        # pop outliers from depth profile
        if self.ls_out:
            dcore_crop = self.popOutlier(dcore_crop=dcore_crop)
            self.ls_out = list()

        # re-do fitting - curve fit and baseline finder
        df_fit_crop, df_fitder = self.reFit(dcore_crop=dcore_crop)

        # re-draw fit plot
        fig3 = plot_FitUpdate(core=self.Core, nr=s, dic_dcore=dcore_crop, dfit=df_fit_crop, dic_deriv=df_fitder,
                              ax1=self.ax1Fit, ax=self.axFit, fig=self.figFit)
        self.figFit.canvas.draw()

        # exchange the updated depth profile to the dictionary (to plot all)
        self.dShiftFit[c][s] = pd.DataFrame(np.array(dcore_crop), index=dcore_crop.index - df_fitder.idxmin().values[0],
                                            columns=dcore_crop.columns)
        # update the depth / index of each dataframe according to the identified SWI
        self.dShift[c][s] = pd.DataFrame(np.array(self.dfCore[s]), index=self.dfCore[s].index - df_fitder.idxmin().values[0],
                                            columns=self.dfCore[s].columns)

        # plot baseline corrected depth profiles for special sample
        fig0 = dbs.GUI_baslineShiftCore(data_shift=self.dShift[c], core_select=self.Core, plot_col='mV', fig=self.figO2,
                                        ax=self.axO2, grp_label=grp_label)
        self.figO2.canvas.draw()

    def slider1_update(self):
        # clear lists for another trial
        self.ls_out, self.ls_cropx = list(), list()

        # allow only discrete values according to existing cores
        sample_select = min(self.FitCore.keys(), key=lambda x: abs(x - self.slider1.value()))
        # update slider position and label
        self.slider1.setValue(sample_select)
        self.sld1_label.setText('sample: {}'.format(sample_select))

        # update goodness of fit (red. chi-2 for actual fit)
        #         if round(self.FitCore[int(sample_select)][0].redchi, 3) > gof_accept:
        # self.chi2_bx.setPixmap(self.pixmapB)
        # elif gof_top < round(self.FitCore[int(sample_select)][0].redchi, 3) < gof_accept:
        #     self.chi2_bx.setPixmap(self.pixmapG)
        # else:
        #     self.chi2_bx.setPixmap(self.pixmapP)
        self.chi2.setText('Goodness of fit (reduced χ2): ' + str(round(self.FitCore[int(sample_select)][0].redchi, 3)))

        # update plot according to selected core
        fig3 = plot_Fitselect(core=self.Core, sample=sample_select, dfCore=self.dfCore, dfFit=self.FitCore,
                              dfDeriv=self.DerivCore, fig=self.figFit, ax=self.axFit, ax1=self.ax1Fit)
        # fig3.canvas.mpl_connect('button_press_event', self.onclick)
        self.figFit.canvas.draw()

    def close_window(self):
        self.hide()

    def save_fit(self):
        # !!! TODO: enable saving of fit figures
        print('enable saving of the fit figures')


class CalibCore(QDialog):
    def __init__(self, ls_core):
        super().__init__()

        # setting title
        self.setWindowTitle("Core selection ")
        self.setGeometry(100, 100, 350, 100)

        # getting the parameter
        self.ls_core = ls_core

        # calling method
        self.initUI()

        # connect checkbox and load file button with a function
        self.ok_button.clicked.connect(self.close)

        # showing all the widgets
        self.show()

    # method for widgets
    def initUI(self):
        # calibration of one core applied to all others -> select core
        self.combo_box = QComboBox(self)

        self.ok_button = QPushButton('OK', self)
        self.ok_button.setFixedWidth(100)

        # core list
        core_str = ['core ' + str(i) for i in sorted(self.ls_core)]
        self.combo_box.addItems(core_str)
        self.combo_box.setEditable(True)
        self.combo_box.setInsertPolicy(QComboBox.InsertAlphabetically)

        # creating label to  print the policy
        label = QLabel("Select core that shall be used for recalibration:", self)
        label.setWordWrap(True)

        # creating window layout
        mlayout2 = QVBoxLayout()
        vbox2 = QHBoxLayout()
        mlayout2.addLayout(vbox2)

        # add items to the layout grid
        MsgGp = QGroupBox()
        MsgGp.setFont(QFont('Helvetica Neue', 12))
        gridMsg = QGridLayout()
        vbox2.addWidget(MsgGp)
        MsgGp.setLayout(gridMsg)

        # add GroupBox to layout and load buttons in GroupBox
        gridMsg.addWidget(label, 0, 0)
        gridMsg.addWidget(self.combo_box, 0, 1)
        gridMsg.addWidget(self.ok_button, 1, 1)

        # add everything to the window layout
        self.setLayout(mlayout2)

    def close(self):
        global core_select
        core_select = int(self.combo_box.currentText().split(' ')[1])
        self.hide()


def figures4saving(ls_core, draw=None, ddata_shift=None, ddcore=None, dfit=None, deriv=None, dcore_pen=None):
    dfigRaw, dfigBase, dfigFit, dfigProf, dfigPen = dict(), dict(), dict(), dict(), dict()
    for c in ls_core:
        # raw data
        if draw:
            dfigRaw[c] = dbs.GUI_rawProfile(O2data=draw, core=c, show=False, ls_core=ls_core, grp_label=grp_label)

        # SWI corrected
        if ddata_shift:
            dfigBase[c] = dbs.GUI_baslineShift(data_shift=ddata_shift, grp_label=grp_label, core=c, show=False,
                                               ls_core=ls_core, plot_col='mV')
        # Fit plots
        dfigFitS = dict()
        if ddcore:
            for s in ddcore[c].keys():
                dfigFitS[s] = GUI_FitDepth(core=c, nr=s, dfCore=ddcore[c], dfFit=dfit[c], dfDeriv=deriv[c], show=False)
            dfigFit[c] = dfigFitS
        # indicated penetration depth
        if dcore_pen:
            dfigPen[c] = GUI_penetration_av(core=c, ls_core=ls_core, dcore_pen=dcore_pen, show=False)[0]
    return dfigRaw, dfigBase, dfigFit, dfigPen


def plot_Fitselect(core, sample, dfCore, dfFit, dfDeriv, fig, ax, ax1):
    fig3 = GUI_FitDepth(core=core, nr=sample, dfCore=dfCore, dfFit=dfFit, dfDeriv=dfDeriv, fig=fig, ax=ax, ax1=ax1)
    fig3.canvas.draw()
    return fig3


def plot_FitUpdate(core, nr, dic_dcore, dfit, dic_deriv, fig, ax, ax1):
    # clear coordinate system but keep the labels
    ax.cla(), ax1.cla()
    ax.title.set_text('Fit characteristics for {} {} - sample {}'.format(grp_label, core, nr))
    ax.set_xlabel('Depth / µm'), ax.set_ylabel('O2 / mV'), ax1.set_ylabel('1st derivative', color='#0077b6')

    # plotting part
    c = 'O2_mV' if 'O2' in dic_dcore.columns else dic_dcore.columns[0]
    ax.plot(dic_dcore.index, dic_dcore[c], lw=0, marker='o', ms=4, color='k')
    ax.plot(dfit[dfit.columns[0]], lw=0.75, ls=':', color='k')

    ax1.plot(dic_deriv, lw=1., color='#0077b6')
    ax1.axvline(dic_deriv.idxmin().values[0], ls='-.', color='darkorange', lw=1.5)

    # text annotation to indicate depth correction
    text = 'surface level \nat {:.1f}µm'
    c = 'O2_mV' if 'O2' in dic_dcore.columns else dic_dcore.columns[0]
    ax.text(dic_dcore[c].index[-1] * 0.6, dic_dcore[c].max() * 0.5,
            text.format(dic_deriv.idxmin().values[0]), ha="left", va="center", color='k', size=9.5,
            bbox=dict(fc='lightgrey', alpha=0.25))

    # general layout
    sns.despine()
    ax.spines['right'].set_visible(True)
    plt.tight_layout(pad=0.75)
    fig.canvas.draw()
    return fig


def GUI_FitDepth(core, nr, dfCore, dfFit, dfDeriv, fig=None, ax=None, ax1=None, show=True):
    plt.ioff()
    # initialize figure plot
    if ax is None:
        fig, ax = plt.subplots(figsize=(5, 3))
        ax1 = ax.twinx()
    else:
        ax.cla(), ax1.cla()

    if core != 0:
        ax.title.set_text('Fit characteristics for {} {} - sample {}'.format(grp_label, core, nr))
        ax.set_xlabel('Depth / µm'), ax.set_ylabel('O2 / mV'), ax1.set_ylabel('1st derivative', color='#0077b6')

    # plotting part
    c = 'O2_mV' if 'O2' in dfCore[nr].columns else dfCore[nr].columns[0]
    ax.plot(dfCore[nr].index, dfCore[nr][c], lw=0, marker='o', ms=4, color='k')
    ax.plot(dfFit[nr][1], lw=0.75, ls=':', color='k')
    ax1.plot(dfDeriv[nr][0], lw=1., color='#0077b6')
    ax1.axvline(dfFit[nr][2], ls='-.', color='darkorange', lw=1.5)

    # text annotation for sediment water interface depth correction
    text = 'surface level \nat {:.1f}µm'
    c = 'O2_mV' if 'O2' in dfCore[nr].columns else dfCore[nr].columns[0]
    ax.text(dfCore[nr][c].index[-1] * 0.6, dfCore[nr][c].max() * 0.5, text.format(dfFit[nr][2]), ha="left",
            va="center", color='k', size=9.5, bbox=dict(fc='lightgrey', alpha=0.25))

    # general layout
    ax.set_xlim(dfCore[nr].index[0]*1.05, dfCore[nr].index[-1]*1.05)
    sns.despine(), ax.spines['right'].set_visible(True)
    plt.tight_layout(pad=1.)

    if show is False:
        plt.close(fig)
    else:
        fig.canvas.draw()
    return fig


def GUI_O2depth(core, ls_core, dcore_pen, dobj_hid, fig, ax):
    ax.cla()
    lines = list()
    # identify closest value in list
    core_select = dbs.closest_core(ls_core=ls_core, core=core)

    # initialize figure plot
    if ax is None:
        fig, ax = plt.subplots(figsize=(3, 4))
    if core_select != 0:
        ax.title.set_text('Fit depth profile for {} {}'.format(grp_label, core_select))
    ax.set_xlabel('O2 concentration / µmol/L'), ax.set_ylabel('Depth / µm')
    ax.invert_yaxis()

    if core_select != 0:
        ax.axhline(0, lw=.5, color='k')
        df = pd.concat([dcore_pen[core_select]['{}-Fit'.format(s[0])] for s in dO2_core[core_select].keys()], axis=1)
        df.columns = [i[0] for i in dO2_core[core_select].keys()]

        # plot depending whether some samples have already been excluded
        for en, s in enumerate(df.columns):
            if core_select in dobj_hid.keys():
                # if s in dictionary of hidden samples, set alpha_ as .1 else as .6
                alpha_ = .0 if 'sample-' + str(s) in dobj_hid[core_select] else .6
            else:
                alpha_ = .6
            d = df[s].dropna()
            line, = ax.plot(d, d.index, color=ls_col[en], lw=1., alpha=alpha_, label='sample-' + str(s))
            lines.append(line)
        leg = ax.legend(frameon=True, fancybox=True, fontsize=fs_*0.8)

        # ------------------------------------------------------------------
        # combine legend
        lined = dict()
        for legline, origline in zip(leg.get_lines(), lines):
            legline.set_picker(5)  # 5 pts tolerance
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

        # Call click func
        fig.canvas.mpl_connect('pick_event', onpick)

        # layout
        ax.set_xlim(-10, df.max().max() * 1.05), ax.set_ylim(df.idxmin().max() * 1.05, df.idxmax().min() * 1.05)
    return fig


def GUI_calcO2penetration(O2_pen, unit, steps, gmod):
    dcore_pen, dcore_fig = dict(), dict()
    for core in dO2_core.keys():
        dic_pen, dfig_pen = dict(), dict()
        for s in dO2_core[core].keys():
            df_fit = dbs.penetration_depth(df=dO2_core[core][s[0]].dropna(), unit=unit, steps=steps, model=gmod,
                                           adv=False)
            dic_pen[str(s[0]) + '-Fit'] = df_fit
            [fig, depth_pen] = dbs.plot_penetrationDepth(core=core, s=s[0], df_fit=df_fit, O2_pen=O2_pen, unit=unit,
                                                         show=False)
            dic_pen[str(s[0]) + '-penetration'] = depth_pen
            dfig_pen[int(s[0])] = fig
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


def av_penetrationDepth(core_select, ls_remain):
    mean_ = (dpen_glob['Depth / µm'].loc[core_select].loc[ls_remain].mean(),
             dpen_glob['O2_µmol/L'].loc[core_select].loc[ls_remain].mean())
    std_ = (dpen_glob['Depth / µm'].loc[core_select].loc[ls_remain].std(),
            dpen_glob['O2_µmol/L'].loc[core_select].loc[ls_remain].std())

    # update dpen_glob
    dpen_glob['Depth / µm'].loc[core_select].loc['mean'] = mean_[0]
    dpen_glob['O2_µmol/L'].loc[core_select].loc['mean'] = mean_[1]
    dpen_glob['Depth / µm'].loc[core_select].loc['std'] = std_[0]
    dpen_glob['O2_µmol/L'].loc[core_select].loc['std'] = std_[1]
    return mean_, std_


def _supplPlot(core_select):
    # samples that should not be included in averaging
    ls_shid = [int(i.split('-')[1]) for i in dobj_hid[core_select]] if core_select in dobj_hid.keys() else list()

    # all samples for core
    ls_sind = list()
    [ls_sind.append(i) for i in dpen_glob['Depth / µm'].loc[core_select].index if i != 'mean' and i != 'std']

    # remaining samples for average penetration depth
    ls_remain = list()
    [ls_remain.append(i) for i in ls_sind if i not in ls_shid]
    return ls_remain


def GUI_penetration_av(core, ls_core, dcore_pen, fig=None, ax=None, show=True):
    plt.ioff()

    # identify closest value in list
    core_select = dbs.closest_core(ls_core=ls_core, core=core)

    # initialize figure plot
    if ax is None:
        fig, ax = plt.subplots(figsize=(3, 4))
    else:
        ax.cla()
    ax.set_xlabel('O2 / mV'), ax.set_ylabel('Depth / µm')
    ax.invert_yaxis()

    # indicate baseline
    if core_select != 0:
        ax.axhline(0, lw=0.75, color='k')

    if core_select != 0:
        # preparation for plot - remaining samples for average penetration depth calculation
        ls_remain = _supplPlot(core_select=core_select)

        # re-plot only the ones that are shown
        df = pd.concat([dcore_pen[core_select]['{}-Fit'.format(s[0])] for s in dO2_core[core_select].keys()], axis=1)
        df.columns = [i[0] for i in dO2_core[core].keys()]
        for en, s in enumerate(df.columns):
            if s in ls_remain:
                d = df[s].dropna()
                ax.plot(d, d.index, color=ls_col[en], lw=1., alpha=0.5, label='sample-' + str(s))
        ax.legend(frameon=True, fancybox=True, fontsize=fs_*0.8)

        # indicate penetration depth mean + std according to visible curves
        mean_, std_ = av_penetrationDepth(core_select=core_select, ls_remain=ls_remain)
        ax.axhline(mean_[0], ls=':', color='crimson')
        ax.fill_betweenx([mean_[0] - std_[0], mean_[0] + std_[0]], -50, 500, lw=0, alpha=0.5, color='grey')
        ax.axvline(mean_[1], ls=':', color='crimson')
        ax.fill_between([mean_[1] - std_[1], mean_[1] + std_[1]], -5000, 5000, lw=0, alpha=0.5, color='grey')

        # layout
        ax.set_xlim(-10, df.max().max() * 1.05), ax.set_ylim(df.idxmin().max() * 1.05, df.idxmax().min() * 1.05)
        ax.set_ylabel('Depth / µm'), ax.set_xlabel('O2 concentration ' + 'µmol/L')

        # include mean depth in title
        if core_select == 0 or not dcore_pen:
            pass
        else:
            ax.title.set_text('Average penetration depth for {} {}: {:.0f} ± {:.0f}µm'.format(grp_label, core_select,
                                                                                              mean_[0], std_[0]))
        if show is False:
            plt.close(fig)
        else:
            fig.canvas.draw()
    return fig, mean_


# -----------------------------------------------
class phPage(QWizardPage):
    def __init__(self, parent=None):
        super(phPage, self).__init__(parent)

        self.setTitle("pH depth profile")
        self.setSubTitle("Initially,  the pH profile will be plotted without any depth correction. "
                         "\nHowever, it can be adjusted later.  Press PLOT to start.\n")
        self.initUI()

        # connect checkbox and load file button with a function
        self.continuepH_button.clicked.connect(self.continue_pH)
        self.adjustpH_button.clicked.connect(self.adjust_pH)
        self.savepH_button.clicked.connect(self.save_pH)
        self.resetpH_button.clicked.connect(self.reset_pHpage)
        self.updatepH_button.clicked.connect(self.swi_correctionpH)

    def initUI(self):
        # manual baseline correction
        swi_label, swi_unit_label = QLabel(self), QLabel(self)
        swi_label.setText('Actual correction: '), swi_unit_label.setText('µm')
        self.swi_edit = QLineEdit(self)
        self.swi_edit.setValidator(QDoubleValidator()), self.swi_edit.setAlignment(Qt.AlignRight)
        self.swi_edit.setMaximumWidth(100), self.swi_edit.setText('--'), self.swi_edit.setEnabled(False)

        # option to select the SWI (baseline) from the O2 calculations in case O2 was selected
        #self.swipH_box = QCheckBox('SWI from O2 analysis', self)
        #self.swipH_box.setFont(QFont('Helvetica Neue', fs_font))
        #self.swipH_box.setVisible(True), self.swipH_box.setEnabled(False)

        # Action button
        self.savepH_button = QPushButton('Save', self)
        self.savepH_button.setFixedWidth(100), self.savepH_button.setFont(QFont('Helvetica Neue', fs_font))
        self.continuepH_button = QPushButton('Plot', self)
        self.continuepH_button.setFixedWidth(100), self.continuepH_button.setFont(QFont('Helvetica Neue', fs_font))
        self.adjustpH_button = QPushButton('Adjustments', self)
        self.adjustpH_button.setFixedWidth(100), self.adjustpH_button.setEnabled(False)
        self.adjustpH_button.setFont(QFont('Helvetica Neue', fs_font))
        self.updatepH_button = QPushButton('Update SWI', self)
        self.updatepH_button.setFixedWidth(100), self.updatepH_button.setEnabled(False)
        self.updatepH_button.setFont(QFont('Helvetica Neue', fs_font))
        self.resetpH_button = QPushButton('Reset', self)
        self.resetpH_button.setFixedWidth(100), self.resetpH_button.setFont(QFont('Helvetica Neue', fs_font))

        # Slider for different cores and label on the right
        self.sliderpH = QSlider(Qt.Horizontal)
        self.sliderpH.setMinimumWidth(350), self.sliderpH.setFixedHeight(20)
        self.sldpH_label = QLabel()
        self.sldpH_label.setFixedWidth(55)
        self.sldpH_label.setText('group: --')

        # creating window layout
        w2 = QWidget(self)
        mlayout2 = QVBoxLayout(w2)
        vbox1_top, vbox1_middle, vbox1_bottom = QHBoxLayout(), QHBoxLayout(), QVBoxLayout()
        mlayout2.addLayout(vbox1_top), mlayout2.addLayout(vbox1_middle), mlayout2.addLayout(vbox1_bottom)

        swiarea = QGroupBox("Correction of surface water interface (SWI)")
        swiarea.setMinimumHeight(100)
        grid_swi = QGridLayout()
        swiarea.setFont(QFont('Helvetica Neue', fs_font))
        vbox1_top.addWidget(swiarea)
        swiarea.setLayout(grid_swi)

        # include widgets in the layout
        grid_swi.addWidget(swi_label, 0, 0)
        grid_swi.addWidget(self.swi_edit, 0, 1)
        grid_swi.addWidget(swi_unit_label, 0, 2)
        # grid_swi.addWidget(self.swipH_box, 0, 3)
        grid_swi.addWidget(self.updatepH_button, 0, 3)
        grid_swi.addWidget(self.continuepH_button, 1, 0)
        grid_swi.addWidget(self.adjustpH_button, 1, 1)
        grid_swi.addWidget(self.resetpH_button, 1, 2)
        grid_swi.addWidget(self.savepH_button, 1, 3)

        # draw additional "line" to separate parameters from plots and to separate navigation from rest
        vline = QFrame()
        vline.setFrameShape(QFrame.HLine | QFrame.Raised)
        vline.setLineWidth(2)
        vbox1_middle.addWidget(vline)

        # plotting area
        self.figpH, self.axpH = plt.subplots(figsize=(3, 2))
        self.canvaspH = FigureCanvasQTAgg(self.figpH)
        self.axpH.set_xlabel('pH value'), self.axpH.set_ylabel('Depth / µm')
        self.axpH.invert_yaxis()
        self.figpH.tight_layout(pad=.5)
        sns.despine()

        pH_group = QGroupBox("pH depth profile")
        pH_group.setMinimumHeight(350)
        grid_pH = QGridLayout()

        # add GroupBox to layout and load buttons in GroupBox
        vbox1_bottom.addWidget(pH_group)
        pH_group.setLayout(grid_pH)
        grid_pH.addWidget(self.sliderpH, 1, 0)
        grid_pH.addWidget(self.sldpH_label, 1, 1)
        grid_pH.addWidget(self.canvaspH, 2, 0)
        self.setLayout(mlayout2)

    def enablePlot_swiBox(self):
        if self.status_pH == 1:
            if self.swipH_box.checkState() == 0:
                self.continuepH_button.setEnabled(True), self.swi_edit.setEnabled(True)
            else:
                self.continuepH_button.setEnabled(False)# , self.swi_edit.setEnabled(False)

    def load_pHdata(self):
        # raw measurement file pre-processed and saved per default as rawData file
        dsheets, dignore = _loadGlobData(file_str=self.field("Data"))
        for k in dignore.keys():
            if 'pH' in dignore[k].keys():
                l = k

        # pre-check whether pH_all in sheet names
        sheet_select = dbs.sheetname_check(dsheets, para='pH')
        checked = checkDatavsPara(sheet_select, par='pH')

        if checked is True:
            #  prepare file depending on the type
            ddata = dsheets[sheet_select].set_index('Nr')

            # remove excluded profiles
            ddata_update = _excludeProfiles(analyt='pH', dignore=dignore[l], ddata=ddata)

            global grp_label
            if grp_label is None:
                grp_label = ddata_update.columns[0]

            # list all available cores for pH sheet
            self.ls_core = list(dict.fromkeys(ddata_update[ddata_update.columns[0]]))

            # import all measurements for given parameter
            [dpH_core, ls_nr,
             self.ls_colname] = dbs.load_measurements(dsheets=ddata_update, ls_core=self.ls_core, para=sheet_select)
            results['pH profile raw data'], results['pH adjusted'] = dpH_core, dpH_core.copy()
        else:
            # reset page as nothing was found
            self.reset_pHpage()
        return checked

    def continue_pH(self):
        self.setSubTitle("Now,  the SWI can be set.  Either choose the depth determined in the O2 project,  or set "
                         "your own depth wisely.  Press PLOT to continue. \n")

        # set status for process control
        self.status_pH = 0

        # load data
        checked = self.load_pHdata()

        if checked is True:
            # adjust all the core plots to the same x-scale
            dic_raw = results['pH profile raw data']
            dfpH_scale = pd.concat([pd.DataFrame([(dic_raw[c][n]['pH'].min(), dic_raw[c][n]['pH'].max())
                                                  for n in dic_raw[c].keys()]) for c in dic_raw.keys()])
            self.scale0 = dfpH_scale[0].min(), dfpH_scale[1].max()
            self.scale = self.scale0
            # plot the pH profile for the first core
            figpH0 = plot_pHProfile(data_pH=dic_raw, core=min(self.ls_core), ls_core=self.ls_core, scale=self.scale,
                                    fig=self.figpH, ax=self.axpH)
            self.figpH.canvas.draw()

            # slider initialized to first core
            self.sliderpH.setMinimum(int(min(self.ls_core))), self.sliderpH.setMaximum(int(max(self.ls_core)))
            self.sliderpH.setValue(int(min(self.ls_core)))
            self.sldpH_label.setText('{}: {}'.format(self.ls_colname[0], int(min(self.ls_core))))

            # when slider value change (on click), return new value and update figure plot
            self.sliderpH.valueChanged.connect(self.sliderpH_update)

            # update continue button to "update" in case the swi shall be updated
            self.swi_edit.setEnabled(True), self.updatepH_button.setEnabled(True)
            self.adjustpH_button.setEnabled(True)
            self.continuepH_button.disconnect()
            self.continuepH_button.clicked.connect(self.continue_pHII)

    def continue_pHII(self):
        # update status for process control
        self.status_pH += 1

        # identify closest value in list
        core_select = dbs.closest_core(ls_core=self.ls_core, core=self.sliderpH.value())

        # plot the pH profile for the first core
        if core_select in scalepH.keys():
            scale_plot = self.scale0 if len(scalepH[core_select]) == 0 else scalepH[core_select]
        else:
            scale_plot = self.scale0
        figpH0 = plot_pHProfile(data_pH=results['pH adjusted'], core=core_select, ls_core=self.ls_core, scale=scale_plot,
                                ls='-', fig=self.figpH, ax=self.axpH)
        self.figpH.canvas.draw()

        # slider initialized to first core - connect to valueChanged
        self.sliderpH.setValue(int(core_select)), self.sldpH_label.setText('{}: {}'.format(self.ls_colname[0],
                                                                                           int(core_select)))
        self.sliderpH.valueChanged.connect(self.sliderpH_update)

    def swi_correctionpH(self):
        # update the status for layout in plot
        self.status_pH = 1.

        # identify closest value in list
        core_select = min(self.ls_core, key=lambda x: abs(x - self.sliderpH.value()))

        # update information about actual correction of pH profile
        if '--' in self.swi_edit.text():
            results['pH swi depth'] = dict({core_select: 0.})
        elif 'pH swi depth' in results.keys():
            if core_select in results['pH swi depth'].keys():
                results['pH swi depth'][core_select] += float(self.swi_edit.text())
            else:
                dic1 = dict({core_select: float(self.swi_edit.text())})
                results['pH swi depth'].update(dic1)
        else:
            results['pH swi depth'] = dict({core_select: float(self.swi_edit.text())})

        if '--' in self.swi_edit.text() or len(self.swi_edit.text()) == 0:
            pass
        else:
            # correction of manually selected baseline
            dadj = dict()
            for s in results['pH adjusted'][core_select].keys():
                ynew = results['pH adjusted'][core_select][s].index - float(self.swi_edit.text())
                dadj[s] = pd.DataFrame(results['pH adjusted'][core_select][s].to_numpy(), index=ynew,
                                       columns=results['pH adjusted'][core_select][s].columns)
            results['pH adjusted'][core_select] = dadj

        # update plot accordingly
        if core_select in scalepH.keys():
            scale_plot = self.scale0 if len(scalepH[core_select]) == 0 else scalepH[core_select]
        else:
            scale_plot = self.scale0
        figpH0 = plot_pHProfile(data_pH=results['pH adjusted'], core=core_select, ls_core=self.ls_core, ls='-',
                                scale=scale_plot, fig=self.figpH, ax=self.axpH)
        self.figpH.canvas.draw()

        # slider initialized to first core
        self.sliderpH.setValue(int(core_select)), self.sldpH_label.setText('{}: {}'.format(self.ls_colname[0],
                                                                                           int(core_select)))
        # when slider value change (on click), return new value and update figure plot
        self.sliderpH.valueChanged.connect(self.sliderpH_update)

    def sliderpH_update(self):
        if self.ls_core:
            # allow only discrete values according to existing cores
            core_select = min(self.ls_core, key=lambda x: abs(x - self.sliderpH.value()))

            # update slider position and label
            self.sliderpH.setValue(int(core_select))
            self.sldpH_label.setText('{}: {}'.format(self.ls_colname[0], core_select))

            # update plot according to selected core
            if core_select in scalepH.keys():
                scale_plot = self.scale0 if len(scalepH[core_select]) == 0 else scalepH[core_select]
            else:
                scale_plot = self.scale0
            ls = '-.' if self.status_pH < 1 else '-'
            figpH0 = plot_pHProfile(data_pH=results['pH adjusted'], core=core_select, ls_core=self.ls_core, ls=ls,
                                    scale=scale_plot, fig=self.figpH, ax=self.axpH)
            self.figpH.canvas.draw()

    def adjust_pH(self):
        # open dialog window to adjust data presentation
        global wAdjust
        wAdjust = AdjustpHWindow(self.sliderpH.value(), self.ls_core, self.scale, self.figpH, self.axpH, self.status_pH)
        if wAdjust.isVisible():
            pass
        else:
            wAdjust.show()

    def save_pH(self):
        # make a project folder for the specific analyte if it doesn't exist
        save_path = self.field("Storage path") + '/pH_project/'
        if not os.path.exists(save_path):
            os.makedirs(save_path)

        # save data and figures
        self.save_pHdata(save_path=save_path)
        self.save_pHfigures()

        # Information about successful saving
        msgBox = QMessageBox()
        msgBox.setIcon(QMessageBox.Information)
        msgBox.setText("Selected data are saved successfully.")
        msgBox.setFont(QFont('Helvetica Neue', 11))
        msgBox.setWindowTitle("Successful")
        msgBox.setStandardButtons(QMessageBox.Ok)

        returnValue = msgBox.exec()
        if returnValue == QMessageBox.Ok:
            pass

    def save_pHdata(self, save_path):
        dout_pH = dict()
        # for an external function
        ls_saveData = list()
        [ls_saveData.append(i) for i in self.field('saving parameters').split(',') if 'fig' not in i]
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
        dbs.save_rawExcel(dout=dout_pH, file=self.field("Data"), savePath=save_path)

    def save_pHfigures(self):
        # create folder for figure output
        ls_saveFig = list()
        [ls_saveFig.append(i) for i in self.field('saving parameters').split(',') if 'fig' in i]
        if len(ls_saveFig) > 0:
            save_path = self.field("Storage path") + '/Graphs/'
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
                    fig = plot_pHProfile(data_pH=results['pH profile raw data'], core=c, scale=None, ls='-.',
                                         show=False, ls_core=list(results['pH profile raw data'].keys()))
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
                                         ls_core=list(results['pH adjusted'].keys()))
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

    def reset_pHpage(self):
        self.setSubTitle("Initially,  the pH profile will be plotted without any depth correction. "
                         "\nHowever, it can be adjusted later.  Press PLOT to start.\n")

        if 'pH profile raw data' in results.keys():
            results.pop('pH profile raw data')
        if 'pH swi adjusted' in results.keys():
            results.pop('pH swi adjusted')
        if 'pH swi depth' in results.keys():
            results.pop('pH swi depth')
        if 'pH swi corrected' in results.keys():
            results.pop('pH swi corrected')
        if 'pH adjusted' in results.keys():
            results.pop('pH adjusted')

        # update status for process control
        global scalepH
        scalepH = dict()
        self.status_pH = 0
        self.scale, self.scale0 = None, None

        # connect plot button to first part
        self.continuepH_button.disconnect()
        self.continuepH_button.clicked.connect(self.continue_pH)
        self.continuepH_button.setEnabled(True)
        self.adjustpH_button.setEnabled(False)
        self.updatepH_button.setEnabled(False)
        self.swi_edit.setEnabled(False)

        # reset slider
        self.count = 0
        self.sliderpH.setValue(int(min(self.ls_core)))
        self.sldpH_label.setText('group: --')
        self.sliderpH.disconnect()
        self.sliderpH.valueChanged.connect(self.sliderpH_update)

        # clear pH range (scale), SWI correction
        self.swi_edit.setText('--')

        # empty figure
        self.axpH.cla()
        self.axpH.set_xlabel('pH value'), self.axpH.set_ylabel('Depth / µm')
        self.axpH.invert_yaxis()
        self.figpH.tight_layout(pad=1.5)
        sns.despine()
        self.figpH.canvas.draw()

    def nextId(self) -> int:
        self.ls_page = list(self.field('parameter selected').split(','))
        if 'o2' in self.ls_page:
            self.ls_page.remove('o2')
        self.ls_page.remove('ph')
        if len(self.ls_page) != 0 and 'h2s' in self.field('parameter selected'):
            return wizard_page_index["h2sPage"]
        elif len(self.ls_page) != 0 and 'ep' in self.field('parameter selected'):
            return wizard_page_index["epPage"]
        else:
            return wizard_page_index["charPage"]


class AdjustpHWindow(QDialog):
    def __init__(self, sliderValue, ls_core, scale, figpH, axpH, status_pH):
        super().__init__()
        self.initUI()

        # return current core - and get the samples to plot (via slider selection)
        self.Core = min(ls_core, key=lambda x: abs(x - sliderValue))

        # get the transmitted data
        self.figpH, self.axpH, self.scaleS0, self.status_pH = figpH, axpH, scale, status_pH

        # plot all samples from current core
        fig = plot_adjustpH(core=self.Core, sample=min(results['pH adjusted'][self.Core].keys()), scale=self.scaleS0,
                            dfCore=results['pH adjusted'][self.Core], fig=self.figpHs, ax=self.axpHs)
        # set the range for pH
        self.pHtrim_edit.setText(str(round(self.scaleS0[0], 2)) + ' - ' + str(round(self.scaleS0[1], 2)))

        # connect onclick event with function
        self.ls_out, self.ls_cropy = list(), list()
        self.figpHs.canvas.mpl_connect('button_press_event', self.onclick_updatepH)

        # update slider range to number of samples and set to first sample
        self.slider1pH.setMinimum(int(min(results['pH adjusted'][self.Core].keys())))
        self.slider1pH.setMaximum(int(max(results['pH adjusted'][self.Core].keys())))
        self.slider1pH.setValue(int(min(results['pH adjusted'][self.Core].keys())))
        self.sldpH1_label.setText('sample: ' + str(int(min(results['pH adjusted'][self.Core].keys()))))

        # when slider value change (on click), return new value and update figure plot
        self.slider1pH.valueChanged.connect(self.slider1pH_update)
        self.figpHs.canvas.draw()

        # connect checkbox and load file button with a function
        self.scale = list()
        self.adjust_button.clicked.connect(self.adjustpH)
        self.reset_button.clicked.connect(self.resetPlot)
        self.close_button.clicked.connect(self.close_window)

    def initUI(self):
        self.setWindowTitle("Adjustment of data presentation")
        self.setGeometry(650, 75, 500, 600) # x-position, y-position, width, height

        # add description about how to use this window (slider, outlier detection, trim range)
        self.msg = QLabel("Use the slider to switch between samples belonging to the selected core. \nYou have the "
                          "following options to improve the fit: \n- Trim pH range (y-axis): press CONTROL/COMMAND + "
                          "select min/max \n- Remove outliers: press SHIFT + select individual points \n\nAt the end, "
                          "update the plot by pressing the button ADJUST.")
        self.msg.setWordWrap(True), self.msg.setFont(QFont('Helvetica Neue', int(fs_font*1.25)))

        # Slider for different cores and label on the right
        self.slider1pH = QSlider(Qt.Horizontal)
        self.slider1pH.setMinimumWidth(350), self.slider1pH.setFixedHeight(20)
        self.sldpH1_label = QLabel()
        self.sldpH1_label.setFixedWidth(70), self.sldpH1_label.setText('sample: --')

        # plot individual sample
        self.figpHs, self.axpHs = plt.subplots(figsize=(3, 2))
        self.figpHs.set_facecolor("none")
        self.canvaspHs = FigureCanvasQTAgg(self.figpHs)
        self.navipHs = NavigationToolbar2QT(self.canvaspHs, self)
        self.axpHs.set_xlabel('pH value'), self.axpHs.set_ylabel('Depth / µm')
        self.axpHs.invert_yaxis()
        self.figpHs.subplots_adjust(bottom=0.2, right=0.95, top=0.9, left=0.15)
        sns.despine()

        # define pH range
        pHtrim_label = QLabel(self)
        pHtrim_label.setText('pH range: '), pHtrim_label.setFont(QFont('Helvetica Neue', 12))
        self.pHtrim_edit = QLineEdit(self)
        self.pHtrim_edit.setValidator(QRegExpValidator()), self.pHtrim_edit.setAlignment(Qt.AlignRight)
        self.pHtrim_edit.setMaximumHeight(int(fs_font*1.5))

        # swi correction for individual sample
        swiSample_label = QLabel(self)
        swiSample_label.setText('SWI correction sample: '), swiSample_label.setFont(QFont('Helvetica Neue', 12))
        self.swiSample_edit = QLineEdit(self)
        self.swiSample_edit.setValidator(QDoubleValidator()), self.swiSample_edit.setAlignment(Qt.AlignRight)
        self.swiSample_edit.setMaximumHeight(int(fs_font * 1.5)), self.swiSample_edit.setText('--')

        # actual range from previous window: self.swi_edit.setText('--')

        # close the window again
        self.close_button = QPushButton('OK', self)
        self.close_button.setFixedWidth(100)
        self.adjust_button = QPushButton('Adjust', self)
        self.adjust_button.setFixedWidth(100)
        self.reset_button = QPushButton('Reset', self)
        self.reset_button.setFixedWidth(100)

        # create grid and groups
        mlayout2 = QVBoxLayout()
        vbox2_top, vbox2_bottom, vbox2_middle = QHBoxLayout(), QHBoxLayout(), QVBoxLayout()
        mlayout2.addLayout(vbox2_top), mlayout2.addLayout(vbox2_middle), mlayout2.addLayout(vbox2_bottom)

        # add items to the layout grid
        # top part
        MsgGp = QGroupBox()
        MsgGp.setFont(QFont('Helvetica Neue', 12))
        gridMsg = QGridLayout()
        vbox2_top.addWidget(MsgGp)
        MsgGp.setLayout(gridMsg)

        # add GroupBox to layout and load buttons in GroupBox
        gridMsg.addWidget(self.msg, 1, 0)

        # in-between for sample plot
        plotGp = QGroupBox()
        plotGp.setFont(QFont('Helvetica Neue', 12))
        plotGp.setMinimumHeight(400)
        gridFig = QGridLayout()
        vbox2_middle.addWidget(plotGp)
        plotGp.setLayout(gridFig)

        # add GroupBox to layout and load buttons in GroupBox
        gridFig.addWidget(self.slider1pH, 1, 1)
        gridFig.addWidget(self.sldpH1_label, 1, 0)
        gridFig.addWidget(self.canvaspHs, 2, 1)
        gridFig.addWidget(self.navipHs, 3, 1)
        gridFig.addWidget(pHtrim_label, 4, 0)
        gridFig.addWidget(self.pHtrim_edit, 4, 1)
        gridFig.addWidget(swiSample_label, 5, 0)
        gridFig.addWidget(self.swiSample_edit, 5, 1)

        # bottom group for navigation panel
        naviGp = QGroupBox("Navigation panel")
        naviGp.setFont(QFont('Helvetica Neue', 12))
        naviGp.setFixedHeight(75)
        gridNavi = QGridLayout()
        vbox2_bottom.addWidget(naviGp)
        naviGp.setLayout(gridNavi)

        # add GroupBox to layout and load buttons in GroupBox
        gridNavi.addWidget(self.close_button, 1, 0)
        gridNavi.addWidget(self.adjust_button, 1, 1)
        gridNavi.addWidget(self.reset_button, 1, 2)

        # add everything to the window layout
        self.setLayout(mlayout2)

    def onclick_updatepH(self, event):
        modifiers = QtWidgets.QApplication.keyboardModifiers()
        if modifiers == Qt.ControlModifier:
            # change selected range when control is pressed on keyboard
            # in case there are more than 2 points selected -> clear list and start over again
            if len(self.ls_cropy) >= 2:
                self.ls_cropy.clear()
            self.ls_cropy.append(event.ydata)

            # mark range in grey
            self._markHLine()

        if modifiers == Qt.ShiftModifier:
            # mark outlier when shift is pressed on keyboard
            self.ls_out.append(event.ydata)

    def slider1pH_update(self):
        # clear lists for another trial
        self.ls_out, self.ls_cropy = list(), list()

        # get actual scale
        self.scale = (float(self.pHtrim_edit.text().split('-')[0]), float(self.pHtrim_edit.text().split('-')[1].strip()))

        # allow only discrete values according to existing cores
        sample_select = min(results['pH adjusted'][self.Core].keys(), key=lambda x: abs(x - self.slider1pH.value()))

        # update slider position and label
        self.slider1pH.setValue(sample_select)
        self.sldpH1_label.setText('sample: {}'.format(sample_select))

        # update plot according to selected core
        fig = plot_adjustpH(core=self.Core, sample=sample_select, dfCore=results['pH adjusted'][self.Core],
                            scale=self.scale, fig=self.figpHs, ax=self.axpHs)
        self.figpHs.canvas.draw()

    def _markHLine(self):
        # in case too many boundaries are selected, use the minimal/maximal values
        if len(self.ls_cropy) > 2:
            ls_crop = [min(self.ls_cropy), max(self.ls_cropy)]
        else:
            ls_crop = sorted(self.ls_cropy)

        # current core, current sample
        c, s = self.Core, int(self.sldpH1_label.text().split(' ')[-1])

        # span grey area to mark outside range
        if len(ls_crop) == 1:
            sub = (results['pH adjusted'][self.Core][s].index[0] - ls_crop[-1],
                   results['pH adjusted'][self.Core][s].index[-1] - ls_crop[-1])
            if np.abs(sub[0]) < np.abs(sub[1]):
                # left outer side
                self.axpHs.axhspan(results['pH adjusted'][self.Core][s].index[0], ls_crop[-1], color='gray', alpha=0.3)
            else:
                # right outer side
                self.axpHs.axhspan(ls_crop[-1], results['pH adjusted'][self.Core][s].index[-1], color='gray', alpha=0.3)
        else:
            if ls_crop[-1] < ls_crop[0]:
                # left outer side
                self.axpHs.axhspan(results['pH adjusted'][self.Core][s].index[0], ls_crop[-1], color='gray', alpha=0.3)
            else:
                # left outer side
                self.axpHs.axhspan(ls_crop[-1], results['pH adjusted'][self.Core][s].index[-1], color='gray', alpha=0.3)

        # draw vertical line to mark boundaries
        [self.axpHs.axhline(x, color='k', ls='--', lw=0.5) for x in ls_crop]
        self.figpHs.canvas.draw()

    def updatepHscale(self):
        # get pH range form LineEdit
        if '-' in self.pHtrim_edit.text():
            scale = (float(self.pHtrim_edit.text().split('-')[0]), float(self.pHtrim_edit.text().split('-')[1].strip()))
        elif ',' in self.pHtrim_edit.text():
            scale = (float(self.pHtrim_edit.text().split(',')[0]), float(self.pHtrim_edit.text().split(',')[1].strip()))
        else:
            scale = (float(self.pHtrim_edit.text().split(' ')[0]), float(self.pHtrim_edit.text().split(' ')[1].strip()))

        # if pH range was updated by the user -> update self.scale (prevent further down)
        if scale != self.scale:
            self.scale = scale

        # update global variable
        global scalepH
        scalepH[self.Core] = (round(self.scale[0], 2), round(self.scale[1], 2))

    def cropDF_pH(self, s):
        if self.ls_cropy:
            # in case there was only 1 point selected -> extend the list to the other end
            if len(self.ls_cropy) == 1:
                sub = (results['pH adjusted'][self.Core][s].index[0] - self.ls_cropy[0],
                       results['pH adjusted'][self.Core][s].index[-1] - self.ls_cropy[0])
                if np.abs(sub[0]) < np.abs(sub[1]):
                    self.ls_cropy = [self.ls_cropy[0], results['pH adjusted'][self.Core][s].index[-1]]
                else:
                    self.ls_cropy = [results['pH adjusted'][self.Core][s].index[0], self.ls_cropy[0]]

            # actually crop the depth profile to the area selected.
            # In case more than 2 points have been selected, choose the outer ones -> trim y-axis
            df = results['pH adjusted'][self.Core][s].loc[min(self.ls_cropy): max(self.ls_cropy)]
        else:
            df = results['pH adjusted'][self.Core][s]
        return df

    def popData_pH(self, df_crop, s):
        if None in self.ls_out:
            self.ls_out.remove(None)

        ls_pop = [min(df_crop.index.to_numpy(), key=lambda x: abs(x - self.ls_out[p])) for p in range(len(self.ls_out))]
        # drop in case value is still there
        [df_crop.drop(p, inplace=True) for p in ls_pop if p in df_crop.index]
        return df_crop

    def adjustpH(self):
        # check if the pH range (scale) changed
        self.updatepHscale()

        # current core and sample
        c, s = self.Core, int(self.sldpH1_label.text().split(' ')[-1])

        # crop dataframe to selected range
        df_crop = self.cropDF_pH(s=s)

        # pop outliers from depth profile
        df_pop = self.popData_pH(df_crop=df_crop, s=s) if self.ls_out else df_crop

        # check individual swi for sample
        if '--' in self.swiSample_edit.text():
            pass
        else:
            # correction of manually selected baseline and store adjusted pH
            ynew = df_pop.index - float(self.swiSample_edit.text())
            df_pop = pd.DataFrame(df_pop.to_numpy(), index=ynew, columns=df_pop.columns)
            self.swiSample_edit.setText('--')

        # update pH adjusted dictionary without altering pH raw data
        dadj = dict()
        for si in results['pH adjusted'][self.Core].keys():
            if si == s:
                dadj[si] = pd.DataFrame(df_pop, index=df_pop.index, columns=df_pop.columns)
            else:
                dadj[si] = pd.DataFrame(results['pH adjusted'][self.Core][si].to_numpy(),
                                        index=results['pH adjusted'][self.Core][si].index,
                                        columns=results['pH adjusted'][self.Core][si].columns)
        results['pH adjusted'][self.Core] = dadj

        # re-draw pH profile plot
        fig = plot_pHUpdate(core=self.Core, nr=s, df_pHs=results['pH adjusted'][self.Core][s], scale=self.scale,
                            ddcore=results['pH adjusted'][self.Core], ax=self.axpHs, fig=self.figpHs)
        self.figpHs.canvas.draw()

        #  update range for pH plot and plot in main window
        self.pHtrim_edit.setText(str(round(self.scale[0], 2)) + ' - ' + str(round(self.scale[1], 2)))
        ls = '-.' if self.status_pH < 1 else '-'
        fig0 = plot_pHProfile(data_pH=results['pH adjusted'], core=self.Core, ls_core=results['pH adjusted'].keys(),
                              scale=self.scale, fig=self.figpH, ax=self.axpH, ls=ls, trimexact=True)
        self.figpH.canvas.draw()

    def resetPlot(self):
        print('start all over again and use the raw data')
        self.swiSample_edit.setText('--')

    def close_window(self):
        self.hide()


def plot_pHProfile(data_pH, core, ls_core, scale, ls='-.', fig=None, ax=None, show=True, trimexact=False):
    plt.ioff()
    # identify closest value in list
    core_select = dbs.closest_core(ls_core=ls_core, core=core)

    # initialize figure
    if ax is None:
        fig, ax = plt.subplots(figsize=(3, 4))
    else:
        ax.cla()
    ax.set_xlabel('pH value'), ax.set_ylabel('Depth / µm')
    ax.invert_yaxis()

    if core_select != 0:
        ax.title.set_text('pH depth profile for {} {}'.format(grp_label, core_select))
        ax.axhline(0, lw=.5, color='k')
        for en, nr in enumerate(data_pH[core_select].keys()):
            lw = 0.75 if ls == '-.' else 1.
            mark = '.' if ls == '-.' else None
            ax.plot(data_pH[core_select][nr]['pH'], data_pH[core_select][nr].index, lw=lw, ls=ls, marker=mark,
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
        plt.close(fig)
    else:
        fig.canvas.draw()
    return fig


def plot_adjustpH(core, sample, dfCore, scale, fig, ax):
    # initialize first plot with first core and sample
    fig = GUI_adjustDepth(core=core, nr=sample, dfCore=dfCore, scale=scale, fig=fig, ax=ax)
    fig.canvas.draw()
    return fig


def plot_pHUpdate(core, nr, df_pHs, ddcore, scale, fig, ax):
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


def GUI_adjustDepth(core, nr, dfCore, scale, fig=None, ax=None, show=True):
    plt.ioff()
    # initialize figure plot
    if ax is None:
        fig, ax = plt.subplots(figsize=(5, 3))
    else:
        ax.cla()

    if core != 0:
        ax.title.set_text('pH profile for {} {} - sample {}'.format(grp_label, core, nr))
        ax.set_ylabel('Depth / µm'), ax.set_xlabel('pH value')

    # plotting part
    ax.axhline(0, lw=.5, color='k')

    # position in sample list to get teh right color
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


# -----------------------------------------------
class h2sPage(QWizardPage):
    def __init__(self, parent=None):
        super(h2sPage, self).__init__(parent)
        # general layout of the H2S / total sulfide project
        self.setTitle("H2S / total sulfide ΣS2- depth profile")
        self.setSubTitle("The depth profile will first be plotted without any depth correction.  In case the pH depth"
                         " profile is available,  the total sulfide ΣS2- concentration is calculated.\n")
        self.initUI()

        # connect checkbox and load file button with a function
        self.salcon_button.clicked.connect(self.conductivity_converter)
        self.continueh2s_button.clicked.connect(self.continue_H2S)
        self.adjusth2s_button.clicked.connect(self.adjust_H2S)
        self.saveh2s_button.clicked.connect(self.save_H2S)
        self.reseth2s_button.clicked.connect(self.reset_H2Spage)
        self.updateh2s_button.clicked.connect(self.swi_correctionH2S)
        # self.swih2s_box.stateChanged.connect(self.enablePlot_swiBoxH2S)

    def initUI(self):
        # plot window, side panel for user input, and continue button
        tempC_label, tempC_unit_label = QLabel(self), QLabel(self)
        tempC_label.setText('Temperature'), tempC_unit_label.setText('degC')
        self.tempC_edit = QLineEdit(self)
        self.tempC_edit.setValidator(QDoubleValidator()), self.tempC_edit.setAlignment(Qt.AlignRight)
        self.tempC_edit.setMaximumWidth(100), self.tempC_edit.setText(str(results['temperature degC']))

        sal_label, sal_unit_label = QLabel(self), QLabel(self)
        sal_label.setText('Salinity'), sal_unit_label.setText('PSU')
        self.sal_edit = QLineEdit(self)
        self.sal_edit.setValidator(QDoubleValidator()), self.sal_edit.setAlignment(Qt.AlignRight)
        self.sal_edit.setMaximumWidth(100)
        if 'salinity PSU' in results.keys():
            self.sal_edit.setText(str(results['salinity PSU']))
        else:
            self.sal_edit.setText('0.')

        # manual baseline correction
        swih2s_label, swih2s_unit_label = QLabel(self), QLabel(self)
        swih2s_label.setText('Actual correction: '), swih2s_unit_label.setText('µm')
        self.swih2s_edit = QLineEdit(self)
        self.swih2s_edit.setValidator(QDoubleValidator()), self.swih2s_edit.setAlignment(Qt.AlignRight)
        self.swih2s_edit.setMaximumWidth(100), self.swih2s_edit.setText('--'), self.swih2s_edit.setEnabled(False)

        # define concentration for sulfidic front
        sFh2s_label, sFh2s_unit_label = QLabel(self), QLabel(self)
        sFh2s_label.setText('Sulfidic Front: '), sFh2s_unit_label.setText('µmol/L')
        self.sFh2s_edit = QLineEdit(self)
        self.sFh2s_edit.setValidator(QDoubleValidator()), self.sFh2s_edit.setAlignment(Qt.AlignRight)
        self.sFh2s_edit.setMaximumWidth(100), self.sFh2s_edit.setText('0.5'), self.sFh2s_edit.setEnabled(False)

        # Action button
        self.salcon_button = QPushButton('Converter', self)
        self.salcon_button.setFixedWidth(100), self.salcon_button.setFont(QFont('Helvetica Neue', fs_font))
        self.saveh2s_button = QPushButton('Save', self)
        self.saveh2s_button.setFixedWidth(100), self.saveh2s_button.setFont(QFont('Helvetica Neue', fs_font))
        self.continueh2s_button = QPushButton('Plot', self)
        self.continueh2s_button.setFixedWidth(100), self.continueh2s_button.setFont(QFont('Helvetica Neue', fs_font))
        self.adjusth2s_button = QPushButton('Adjust profile', self)
        self.adjusth2s_button.setFixedWidth(100), self.adjusth2s_button.setEnabled(False)
        self.adjusth2s_button.setFont(QFont('Helvetica Neue', fs_font))
        self.updateh2s_button = QPushButton('Update SWI', self)
        self.updateh2s_button.setFixedWidth(100), self.updateh2s_button.setEnabled(False)
        self.updateh2s_button.setFont(QFont('Helvetica Neue', fs_font))
        self.reseth2s_button = QPushButton('Reset', self)
        self.reseth2s_button.setFixedWidth(100), self.reseth2s_button.setFont(QFont('Helvetica Neue', fs_font))

        # Slider for different cores and label on the right
        self.sliderh2s = QSlider(Qt.Horizontal)
        self.sliderh2s.setMinimumWidth(250), self.sliderh2s.setFixedHeight(20)
        self.sldh2s_label = QLabel()
        self.sldh2s_label.setFixedWidth(55)
        self.sldh2s_label.setText('group: --')

        # creating window layout
        w2 = QWidget(self)
        mlayout2 = QVBoxLayout(w2)
        vbox1_top, vbox1_middle, vbox1_bottom = QHBoxLayout(), QHBoxLayout(), QVBoxLayout()
        mlayout2.addLayout(vbox1_top), mlayout2.addLayout(vbox1_middle), mlayout2.addLayout(vbox1_bottom)

        para_settings = QGroupBox("Input for H2S analysis")
        grid_load = QGridLayout()
        para_settings.setFont(QFont('Helvetica Neue', 12))
        vbox1_top.addWidget(para_settings)
        para_settings.setFixedHeight(180)
        para_settings.setLayout(grid_load)

        # include widgets in the layout
        grid_load.addWidget(tempC_label, 0, 0)
        grid_load.addWidget(self.tempC_edit, 0, 1)
        grid_load.addWidget(tempC_unit_label, 0, 2)
        grid_load.addWidget(sal_label, 1, 0)
        grid_load.addWidget(self.sal_edit, 1, 1)
        grid_load.addWidget(sal_unit_label, 1, 2)
        grid_load.addWidget(self.salcon_button, 1, 3)
        grid_load.addWidget(swih2s_label, 2, 0)
        grid_load.addWidget(self.swih2s_edit, 2, 1)
        grid_load.addWidget(swih2s_unit_label, 2, 2)
        grid_load.addWidget(self.updateh2s_button, 2, 3)
        grid_load.addWidget(sFh2s_label, 3, 0)
        grid_load.addWidget(self.sFh2s_edit, 3, 1)
        grid_load.addWidget(sFh2s_unit_label, 3, 2)
        # grid_load.addWidget(self.swih2s_box, 2, 3)
        grid_load.addWidget(self.continueh2s_button, 4, 0)
        grid_load.addWidget(self.adjusth2s_button, 4, 1)
        grid_load.addWidget(self.reseth2s_button, 4, 2)
        grid_load.addWidget(self.saveh2s_button, 4, 3)

        # draw additional "line" to separate parameters from plots and to separate navigation from rest
        vline = QFrame()
        vline.setFrameShape(QFrame.HLine | QFrame.Raised)
        vline.setLineWidth(2)
        vbox1_middle.addWidget(vline)

        # plotting area
        self.figh2s, self.axh2s = plt.subplots(figsize=(3, 2))
        self.canvash2s = FigureCanvasQTAgg(self.figh2s)
        self.axh2s.set_xlabel('H2S / µmol/L'), self.axh2s.set_ylabel('Depth / µm')
        self.axh2s.invert_yaxis()
        self.figh2s.tight_layout(pad=0.5)
        sns.despine()

        H2S_group = QGroupBox("H2S depth profile")
        H2S_group.setMinimumHeight(300), H2S_group.setMinimumWidth(550)
        grid_H2S = QGridLayout()

        # add GroupBox to layout and load buttons in GroupBox
        vbox1_bottom.addWidget(H2S_group)
        H2S_group.setLayout(grid_H2S)
        grid_H2S.addWidget(self.sliderh2s, 1, 0)
        grid_H2S.addWidget(self.sldh2s_label, 1, 1)
        grid_H2S.addWidget(self.canvash2s, 2, 0)
        self.setLayout(mlayout2)

    def enablePlot_swiBoxH2S(self):
        if self.status_h2s == 1:
            self.continueh2s_button.setEnabled(True), self.swih2s_edit.setEnabled(True)
            self.self.sFh2s_edit.setEnabled(True)

    def load_H2Sdata(self):
        # raw measurement file pre-processed and saved per default as rawData file
        dsheets, dignore = _loadGlobData(file_str=self.field("Data"))
        for k in dignore.keys():
            if 'H2S' in dignore[k].keys():
                l = k

        # pre-check whether pH_all in sheet names
        sheet_select = dbs.sheetname_check(dsheets, para='H2S')
        checked = checkDatavsPara(sheet_select, par='H2S')

        if checked is True:
            #  prepare file depending on the type
            ddata = dsheets[sheet_select].set_index('Nr')

            # remove excluded profiles
            ddata_update = _excludeProfiles(analyt='H2S', dignore=dignore[l], ddata=ddata)

            global grp_label
            if grp_label is None:
                grp_label = ddata_update.columns[0]

            # list all available cores for pH sheet
            self.ls_core = list(dict.fromkeys(ddata_update[ddata_update.columns[0]].to_numpy()))

            # import all measurements for given parameter
            [self.dH2S_core, ls_nr,
             self.ls_colname] = dbs.load_measurements(dsheets=ddata_update, ls_core=self.ls_core, para=sheet_select)
            results['H2S adjusted'] = self.dH2S_core

            # separate storage of raw data
            results['H2S profile raw data'] = dict()
            for c in results['H2S adjusted'].keys():
                ddic = dict()
                for i in results['H2S adjusted'][c].keys():
                    df_i = pd.DataFrame(np.array(results['H2S adjusted'][c][i]), index=results['H2S adjusted'][c][i].index,
                                        columns=results['H2S adjusted'][c][i].columns)
                    ddic[i] = df_i
                results['H2S profile raw data'][c] = ddic
        else:
            self.reset_H2Spage()
        return checked

    def load_additionalInfo(self):
        # convert potential str-list into list of strings
        if '[' in self.field("Data"):
            ls_file = [i.strip()[1:-1] for i in self.field("Data")[1:-1].split(',')]
        else:
            ls_file = list(self.field("Data"))

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
                dfcorrel_sum = self.correlationInfo(en=en, key=key, dsheets_add=dsheets_add, dic_sheets=dic_sheets)

            else:
                dfcorrel_sum = dsheets_add['pH - H2S correlation']
            dsheets_add = dict({'meta data': dfmeta_sum, 'pH - H2S correlation': dfcorrel_sum})
        return dsheets_add

    def correlationInfo(self, dsheets_add, dic_sheets, en, key):
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
                            msgBox.setText("The excel sheets contain mismatching information for pH-H2S correlation.  Please "
                                           "check column {} in line {}".format(value, index))
                            msgBox.setFont(QFont('Helvetica Neue', 11))
                            msgBox.setWindowTitle("Warning")
                            msgBox.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)

                            returnValue = msgBox.exec()
                            if returnValue == QMessageBox.Ok:
                                pass

                    dfcorrel_sum = dsheets_add['pH - H2S correlation']
        return dfcorrel_sum

    def conductivity_converter(self):
        # open dialog window for conductivity -> salinity conversion
        global wConv
        wConv = SalConvWindowO2(self.tempC_edit, self.sal_edit)
        if wConv.isVisible():
            pass
        else:
            wConv.show()

    def continue_H2S(self):
        # get relevant information from previous projects if possible
        ssal = str(round(results['salinity PSU'], 4)) if 'salinity PSU' in results.keys() else '0.'
        self.sal_edit.setText(ssal)

        # set status for process control
        self.status_h2s = 0

        # update subtitle in case the pH profile was present as well
        if 'pH profile raw data' in results.keys():
            self.setSubTitle("You reached the sediment-water interface correction.  You can manually adjust the surface"
                             " and update the profile by clicking the update button.\n")

        # load data - mV and µM
        checked = self.load_H2Sdata()

        if checked is True:
            # adjust all the core plots to the same x-scale (uncalibrated)
            c = list(self.dH2S_core.keys())[0]
            nr = list(self.dH2S_core[c].keys())[0]
            # columns: Core, H2S_mV
            self.colH2S = self.dH2S_core[c][nr].columns[1]
            dfH2S_scale = pd.concat([pd.DataFrame([(self.dH2S_core[c][n][self.colH2S].min(),
                                                    self.dH2S_core[c][n][self.colH2S].max())
                                                   for n in self.dH2S_core[c].keys()]) for c in self.dH2S_core.keys()])
            self.scale0 = dfH2S_scale[0].min(), dfH2S_scale[1].max()
            self.scale = self.scale0

            # plot the pH profile for the first core
            figH2S0 = plot_H2SProfile(data_H2S=self.dH2S_core, core=min(self.ls_core), ls_core=self.ls_core,
                                      col=self.colH2S, scale=self.scale0, dobj_hidH2S=dobj_hidH2S, fig=self.figh2s,
                                      ax=self.axh2s)

            # slider initialized to first core
            self.sliderh2s.setMinimum(int(min(self.ls_core))), self.sliderh2s.setMaximum(int(max(self.ls_core)))
            self.sliderh2s.setValue(int(min(self.ls_core)))
            self.sldh2s_label.setText('{}: {}'.format(self.ls_colname[0], int(min(self.ls_core))))

            # when slider value change (on click), return new value and update figure plot
            self.sliderh2s.valueChanged.connect(self.sliderh2s_update)

            # allow profile data adjustment and SWI correction of raw data
            self.adjusth2s_button.setEnabled(True)
            self.swih2s_edit.setEnabled(True), self.updateh2s_button.setEnabled(True), self.sFh2s_edit.setEnabled(True)
            self.continueh2s_button.disconnect()

            # decide to which direction the code shall continue
            if 'pH profile raw data' in results.keys():
                # get information about correlation pH to H2S + pre-check if the excel file contains a correlation sheet
                dsheets_add = self.load_additionalInfo()
                results['pH - H2S correlation'] = dsheets_add['pH - H2S correlation']

                # calculation of total sulfide possible
                self.continueh2s_button.clicked.connect(self.continue_H2SIIa)
            else:
                # skip total sulfide but allow swi correction
                self.continueh2s_button.clicked.connect(self.continue_H2SIIb)

    def getOriginal_pH(self, corepH, sample):
        if 'pH swi depth' in results.keys():
            corepH1 = _findCoreLabel(option1=corepH, option2=int(corepH.split(' ')[1]), ls=results['pH swi depth'].keys())

            if corepH1:
                if isinstance(results['pH swi depth'][corepH1], float):
                    corr = results['pH swi depth'][corepH1]
                else:
                    corr = results['pH swi depth'][corepH1]['Depth (µm)']
            else:
                corr = 0.
                corepH1 = _findCoreLabel(option1=corepH, option2=int(corepH.split(' ')[1]), ls=results['pH adjusted'])
            xold = results['pH adjusted'][corepH1][sample].index
            pH_coreS = pd.DataFrame(results['pH adjusted'][corepH1][sample]['pH'])
            pH_coreS.index = xold
            # elif int(corepH.split(' ')[1]) in results['pH swi depth'].keys():
            #     if isinstance(results['pH swi depth'][int(corepH.split(' ')[1])], float):
            #         corr = results['pH swi depth'][int(corepH.split(' ')[1])]
            #     else:
            #         corr = results['pH swi depth'][int(corepH.split(' ')[1])]['Depth (µm)']
            # else:
            #     corr = 0.
            # if corepH:
            #     in results['pH adjusted'].keys():
            #     labCore = corepH
            # elif int(corepH.split(' ')[1]) in results['pH adjusted'].keys():
            #     labCore = int(corepH.split(' ')[1])
        else:
            corepH = _findCoreLabel(option1=corepH, option2=int(corepH.split(' ')[1]), ls=results['pH adjusted'])
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

    def _calcTotalSulfide(self, tempK, sal_pmill, coreh2s, sampleS, pH_coreS):
        coreh2s = int(coreh2s.split(' ')[1])

        # pK1 equation
        pK1 = -98.08 + (5765.4/tempK) + 15.04555*np.log(tempK) + -0.157*(sal_pmill**0.5) + 0.0135*sal_pmill
        K1 = 10**(-pK1)

        # get appropriate column of H2S
        for c in self.dH2S_core[coreh2s][sampleS].columns:
            if 'M' in c or 'mol' in c:
                col = c
        d_H2S = self.dH2S_core[coreh2s][sampleS][col] if col else self.dH2S_core[coreh2s][sampleS]

        # interpolate profiles to align data to the same index
        self.H2S_pH_interpolation(pd.DataFrame(pH_coreS), pd.DataFrame(d_H2S))

        # generate total sulfide DF
        self.df_interpol['total sulfide_µmol/L'] = self.df_interpol['H2S'] * (1 + (K1 / 10**(-self.df_interpol['pH'])))

        # zero correction -> everything that is negative is set to 0
        df_ = self.df_interpol['total sulfide_µmol/L'].copy()
        df_[df_ < 0] = 0
        self.df_interpol['total sulfide zero corr_µmol/L'] = df_
        return self.df_interpol

    def H2S_pH_interpolation(self, pH_coreS, d_H2S):
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
        self.df_interpol = df_combo.interpolate(method='linear').dropna()

    def precheck_totalSulfide(self, ddata_all):
        try:
            if 'correlation' in ddata_all.keys():
                df_correl = ddata_all['correlation']
            elif 'Correlation' in ddata_all.keys():
                df_correl = ddata_all['Correlation']
            else:
                df_correl = None
                msgBox = QMessageBox()
                msgBox.setIcon(QMessageBox.Warning)
                msgBox.setText("Information missing how to correlate pH and H2S sensor profiles.  In case the total "
                               "sulfide ΣS2- shall be calculated, please add respective information in the excel sheet "
                               "labeled correlation.")
                msgBox.setFont(QFont('Helvetica Neue', 11))
                msgBox.setWindowTitle("Warning")
                msgBox.setStandardButtons(QMessageBox.Ok)

                returnValue = msgBox.exec()
                if returnValue == QMessageBox.Ok:
                    pass
        except:
            df_correl = None
            msgBox = QMessageBox()
            msgBox.setIcon(QMessageBox.Warning)
            msgBox.setText("Information missing how to correlate pH and H2S sensor profiles. Please add respective "
                           "information in excel sheet labeled correlation.")
            msgBox.setFont(QFont('Helvetica Neue', 11))
            msgBox.setWindowTitle("Warning")
            msgBox.setStandardButtons(QMessageBox.Ok)

            returnValue = msgBox.exec()
            if returnValue == QMessageBox.Ok:
                pass

        return df_correl

    def calc_total_sulfide(self):
        # convert parameter
        tempK, sal_pmill = float(self.tempC_edit.text())+convC2K, float(self.sal_edit.text())
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
                pH_coreS = self.getOriginal_pH(corepH=df_corr.loc[n]['pH code'], sample=df_corr.loc[n]['pH Nr'])

                # calculate total sulfide for specific core and sample according to associated pH profile
                df = self._calcTotalSulfide(coreh2s=coreh2s, sampleS=s, tempK=tempK, sal_pmill=sal_pmill,
                                            pH_coreS=pH_coreS)
                dsulfideS[s] = df
                n += 1
            dsulfide[coreh2s] = dsulfideS

        return dsulfide

    def continue_H2SIIa(self):
        # update subtitle for swi correction
        self.setSubTitle("The total sulfide ΣS2- is calculated based on H2S as well as the temperature and salinity.  "
                         "Please make sure both parameters are correct..\n")

        # update status for process control
        self.status_h2s = 1
        # identify closest value in list
        core_select = dbs.closest_core(ls_core=self.ls_core, core=self.sliderh2s.value())

        # convert H2S into total sulfide in case pH was measured
        dsulfide = self.calc_total_sulfide()
        results['H2S adjusted'] = dsulfide

        # update pH profile plot for the first core
        para = 'total sulfide zero corr_µmol/L'
        dscale = dict()
        for c in dsulfide.keys():
            l = np.array([(dsulfide[c][nr][para].min(), dsulfide[c][nr][para].max()) for nr in dsulfide[c].keys()])

            # outlier test
            l = l[(l > np.quantile(l, 0.1)) & (l < np.quantile(l, 0.75))].tolist()

            # summarize for absolute min/max analysis
            dscale[c] = pd.DataFrame((np.min(l), np.median(l)))
        self.scaleS0 = (pd.concat(dscale, axis=1).T[0].min(), pd.concat(dscale, axis=1).T[1].max())
        self.col2 = para

        # update column name that shall be plotted
        te = True if core_select in scaleh2s.keys() else False
        figH2S0 = plot_H2SProfile(data_H2S=dsulfide, core=core_select, ls_core=self.ls_core, scale=self.scaleS0, ls='-',
                                  fig=self.figh2s, ax=self.axh2s, col=self.col2, dobj_hidH2S=dobj_hidH2S, trimexact=te)

        # slider initialized to first core
        self.sliderh2s.setMinimum(int(min(self.ls_core))), self.sliderh2s.setMaximum(int(max(self.ls_core)))
        self.sliderh2s.setValue(int(min(self.ls_core)))
        self.sldh2s_label.setText('{}: {}'.format(self.ls_colname[0], int(min(self.ls_core))))

        # when slider value change (on click), return new value and update figure plot
        self.sliderh2s.valueChanged.connect(self.sliderh2s_updateII)

        # ----------------------------------------------------------------------------------------------------------
        # update continue button as well as adjustment button in case the swi shall be updated
        self.adjusth2s_button.disconnect()
        self.adjusth2s_button.clicked.connect(self.adjust_H2SII)
        self.continueh2s_button.disconnect()
        self.continueh2s_button.clicked.connect(self.sulfidicFront)

    def continue_H2SIIb(self):
        # update status for process control
        self.status_h2s = 2

        # update layout
        # self.swih2s_box.setEnabled(True) if self.field("SWI pH as o2") == 'True' else self.swih2s_box.setEnabled(False)
        self.swih2s_edit.setEnabled(True), self.sFh2s_edit.setEnabeled(True)

        # update subtitle for swi correction
        self.setSubTitle("You can manually adjust the surface and update the profile by clicking the update button.\n\n")

        # identify closest value in list
        core_select = dbs.closest_core(ls_core=self.ls_core, core=self.sliderh2s.value())
        # identify data, that shall be plotted
        self.data = results['H2S profile total sulfide'] if 'H2S profile total sulfide' in results.keys() else self.dH2S_core

        # plot the pH profile for the first core
        if core_select in scaleh2s.keys():
            scale_plot = scaleh2s[core_select]
        else:
            scale_plot = self.scale0
        te = True if core_select in scaleh2s.keys() else False
        figH2S = plot_H2SProfile(data_H2S=self.data, core=core_select, ls_core=self.ls_core, scale=scale_plot, ls='-',
                                 fig=self.figh2s, ax=self.axh2s, col=self.colH2S, dobj_hidH2S=dobj_hidH2S, trimexact=te)
        self.figh2s.canvas.draw()

        # update continue button as well as adjustment button in case the swi shall be updated
        self.continueh2s_button.disconnect()
        self.continueh2s_button.clicked.connect(self.sulfidicFront)

    def swi_correctionH2S(self):
        # identify the data to adjust (SWI)
        data = results['H2S adjusted']

        # identify closest value in list
        core_select = min(self.ls_core, key=lambda x: abs(x - self.sliderh2s.value()))
        self.continueh2s_button.setEnabled(True)

        if '--' in self.swih2s_edit.text() or len(self.swih2s_edit.text()) == 0:
            pass
        else:
            # correction of manually selected baseline
            core_select = _findCoreLabel(option1=core_select, option2='core '+str(core_select), ls=list(data.keys()))
            for s in data[core_select].keys():
                # H2S correction
                ynew = data[core_select][s].index - float(self.swih2s_edit.text())
                data[core_select][s].index = ynew
                # pH correction
                ynew = data[core_select][s].index - float(self.swih2s_edit.text())
        # else:
        #     dpenH2S_av = dict()
        #     if 'O2 penetration depth' in results.keys():
        #         for c in results['O2 penetration depth'].keys():
        #             ls = list()
        #             [ls.append(i.split('-')[0]) for i in list(results['O2 penetration depth'][c].keys())
        #              if "penetration" in i]
        #             l = pd.DataFrame([results['O2 penetration depth'][c][s]
        #                               for s in results['O2 penetration depth'][c].keys()
        #                               if 'penetration' in s], columns=['Depth (µm)', 'O2 (%air)'], index=ls)
        #             dpenH2S_av[c] = l.mean()
        #
        #     # SWI correction as for O2 project
        #     for c in self.data.keys():
        #         for s in self.data[c].keys():
        #             xnew = [i - dpenH2S_av[c]['Depth (µm)'] for i in self.data[c][s].index]
        #             self.data[c][s].index = xnew
        #
        #     # SWI correction applied only once
        #     self.continueh2s_button.setEnabled(False)

        # add to results dictionary
        results['H2S adjusted'] = data

        # plot the pH profile for the first core
        ls = '-.' if self.status_h2s < 1 else '-'
        te = True if core_select in scaleh2s.keys() else False
        figH2S0 = plot_H2SProfile(data_H2S=data, core=core_select, ls_core=self.ls_core, col=self.colH2S, ax=self.axh2s,
                                  scale=self.scale0, dobj_hidH2S=dobj_hidH2S, fig=self.figh2s, trimexact=te, ls=ls)[0]
        # slider initialized to first core
        if isinstance(core_select, str):
            core_select = int(core_select.split(' ')[1])
        self.sliderh2s.setValue(int(core_select))
        self.sldh2s_label.setText('{}: {}'.format(self.ls_colname[0], int(core_select)))

    def sulfidicFront(self):
        # update status for process control
        self.status_h2s += 1

        # update subtitle for swi correction
        self.setSubTitle("The sulfidic front indicates the depth below the surface where total sulfide ΣS2- or H2S can"
                         " be detected for the first time in the sediment.\n")

        # identify data to use for the sulfidic front
        df_sulfFront = results['H2S adjusted']

        df_sFront = dict()
        for coreS in df_sulfFront.keys():
            ls_sample = list()
            for en, s in enumerate(df_sulfFront[coreS].keys()):
                df_, col = df_sulfFront[coreS][s], df_sulfFront[coreS][s].columns[-1]
                # base = df_[col].loc[df_[col].index[0]]
                sulFront = df_[col][df_[col] >= float(self.sFh2s_edit.text())] #  base*(1+float(self.sFh2s_edit.text())/100)
                if sulFront.empty:
                    ls_sample.append(np.nan)
                else:
                    ls_sample.append(sulFront.index[0])
            ind = ['sample '+str(i) for i in df_sulfFront[coreS].keys()]
            dfCore = pd.DataFrame(ls_sample, index=ind, columns=['sulfidic front'])

            # average when object not hidden
            if coreS in dobj_hidH2S.keys():
                smp_all = list(dfCore.index)
                [smp_all.remove(i) for i in dobj_hidH2S[coreS] if i in smp_all]
            else:
                smp_all = list(dfCore.index)
            dfCore.loc['mean', 'sulfidic front'] = np.nanmean(dfCore.loc[smp_all])
            dfCore.loc['std', 'sulfidic front'] = np.nanstd(dfCore.loc[smp_all])
            df_sFront[coreS] = dfCore
        results['H2S sulfidic front'], results['H2S hidden objects'] = df_sFront, dobj_hidH2S

        # identify closest value in list
        core_select = dbs.closest_core(ls_core=self.ls_core, core=self.sliderh2s.value())

        # indicate sulfidic front in plot
        figH2S0 = plot_sulfidicFront(df_Front=results['H2S sulfidic front'], core_select=core_select, fig=self.figh2s,
                                     ax=self.axh2s)

        # when slider value change (on click), return new value and update figure plot
        self.sliderh2s.valueChanged.connect(self.sliderh2s_updateIII)
        self.continueh2s_button.disconnect(), self.continueh2s_button.setEnabled(False)

    def sliderh2s_update(self):
        if self.ls_core:
            # allow only discrete values according to existing cores
            core_select = min(self.ls_core, key=lambda x: abs(x - self.sliderh2s.value()))

            # update slider position and label
            self.sliderh2s.setValue(int(core_select))
            self.sldh2s_label.setText('{}: {}'.format(self.ls_colname[0], core_select))

            # update plot according to selected core
            if core_select in scaleh2s.keys():
                scale_plot = self.scale0 if len(scaleh2s[core_select]) == 0 else scaleh2s[core_select]
            else:
                scale_plot = self.scale0
            ls = '-.' if self.status_h2s < 1 else '-'
            te = True if core_select in scaleh2s.keys() else False
            figH2S = plot_H2SProfile(data_H2S=results['H2S adjusted'], core=core_select, scale=scale_plot, ls=ls,
                                     fig=self.figh2s, ax=self.axh2s, dobj_hidH2S=dobj_hidH2S, ls_core=self.ls_core,
                                     col=self.colH2S, trimexact=te)[0]
            self.figh2s.canvas.draw()

    def sliderh2s_updateII(self):
        if self.ls_core:
            # allow only discrete values according to existing cores
            core_select = min(self.ls_core, key=lambda x: abs(x - self.sliderh2s.value()))

            # update slider position and label
            self.sliderh2s.setValue(int(core_select))
            self.sldh2s_label.setText('{}: {}'.format(self.ls_colname[0], core_select))

            # update plot according to selected core
            if core_select in scaleh2s.keys():
                scale_plot = self.scale0 if len(scaleh2s[core_select]) == 0 else scaleh2s[core_select]
            else:
                scale_plot = self.scale0
            te = True if core_select in scaleh2s.keys() else False
            figH2S = plot_H2SProfile(data_H2S=results['H2S adjusted'], core=core_select, ls_core=self.ls_core,
                                     col=self.col2, scale=scale_plot, fig=self.figh2s, ax=self.axh2s, ls='-',
                                     dobj_hidH2S=dobj_hidH2S, trimexact=te)[0]
            self.figh2s.canvas.draw()

    def sliderh2s_updateIII(self):
        if self.ls_core:
            # allow only discrete values according to existing cores
            core_select = min(self.ls_core, key=lambda x: abs(x - self.sliderh2s.value()))

            # update slider position and label
            self.sliderh2s.setValue(int(core_select))
            self.sldh2s_label.setText('{}: {}'.format(self.ls_colname[0], core_select))

            # update plot according to selected core
            figH2S = plot_sulfidicFront(df_Front=results['H2S sulfidic front'], core_select=core_select,
                                        fig=self.figh2s, ax=self.axh2s)
            self.figh2s.canvas.draw()

    def adjust_H2S(self):
        # open dialog window to adjust data presentation
        global wAdjustS
        res_pH = results['pH - H2S correlation'] if 'pH - H2S correlation' in results.keys() else None
        wAdjustS = AdjustpHWindowS(self.sliderh2s.value(), self.ls_core, self.dH2S_core, self.scale, self.colH2S,
                                   self.figh2s, self.axh2s, res_pH, self.swih2s_edit, 0)
        if wAdjustS.isVisible():
            pass
        else:
            wAdjustS.show()

    def adjust_H2SII(self):
        # open dialog window to adjust data presentation
        res_pH = results['pH - H2S correlation'] if 'pH - H2S correlation' in results.keys() else None
        global wAdjustS
        wAdjustS = AdjustpHWindowS(self.sliderh2s.value(), self.ls_core, results['H2S adjusted'], self.scaleS0,
                                   self.col2, self.figh2s, self.axh2s, res_pH, self.swih2s_edit, self.status_h2s)
        if wAdjustS.isVisible():
            pass
        else:
            wAdjustS.show()

    def save_H2S(self):
        global dout
        # preparation to save data
        dout = dbs.prepDataH2Soutput(dout=dout, results=results)

        # actual saving of data and figures
        self.save_H2Sdata()
        self.save_H2Sfigure()

        # Information that saving was successful
        msgBox = QMessageBox()
        msgBox.setIcon(QMessageBox.Information)
        msgBox.setText("Selected data are saved successfully.")
        msgBox.setFont(QFont('Helvetica Neue', 11))
        msgBox.setWindowTitle("Successful")
        msgBox.setStandardButtons(QMessageBox.Ok)

        returnValue = msgBox.exec()
        if returnValue == QMessageBox.Ok:
            pass

    def save_H2Sdata(self):
        # make a project folder for the specific analyte if it doesn't exist
        save_path = self.field("Storage path") + '/H2S_project/'
        if not os.path.exists(save_path):
            os.makedirs(save_path)

        ls_saveData = list()
        [ls_saveData.append(i) for i in self.field('saving parameters').split(',') if 'fig' not in i]
        if len(ls_saveData) > 0:
            # all keys that shall be removed
            ls_removeKey = list()
            [ls_removeKey.append(i) for i in ls_allData if i not in ls_saveData]
            if 'fit_mV' in ls_removeKey:
                ls_removeKey.append('derivative_mV')

            # delete a keys not in that list regardless of whether it is in the dictionary
            [dout.pop(i, None) for i in ls_removeKey]

            # save to excel sheets
            dbs.save_rawExcel(dout=dout, file=self.field("Data"), savePath=save_path)

    def save_H2Sfigure(self):
        ls_saveFig = list()
        [ls_saveFig.append(i) for i in self.field('saving parameters').split(',') if 'fig' in i]
        if len(ls_saveFig) > 0:
            save_path = self.field("Storage path") + '/Graphs/'
            # make folder "Graphs" if it doesn't exist
            if not os.path.exists(save_path):
                os.makedirs(save_path)

            # make a project folder for the specific analyte if it doesn't exist
            save_path = save_path + 'H2S_project/'
            if not os.path.exists(save_path):
                os.makedirs(save_path)

            # generate images of all all samples (don't plot them)
            [dfigRaw, dfigBase,
             dfigPen] = fig4saving_H2S(ls_core=self.ls_core, draw=results['H2S profile raw data'],
                                       dadj=results['H2S adjusted'], dsulFront=results['H2S sulfidic front'])

            # Depth profiles
            if 'fig raw' in ls_saveFig:
                self.save_figraw(save_path=save_path, dfigRaw=dfigRaw)
            if 'fig adjusted' in ls_saveFig:
                self.save_figdepth(save_path=save_path, dfigBase=dfigBase)
            # Penetration depth
            if 'fig penetration' in ls_saveFig:
                if dfigPen:
                    self.save_figPen(save_path=save_path, dfigPen=dfigPen)

    def save_figraw(self, save_path, dfigRaw):
        # find the actual running number
        save_folder = dbs._actualFolderName(savePath=save_path, cfolder='rawProfile', rlabel='run')
        if not os.path.exists(save_folder):
            os.makedirs(save_folder)

        for f in dfigRaw.keys():
            for t in ls_figtype:
                name = save_folder + 'rawDepthprofile_core-{}.'.format(f) + t
                dfigRaw[f].savefig(name, bbox_inches='tight', pad_inches=0.1, dpi=dpi)

    def save_figdepth(self, save_path, dfigBase):
        # find the actual running number
        save_folder = dbs._actualFolderName(savePath=save_path, cfolder='DepthProfile', rlabel='run')
        if not os.path.exists(save_folder):
            os.makedirs(save_folder)

        for f in dfigBase.keys():
            for t in ls_figtype:
                name = save_folder + 'Depthprofile_core-{}_adjusted.'.format(f) + t
                dfigBase[f].savefig(name, bbox_inches='tight', pad_inches=0.1, dpi=dpi)

    def save_figPen(self, save_path, dfigPen):
        # find the actual running number
        save_folder = dbs._actualFolderName(savePath=save_path, cfolder='SulfidicFront', rlabel='run')
        if not os.path.exists(save_folder):
            os.makedirs(save_folder)

        for f in dfigPen.keys():
            for t in ls_figtype:
                name = save_folder + 'SulfidicFront_core-{}.'.format(f) + t
                dfigPen[f].savefig(name, bbox_inches='tight', pad_inches=0.1, dpi=dpi)

    def reset_H2Spage(self):
        self.status_h2s = 0
        # reset global parameter
        global scaleh2s
        scaleh2s = dict()

        if 'H2S profile raw data' in results.keys():
            results.pop('H2S profile raw data')
        if 'pH - H2S correlation' in results.keys():
            results.pop('pH - H2S correlation')
        if 'H2S profile total sulfide' in results.keys():
            results.pop('H2S profile total sulfide')
        if 'H2S profile total sulfide swi corrected' in results.keys():
            results.pop('H2S profile total sulfide swi corrected')
        if 'H2S profile swi corrected' in results.keys():
            results.pop('H2S profile swi corrected')

        # update status for process control
        self.scale = None
        if self.dH2S_core:
            dfH2S_scale = pd.concat([pd.DataFrame([(self.dH2S_core[c][n][self.colH2S].min(),
                                                    self.dH2S_core[c][n][self.colH2S].max())
                                                   for n in self.dH2S_core[c].keys()]) for c in self.dH2S_core.keys()])
        else:
            dfH2S_scale = None
        self.scale0 = dfH2S_scale[0].min(), dfH2S_scale[1].max()
        self.tempC_edit.setText('13.2')
        self.sal_edit.setText('0.')

        # connect plot button to first part
        #self.continueh2s_button.disconnect()
        self.continueh2s_button.clicked.connect(self.continue_H2S)
        self.continueh2s_button.setEnabled(True)
        self.adjusth2s_button.setEnabled(False)
        self.swih2s_edit.setEnabled(False)
        self.updateh2s_button.setEnabled(False)
        self.sFh2s_edit.setText('0'), self.sFh2s_edit.setEnabled(False)

        # reset slider
        self.count = 0
        self.sliderh2s.setValue(int(min(self.ls_core)))
        self.sldh2s_label.setText('group: --')
        self.sliderh2s.disconnect()
        self.sliderh2s.valueChanged.connect(self.sliderh2s_update)

        # clear pH range (scale), SWI correction
        self.swih2s_edit.setText('--')
        # self.swih2s_box.setVisible(True), self.swih2s_box.setEnabled(False)
        # self.swih2s_box.setCheckState(False)

        # empty figure
        self.axh2s.cla()
        self.axh2s.set_xlabel('H2S / µmol/L'), self.axh2s.set_ylabel('Depth / µm')
        self.axh2s.invert_yaxis()
        self.figh2s.subplots_adjust(bottom=0.2, right=0.95, top=0.9, left=0.15)
        sns.despine()
        self.figh2s.canvas.draw()

        # reset the subtext
        self.setSubTitle("The depth profile will be plotted without any depth correction.  In case the pH depth profile"
                         " is available,  the total sulfide concentration is calculated.\n")

    def nextId(self) -> int:
        self.ls_page = list(self.field('parameter selected').split(','))
        if 'o2' in self.ls_page:
            self.ls_page.remove('o2')
        if 'ph' in self.ls_page:
            self.ls_page.remove('ph')
        self.ls_page.remove('h2s')
        if self.field('parameter selected'):
            if len(self.ls_page) != 0 and 'ep' in self.field('parameter selected'):
                return wizard_page_index["epPage"]
            else:
                return wizard_page_index["charPage"]


def fig4saving_H2S(ls_core, draw, dadj, dsulFront=None):
    dfigRaw, dfigBase, dfigPen = dict(), dict(), dict()
    # raw data
    for c in ls_core:
        dfigRaw[c] = plot_H2SProfile(data_H2S=draw, core=c, ls_core=ls_core, scale=None, col='H2S_uM', dobj_hidH2S=None,
                                     ls='-.', show=False, trimexact=False)[0]
    # adjusted data
    for c in ls_core:
        cC = _findCoreLabel(option1=c, option2='core ' + str(c), ls=dadj)
        s = list(dadj[cC].keys())
        dfigBase[c] = plot_H2SProfile(data_H2S=dadj, core=c, ls_core=ls_core, scale=None, col=dadj[cC][s[0]].columns[-1],
                                      ls='-', show=False, dobj_hidH2S=dobj_hidH2S, trimexact=False)[0]

    # sulfidic front in adjusted profile
    if dsulFront:
        for c in ls_core:
            cC = _findCoreLabel(option1=c, option2='core ' + str(c), ls=dadj)
            s = list(dadj[cC].keys())
            df, ax = plot_H2SProfile(data_H2S=dadj, core=c, ls_core=ls_core, scale=None, col=dadj[cC][s[0]].columns[-1],
                                     ls='-', show=False, dobj_hidH2S=dobj_hidH2S, trimexact=False)
            ax.axhline(dsulFront[cC].loc['mean'].values[0], color='crimson', lw=0.75, ls=':')
            ax.fill_betweenx([dsulFront[cC].loc['mean'].values[0] - dsulFront[cC].loc['std'].values[0],
                              dsulFront[cC].loc['mean'].values[0] + dsulFront[cC].loc['std'].values[0]],
                             ax.get_xlim()[0], ax.get_xlim()[1], lw=0, alpha=0.5, color='grey')
            dfigPen[c] = df

    return dfigRaw, dfigBase, dfigPen


class AdjustpHWindowS(QDialog):
    def __init__(self, sliderValue, ls_core, dic_H2S, scale, col, figH2S, axH2S, df_correl, swih2s_edit, status):
        super().__init__()
        self.initUI()

        # get the transmitted data
        self.figH2S, self.axH2S, self.dic_H2S, self.scaleS0, self.colH2S = figH2S, axH2S, dic_H2S, scale, col
        self.df_correl, self.ls_core, self.swih2s_edit, self.status_ph = df_correl, ls_core, swih2s_edit, status
        self.ls = '-.' if self.status_ph == 0 else '-'

        # return current core - and get the samples to plot (via slider selection)
        self.Core = min(self.ls_core, key=lambda x: abs(x - sliderValue))

        # plot all samples from current core
        self.Core = _findCoreLabel(option1=self.Core, option2='core ' +str(self.Core), ls=self.dic_H2S)
        h2s_nr = min(self.dic_H2S[self.Core].keys())
        if self.df_correl is None:
            pH_sample, pH_core = None, None
        else:
            pH_sample = self.df_correl[self.df_correl['H2S Nr'] == h2s_nr]['pH Nr'].to_numpy()[0]
            c = _findCoreLabel(option1=self.Core, option2='core ' + str(self.Core), ls=self.df_correl['H2S code'].to_numpy())
            pH_core = self.df_correl[self.df_correl['H2S code'] == c]['pH code'].to_numpy()[0]

        # get pH data and in case apply depth correction in case it was done for H2S / total sulfide
        self.pH_data = results['pH adjusted'] if 'pH adjusted' in results.keys() else None
        if self.pH_data:
            self.swi_correctionpHII()
        fig, self.ax1 = plot_adjustH2S(core=self.Core, sample=h2s_nr, col=self.colH2S, dfCore=self.dic_H2S[self.Core],
                                       scale=self.scaleS0, fig=self.figH2Ss, ax1=None, ax=self.axH2Ss, pH=self.pH_data,
                                       pH_sample=pH_sample, pH_core=pH_core)
        # set the range for pH
        if self.scaleS0:
            self.H2Strim_edit.setText(str(round(self.scaleS0[0], 2)) + ' - ' + str(round(self.scaleS0[1], 2)))

        # connect onclick event with function
        self.ls_out, self.ls_cropy = list(), list()
        self.figH2Ss.canvas.mpl_connect('button_press_event', self.onclick_updateH2S)

        # update slider range to number of samples and set to first sample
        self.slider1H2S.setMinimum(int(min(self.dic_H2S[self.Core].keys())))
        self.slider1H2S.setMaximum(int(max(self.dic_H2S[self.Core].keys())))
        self.slider1H2S.setValue(int(min(self.dic_H2S[self.Core].keys())))
        self.sldH2S1_label.setText('sample: ' + str(int(min(self.dic_H2S[self.Core].keys()))))

        # when slider value change (on click), return new value and update figure plot
        self.slider1H2S.valueChanged.connect(self.slider1H2S_update)
        self.figH2Ss.canvas.draw()

        # connect checkbox and load file button with a function
        self.scale = list()
        self.adjust_button.clicked.connect(self.adjustH2S)
        self.reset_button.clicked.connect(self.resetPlotH2S)
        self.close_button.clicked.connect(self.close_windowH2S)

    def initUI(self):
        self.setWindowTitle("Adjustment of data presentation")
        self.setGeometry(650, 75, 500, 600) # position (x,y), width, height

        # add description about how to use this window (slider, outlier detection, trim range)
        self.msg = QLabel("Use the slider to switch between samples belonging to the selected core. \nYou have the "
                          "following options to improve the fit: \n- Trim pH range (y-axis): press CONTROL/COMMAND + "
                          "select min/max \n- Remove outliers: press SHIFT + select individual points \n\nAt the end, "
                          "update the plot by pressing the button ADJUST.")
        self.msg.setWordWrap(True), self.msg.setFont(QFont('Helvetica Neue', int(fs_font*1.15)))

        # Slider for different cores and label on the right
        self.slider1H2S = QSlider(Qt.Horizontal)
        self.slider1H2S.setMinimumWidth(350), self.slider1H2S.setFixedHeight(20)
        self.sldH2S1_label = QLabel()
        self.sldH2S1_label.setFixedWidth(70), self.sldH2S1_label.setText('sample: --')

        # plot individual sample
        self.figH2Ss, self.axH2Ss = plt.subplots(figsize=(3, 2.5))
        self.figH2Ss.set_facecolor("none")
        self.canvasH2Ss = FigureCanvasQTAgg(self.figH2Ss)
        self.naviH2Ss = NavigationToolbar2QT(self.canvasH2Ss, self)
        self.axH2Ss.set_xlabel('H2S / µmol/L'), self.axH2Ss.set_ylabel('Depth / µm')
        self.axH2Ss.invert_yaxis()
        self.figH2Ss.subplots_adjust(bottom=0.2, right=0.95, top=0.85, left=0.15)
        sns.despine()

        # define pH range
        H2Strim_label = QLabel(self)
        H2Strim_label.setText('H2S range: '), H2Strim_label.setFont(QFont('Helvetica Neue', 12))
        self.H2Strim_edit = QLineEdit(self)
        self.H2Strim_edit.setValidator(QRegExpValidator()), self.H2Strim_edit.setAlignment(Qt.AlignRight)
        self.H2Strim_edit.setMaximumHeight(int(fs_font*1.5))

        # swi correction for individual sample
        swiSample_label = QLabel(self)
        swiSample_label.setText('SWI correction sample: '), swiSample_label.setFont(QFont('Helvetica Neue', 12))
        self.swiSample_edit = QLineEdit(self)
        self.swiSample_edit.setValidator(QDoubleValidator()), self.swiSample_edit.setAlignment(Qt.AlignRight)
        self.swiSample_edit.setMaximumHeight(int(fs_font * 1.5)), self.swiSample_edit.setText('--')

        # close the window again
        self.close_button = QPushButton('OK', self)
        self.close_button.setFixedWidth(100)
        self.adjust_button = QPushButton('Adjust', self)
        self.adjust_button.setFixedWidth(100)
        self.reset_button = QPushButton('Reset', self)
        self.reset_button.setFixedWidth(100)

        # create grid and groups
        mlayout2 = QVBoxLayout()
        vbox2_top, vbox2_bottom, vbox2_middle = QHBoxLayout(), QHBoxLayout(), QVBoxLayout()
        mlayout2.addLayout(vbox2_top), mlayout2.addLayout(vbox2_middle), mlayout2.addLayout(vbox2_bottom)

        # add items to the layout grid
        # top part
        MsgGp = QGroupBox()
        MsgGp.setFont(QFont('Helvetica Neue', 12))
        # MsgGp.setMinimumWidth(300)
        gridMsg = QGridLayout()
        vbox2_top.addWidget(MsgGp)
        MsgGp.setLayout(gridMsg)

        # add GroupBox to layout and load buttons in GroupBox
        gridMsg.addWidget(self.msg, 1, 0)

        # in-between for sample plot
        plotGp = QGroupBox()
        plotGp.setFont(QFont('Helvetica Neue', 12))
        plotGp.setMinimumHeight(450)
        gridFig = QGridLayout()
        vbox2_middle.addWidget(plotGp)
        plotGp.setLayout(gridFig)

        # add GroupBox to layout and load buttons in GroupBox
        gridFig.addWidget(self.slider1H2S, 1, 1)
        gridFig.addWidget(self.sldH2S1_label, 1, 0)
        gridFig.addWidget(self.canvasH2Ss, 2, 1)
        gridFig.addWidget(self.naviH2Ss, 3, 1)
        gridFig.addWidget(H2Strim_label, 4, 0)
        gridFig.addWidget(self.H2Strim_edit, 4, 1)
        gridFig.addWidget(swiSample_label, 5, 0)
        gridFig.addWidget(self.swiSample_edit, 5, 1)

        # bottom group for navigation panel
        naviGp = QGroupBox("Navigation panel")
        naviGp.setFont(QFont('Helvetica Neue', 12))
        naviGp.setFixedHeight(75)
        gridNavi = QGridLayout()
        vbox2_bottom.addWidget(naviGp)
        naviGp.setLayout(gridNavi)

        # add GroupBox to layout and load buttons in GroupBox
        gridNavi.addWidget(self.close_button, 1, 0)
        gridNavi.addWidget(self.adjust_button, 1, 1)
        gridNavi.addWidget(self.reset_button, 1, 2)

        # add everything to the window layout
        self.setLayout(mlayout2)

    def onclick_updateH2S(self, event):
        modifiers = QtWidgets.QApplication.keyboardModifiers()
        if modifiers == Qt.ControlModifier:
            # change selected range when control is pressed on keyboard
            # in case there are more than 2 points selected -> clear list and start over again
            if len(self.ls_cropy) >= 2:
                self.ls_cropy.clear()
            self.ls_cropy.append(event.ydata)

            # mark range in grey
            self._markHLine()

        if modifiers == Qt.ShiftModifier:
            # mark outlier when shift is pressed on keyboard
            self.ls_out.append(event.ydata)

    def slider1H2S_update(self):
        # clear lists for another trial
        self.ls_out, self.ls_cropy = list(), list()

        # get actual scale
        if self.H2Strim_edit.text():
            if len(self.H2Strim_edit.text().split('-')) > 1:
                # assume that negative numbers occur
                ls = re.findall(r"[-+]?(?:\d*\.\d+|\d+)", self.H2Strim_edit.text())
                self.scale = (float(ls[0]), float(ls[1]))
            else:
                self.scale = (float(self.H2Strim_edit.text().split('-')[0]),
                              float(self.H2Strim_edit.text().split('-')[1].strip()))

        # allow only discrete values according to existing cores
        sample_select = min(self.dic_H2S[self.Core].keys(), key=lambda x: abs(x - self.slider1H2S.value()))

        # update slider position and label
        self.slider1H2S.setValue(sample_select)
        self.sldH2S1_label.setText('sample: {}'.format(sample_select))

        # update plot according to selected core
        if self.df_correl is None:
            pH_sample, pH_core = None, None
        else:
            pH_sample = self.df_correl[self.df_correl['H2S Nr'] == sample_select]['pH Nr'].to_numpy()[0]
            c = _findCoreLabel(option1=self.Core, option2='core ' + str(self.Core), ls=self.df_correl['H2S code'].to_numpy())
            pH_core = self.df_correl[self.df_correl['H2S code'] == c]['pH code'].to_numpy()[0]

        pH_data = results['pH profile raw data'] if 'pH profile raw data' in results.keys() else None
        fig, self.ax1 = plot_adjustH2S(core=self.Core, sample=sample_select, dfCore=self.dic_H2S[self.Core],
                                       scale=self.scale, fig=self.figH2Ss, ax=self.axH2Ss, col=self.colH2S,
                                       pH=pH_data, pH_sample=pH_sample, pH_core=pH_core, ax1=self.ax1)
        self.figH2Ss.canvas.draw()

    def _markHLine(self):
        # in case too many boundaries are selected, use the minimal/maximal values
        if len(self.ls_cropy) > 2:
            ls_crop = [min(self.ls_cropy), max(self.ls_cropy)]
        else:
            ls_crop = sorted(self.ls_cropy)

        # current core, current sample
        c, s = self.Core, int(self.sldH2S1_label.text().split(' ')[-1])

        # span grey area to mark outside range
        if len(ls_crop) == 1:
            sub = (self.dic_H2S[self.Core][s].index[0] - ls_crop[-1], self.dic_H2S[self.Core][s].index[-1] - ls_crop[-1])
            if np.abs(sub[0]) < np.abs(sub[1]):
                # left outer side
                self.axH2Ss.axhspan(self.dic_H2S[self.Core][s].index[0], ls_crop[-1], color='gray', alpha=0.3)
            else:
                # right outer side
                self.axH2Ss.axhspan(ls_crop[-1], self.dic_H2S[self.Core][s].index[-1], color='gray', alpha=0.3)
        else:
            if ls_crop[-1] < ls_crop[0]:
                # left outer side
                self.axH2Ss.axhspan(self.dic_H2S[self.Core][s].index[0], ls_crop[-1], color='gray', alpha=0.3)
            else:
                # left outer side
                self.axH2Ss.axhspan(ls_crop[-1], self.dic_H2S[self.Core][s].index[-1], color='gray', alpha=0.3)

        # draw vertical line to mark boundaries
        [self.axH2Ss.axhline(x, color='k', ls='--', lw=0.5) for x in ls_crop]
        self.figH2Ss.canvas.draw()

    def updateH2Sscale(self):
        # get pH range form LineEdit
        if self.H2Strim_edit.text():
            if '-' in self.H2Strim_edit.text():
                if len(self.H2Strim_edit.text().split('-')) > 1:
                    # assume that negative numbers occur
                    ls = re.findall(r"[-+]?(?:\d*\.\d+|\d+)", self.H2Strim_edit.text())
                    scale = (float(ls[0]), float(ls[1]))
                else:
                    scale = (float(self.H2Strim_edit.text().split('-')[0]),
                             float(self.H2Strim_edit.text().split('-')[1].strip()))
            elif ',' in self.H2Strim_edit.text():
                scale = (float(self.H2Strim_edit.text().split(',')[0]),
                         float(self.H2Strim_edit.text().split(',')[1].strip()))
            else:
                scale = (float(self.H2Strim_edit.text().split(' ')[0]),
                         float(self.H2Strim_edit.text().split(' ')[1].strip()))
        else:
            scale = None

        # if pH range was updated by the user -> update self.scale (prevent further down)
        if scale:
            if scale != self.scale:
                self.scale = scale
            # update global variable
            global scaleh2s
            scaleh2s[self.Core] = (round(self.scale[0], 2), round(self.scale[1], 2))

    def cropDF_H2S(self, s):
        if self.ls_cropy:
            # in case there was only 1 point selected -> extend the list to the other end
            if len(self.ls_cropy) == 1:
                sub = (self.dic_H2S[self.Core][s].index[0] - self.ls_cropy[0],
                       self.dic_H2S[self.Core][s].index[-1] - self.ls_cropy[0])
                if np.abs(sub[0]) < np.abs(sub[1]):
                    self.ls_cropy = [self.ls_cropy[0], self.dic_H2S[self.Core][s].index[-1]]
                else:
                    self.ls_cropy = [self.dic_H2S[self.Core][s].index[0], self.ls_cropy[0]]

            # actually crop the depth profile to the area selected.
            # In case more than 2 points have been selected, choose the outer ones -> trim y-axis
            dcore_crop = self.dic_H2S[self.Core][s].loc[min(self.ls_cropy): max(self.ls_cropy)]
        else:
            dcore_crop = self.dic_H2S[self.Core][s]
        return dcore_crop

    def popData_H2S(self, dcore_crop):
        ls_pop = [min(dcore_crop.index.to_numpy(), key=lambda x: abs(x - self.ls_out[p]))
                  for p in range(len(self.ls_out))]
        # drop in case value is still there
        [dcore_crop.drop(p, inplace=True) for p in ls_pop if p in dcore_crop.index]
        return dcore_crop

    def adjustH2S(self):
        # check if the pH range (scale) changed
        self.updateH2Sscale()
        self.status_ph = 1

        # current core, current sample
        c, s = self.Core, int(self.sldH2S1_label.text().split(' ')[-1])

        # crop dataframe to selected range
        dcore_crop = self.cropDF_H2S(s=s)
        # pop outliers from depth profile
        if self.ls_out:
            dcore_crop = self.popData_H2S(dcore_crop=dcore_crop)

        # check individual swi for sample
        if '--' in self.swiSample_edit.text():
            pass
        else:
            swiS = float(self.swiSample_edit.text())
            xnew = dcore_crop.index - swiS
            dcore_crop.index = xnew
            self.swiSample_edit.setText('--')

        # update the general dictionary and store adjusted pH
        self.dic_H2S[self.Core][s] = dcore_crop

        # re-draw pH profile plot
        if self.df_correl is None:
            pH_sample, pH_core = None, None
        else:
            pH_sample = self.df_correl[self.df_correl['H2S Nr'] == s]['pH Nr'].to_numpy()[0]
            c = _findCoreLabel(option1=self.Core, option2='core ' + str(self.Core),
                               ls=self.df_correl['H2S code'].to_numpy())
            pH_core = self.df_correl[self.df_correl['H2S code'] == c]['pH code'].to_numpy()[0]

        self.pH_data = results['pH profile raw data'] if 'pH profile raw data' in results.keys() else None

        if 'H2S profile swi corrected pH' in results and self.pH_data:
            self.swi_correctionpHII()
        fig, self.ax1 = plot_H2SUpdate(core=self.Core, nr=s, df_H2Ss=dcore_crop, ddcore=self.dic_H2S[self.Core],
                                       scale=self.scale, ax=self.axH2Ss, fig=self.figH2Ss, col=self.colH2S,
                                       pH=self.pH_data, pHnr=pH_sample, pH_core=pH_core, ax1=self.ax1, trimexact=True)
        self.figH2Ss.canvas.draw()

        #  update range for pH plot and plot in main window
        if self.scale:
            self.H2Strim_edit.setText(str(round(self.scale[0], 2)) + ' - ' + str(round(self.scale[1], 2)))
        fig0 = plot_H2SProfile(data_H2S=self.dic_H2S, core=self.Core, ls_core=self.dic_H2S.keys(), scale=self.scale,
                               fig=self.figH2S, ax=self.axH2S, col=self.colH2S, dobj_hidH2S=dobj_hidH2S, ls=self.ls)[0]
        self.figH2S.canvas.draw()
        self.status_ph += 1

    def swi_correctionpHII(self):
        # identify closest value in list
        core_select = min(self.ls_core, key=lambda x: abs(x - self.slider1H2S.value()))
        # if self.swih2s_box.checkState() == 0:
        if '--' in self.swih2s_edit.text() or len(self.swih2s_edit.text()) == 0:
            pass
        else:
            # correction of manually selected baseline
            for s in self.pH_data[core_select].keys():
                ynew = self.pH_data[core_select][s].index - float(self.swih2s_edit.text())
        # else:
        #     dpenH2S_av = dict()
        #     for c in results['O2 penetration depth'].keys():
        #         ls = list()
        #         [ls.append(i.split('-')[0]) for i in list(results['O2 penetration depth'][c].keys())
        #          if "penetration" in i]
        #         l = pd.DataFrame([results['O2 penetration depth'][c][s]
        #                           for s in results['O2 penetration depth'][c].keys()
        #                           if 'penetration' in s], columns=['Depth (µm)', 'O2 (%air)'], index=ls)
        #         dpenH2S_av[c] = l.mean()
            # # SWI correction as for O2 project
            # for c in self.pH_data.keys():
            #     for s in self.pH_data[c].keys():
            #         xnew = [i - dpenH2S_av[c]['Depth (µm)'] for i in self.pH_data[c][s].index]
            #         self.pH_data[c][s].index = xnew

        # add to results dictionary
        if 'H2S profile total sulfide' in results.keys():
            results['H2S profile total sulfide swi corrected pH'] = self.pH_data
        else:
            results['H2S profile swi corrected pH'] = self.pH_data

    def resetPlotH2S(self):
        print('start all over again and use the raw data')
        self.swiSample_edit.setText('--')

    def close_windowH2S(self):
        self.hide()


def plot_H2SProfile(data_H2S, core, ls_core, col, dobj_hidH2S, ls='-.', scale=None, fig=None, ax=None, show=True,
                    trimexact=False):
    plt.ioff()
    lines = list()
    # identify closest value in list and the plotted analyte
    core_select = dbs.closest_core(ls_core=ls_core, core=core)
    if core_select in data_H2S.keys():
        s0 = list(data_H2S[core_select].keys())[0]
        labCore = core_select
    else:
        # 'core ' + str(core_select) in data_H2S.keys():
        s0 = list(data_H2S['core ' + str(core_select)].keys())[0]
        labCore = 'core ' + str(core_select)

    para = 'total sulfide zero corr_µmol/L' if 'total sulfide zero corr_µmol/L' in data_H2S[labCore][s0].columns else col
    unit = col.split('_')[1]

    # initialize figure
    if ax is None:
        fig, ax = plt.subplots(figsize=(3, 4))
    else:
        ax.cla()
    ax.set_xlabel('{} / {}'.format(para.split('zero')[0].split('_')[0], unit)), ax.set_ylabel('Depth / µm')
    ax.invert_yaxis()

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
            if dobj_hidH2S and labCore in dobj_hidH2S.keys():
                alpha_ = .0 if 'sample ' + str(nr) in dobj_hidH2S[labCore] else .6
            else:
                alpha_ = .6

            if para not in data_H2S[labCore][nr].columns:
                para = data_H2S[labCore][nr].filter(like='H2S').columns[0]
            df = data_H2S[labCore][nr][para].dropna()
            mark = '.' if ls == '-.' else None
            lw = .75 if ls == '-.' else 1.
            if en <= len(ls_col):
                line, = ax.plot(df, df.index, lw=lw, ls=ls, marker=mark, color=ls_col[en], alpha=alpha_,
                                label='sample ' + str(nr))
                lines.append(line)
        leg = ax.legend(frameon=True, fancybox=True, fontsize=fs_*0.8)

        # ------------------------------------------------------------------
        # combine legend
        lined = dict()
        for legline, origline in zip(leg.get_lines(), lines):
            legline.set_picker(5)  # 5 pts tolerance
            lined[legline] = origline

        # picker - hid curves in plot
        def onpick(event):
            ls_hid = dobj_hidH2S[labCore] if labCore in dobj_hidH2S.keys() else list()
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
            scale_min = -1 * scale[1]/10 if scale[0] == 0 else scale[0]
            scale_max = scale[1]
        else:
            scale_min = -1 * scale[1]/100 if scale[0] == 0 else scale[0]*0.95
            scale_max = scale[1]*1.05
        ax.set_xlim(scale_min, scale_max)
        fig.subplots_adjust(bottom=0.2, right=0.95, top=0.85, left=0.15)
    else:
        plt.tight_layout(pad=0.5)

    if show is False:
        plt.close(fig)
    else:
        fig.canvas.draw()
    return fig, ax


def plot_adjustH2S(core, sample, dfCore, col, scale, pH, pH_sample, pH_core, fig, ax, ax1):
    # initialize first plot with first core and sample
    fig, ax1 = GUI_adjustDepthH2S(core=core, nr=sample, dfCore=dfCore, col=col, scale=scale, fig=fig, ax=ax, ax1=ax1,
                                  pH=pH, pHnr=pH_sample, pH_core=pH_core)
    fig.canvas.draw()
    return fig, ax1


def plot_H2SUpdate(core, nr, df_H2Ss, ddcore, scale, col, pH, pH_core, pHnr, fig, ax, ax1=None, trimexact=False):
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
    ax.plot(df_H2Ss[col], df_H2Ss.index, lw=0.75, ls='-.', marker='.', ms=4, color=ls_col[pos], alpha=0.75)
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
        if isinstance(pH_core, str):
            pH_core = _findCoreLabel(option1=pH_core, option2=int(pH_core.split(' ')[1]), ls=results['pH profile raw data'].keys())
        ax1.plot(results['pH profile raw data'][pH_core][pHnr]['pH'], results['pH profile raw data'][pH_core][pHnr].index+corr,
                 lw=0.75, ls='--', color='#971EB3', alpha=0.75)

    # general layout
    if scale:
        scale_min = scale[0] if trimexact is True else -1 * scale[1]/10 if scale[0] == 0 else scale[0]*0.95
        scale_max = scale[1] if trimexact is True else scale[1]*1.015
        ax.set_xlim(scale_min, scale_max)
    ax.invert_yaxis()
    sns.despine()
    if pH:
        ax.spines['top'].set_visible(True)
    plt.tight_layout(pad=.5) #subplots_adjust(bottom=0.2, right=0.95, top=0.8, left=0.15)
    fig.canvas.draw()
    return fig, ax1


def GUI_adjustDepthH2S(core, nr, dfCore, scale, col, pH=None, pHnr=None, pH_core=None, fig=None, ax=None, ax1=None,
                       show=True):
    plt.ioff()
    unit = col.split('_')[1]

    # initialize figure plot
    if ax is None:
        fig, ax = plt.subplots(figsize=(5, 3))
    else:
        ax.cla()
    if pH:
        if ax1 is None:
            ax1 = ax.twiny()
        else:
            ax1.clear()
        ax1.set_xlabel('pH value')
    else:
        ax1 = None

    if core != 0:
        ax.title.set_text('H2S profile for {} {} - sample {}'.format(grp_label, core, nr))
        ax.set_ylabel('Depth / µm'), ax.set_xlabel('H2S / {}'.format(unit))

    # plotting part
    ax.axhline(0, lw=.5, color='k')

    # position in sample list to get teh right color
    pos = 0
    for en in enumerate(dfCore.keys()):
        if en[1] == nr:
            pos = en[0]
    if col in dfCore[nr].keys():
        pass
    else:
        col = 'H2S_µM'
    ax.plot(dfCore[nr][col], dfCore[nr].index, lw=0.75, ls='-.', marker='.', ms=4, color=ls_col[pos], alpha=0.75)

    if pH:
        # correlated pH sample Nr. - use the corrected profiles
        if isinstance(pH_core, str):
            pH_core = _findCoreLabel(option1=pH_core, option2=int(pH_core.split(' ')[1]), ls=results['pH adjusted'].keys())
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
        scale_min = -1 * scale[1]/10 if scale[0] == 0 else scale[0]*0.95
        ax.set_xlim(scale_min, scale[1] * 1.015)
    ax.invert_yaxis()
    sns.despine()
    ax.spines['top'].set_visible(True) if pH else ax.spines['top'].set_visible(False)
    if pH:
        fig.tight_layout(pad=0.5)#fig.subplots_adjust(bottom=0.2, right=0.95, top=0.8, left=0.15)
    else:
        fig.tight_layout(pad=0.5)#+fig.subplots_adjust(bottom=0.2, right=0.95, top=0.8, left=0.15)

    if show is False:
        plt.close(fig)
    else:
        fig.canvas.draw()
    return fig, ax1


def plot_sulfidicFront(df_Front, core_select, fig, ax):
    # add average + std to the plot
    if core_select != 0:
        if isinstance(core_select, str):
            core_select = _findCoreLabel(option1=core_select, option2=int(core_select.split(' ')[1]), ls=df_Front.keys())
        else:
            core_select = _findCoreLabel(option1=core_select, option2='core ' + str(core_select), ls=df_Front.keys())
        mean_ = df_Front[core_select].loc['mean'].to_numpy()[0]
        std_ = df_Front[core_select].loc['std'].to_numpy()[0]

        # indicate penetration depth mean + std according to visible curves
        ax.axhline(mean_, ls=':', color='crimson')
        ax.fill_betweenx([mean_ - std_, mean_ + std_], -50, 500, lw=0, alpha=0.5, color='grey')

        # include mean depth in title
        if core_select == 0:
            pass
        else:
            ax.title.set_text('Average sulfidic front for {} {}: {:.0f} ± {:.0f}µm'.format(grp_label, core_select,
                                                                                           mean_, std_))

        # layout
        fig.canvas.draw()


# -----------------------------------------------
class epPage(QWizardPage):
    def __init__(self, parent=None):
        super(epPage, self).__init__(parent)
        self.setTitle("EP depth profile")
        self.setSubTitle("Press PLOT to start and display the initial EP profiles.  If a drift correction shall be "
                         "included, make sure to check the checkbox.  At any case,  the profile can be adjusted by "
                         "trimming the depth range and removing outliers.")

        self.ls_core, self.status_EP = None, 0
        self.initUI()

        # connect checkbox and load file button with a function
        self.continueEP_button.clicked.connect(self.continue_EP)
        self.adjustEP_button.clicked.connect(self.adjust_EP)
        self.saveEP_button.clicked.connect(self.save_EP)
        self.resetEP_button.clicked.connect(self.reset_EPpage)
        self.updateEP_button.clicked.connect(self.swi_correctionEP)
        self.driftEP_box.stateChanged.connect(self.checkConnection_EP)

    def initUI(self):
        # manual baseline correction
        swi_label, swi_unit_label = QLabel(self), QLabel(self)
        swi_label.setText('Actual correction: '), swi_unit_label.setText('µm')
        self.swi_edit = QLineEdit(self)
        self.swi_edit.setValidator(QDoubleValidator()), self.swi_edit.setAlignment(Qt.AlignRight)
        self.swi_edit.setMaximumWidth(100), self.swi_edit.setText('--'), self.swi_edit.setEnabled(False)

        self.updateEP_button = QPushButton('Update SWI', self)
        self.updateEP_button.setFont(QFont('Helvetica Neue', fs_font)), self.updateEP_button.setFixedWidth(100)
        self.updateEP_button.setEnabled(False)

        # user option to consider drift correction
        drift_label, self.driftEP_box = QLabel(self), QCheckBox('Yes, please', self)
        drift_label.setText('Drift correction')
        self.driftEP_box.setFont(QFont('Helvetica Neue', int(fs_font*1.15)))
        self.driftEP_box.setChecked(False)

        # Action button
        self.saveEP_button = QPushButton('Save', self)
        self.saveEP_button.setFixedWidth(100), self.saveEP_button.setFont(QFont('Helvetica Neue', fs_font))
        self.continueEP_button = QPushButton('Plot', self)
        self.continueEP_button.setFixedWidth(100), self.continueEP_button.setFont(QFont('Helvetica Neue', fs_font))
        self.adjustEP_button = QPushButton('Adjustments', self)
        self.adjustEP_button.setFixedWidth(100), self.adjustEP_button.setEnabled(False)
        self.adjustEP_button.setFont(QFont('Helvetica Neue', fs_font))
        self.resetEP_button = QPushButton('Reset', self)
        self.resetEP_button.setFixedWidth(100), self.resetEP_button.setFont(QFont('Helvetica Neue', fs_font))

        # Slider for different cores and label on the right
        self.sliderEP = QSlider(Qt.Horizontal)
        self.sliderEP.setMinimumWidth(350), self.sliderEP.setFixedHeight(20)
        self.sldEP_label = QLabel()
        self.sldEP_label.setFixedWidth(55), self.sldEP_label.setText('group: --')

        # creating window layout
        w2 = QWidget(self)
        mlayout2 = QVBoxLayout(w2)
        vbox1_top, vbox1_middle, vbox1_bottom = QHBoxLayout(), QHBoxLayout(), QVBoxLayout()
        mlayout2.addLayout(vbox1_top), mlayout2.addLayout(vbox1_middle), mlayout2.addLayout(vbox1_bottom)

        swiarea = QGroupBox("Navigation panel")
        grid_swi = QGridLayout()
        swiarea.setFont(QFont('Helvetica Neue', fs_font)), swiarea.setMinimumHeight(115)
        vbox1_top.addWidget(swiarea)
        swiarea.setLayout(grid_swi)

        # include widgets in the layout
        grid_swi.addWidget(drift_label, 0, 0)
        grid_swi.addWidget(self.driftEP_box, 0, 1)
        grid_swi.addWidget(swi_label, 1, 0)
        grid_swi.addWidget(self.swi_edit, 1, 1)
        grid_swi.addWidget(swi_unit_label, 1, 2)
        grid_swi.addWidget(self.updateEP_button, 1, 3)
        grid_swi.addWidget(self.continueEP_button, 2, 0)
        grid_swi.addWidget(self.adjustEP_button, 2, 1)
        grid_swi.addWidget(self.resetEP_button, 2, 2)
        grid_swi.addWidget(self.saveEP_button, 2, 3)

        # draw additional "line" to separate parameters from plots and to separate navigation from rest
        vline = QFrame()
        vline.setFrameShape(QFrame.HLine | QFrame.Raised)
        vline.setLineWidth(2)
        vbox1_middle.addWidget(vline)

        # plotting area
        self.figEP, self.axEP = plt.subplots(figsize=(3, 2))
        self.canvasEP = FigureCanvasQTAgg(self.figEP)
        self.axEP.set_xlabel('EP / mV'), self.axEP.set_ylabel('Depth / µm')
        self.axEP.invert_yaxis()
        self.figEP.tight_layout(pad=.5)
        sns.despine()

        ep_group = QGroupBox("EP depth profile")
        ep_group.setMinimumHeight(300)
        grid_ep = QGridLayout()

        # add GroupBox to layout and load buttons in GroupBox
        vbox1_bottom.addWidget(ep_group)
        ep_group.setLayout(grid_ep)
        grid_ep.addWidget(self.sliderEP, 1, 0)
        grid_ep.addWidget(self.sldEP_label, 1, 1)
        grid_ep.addWidget(self.canvasEP, 2, 0)
        self.setLayout(mlayout2)

    def checkConnection_EP(self):
        if self.status_EP > 0:
            if self.driftEP_box.isChecked():
                self.continueEP_button.clicked.connect(self.continue_EPIIa)

        # collect initial information
        if self.driftEP_box.isChecked():
            print('plot time-drive of all profiles -> ask for which profiles belong together')

    def load_EPdata(self):
        # raw measurement file pre-processed and saved per default as rawData file
        dsheets, dignore = _loadGlobData(file_str=self.field("Data"))
        self.dsheets = dsheets

        for k in dignore.keys():
            if 'EP' in dignore[k].keys():
                l = k


        # pre-check whether EP_all in sheet names
        sheet_select = dbs.sheetname_check(dsheets, para='EP')
        checked = checkDatavsPara(sheet_select, par='EP')

        if checked is True:
            #  prepare file depending on the type
            ddata = dsheets[sheet_select].set_index('Nr')

            # remove excluded profiles
            ddata_update = _excludeProfiles(analyt='EP', dignore=dignore[l], ddata=ddata)

            global grp_label
            if grp_label is None:
                grp_label = ddata_update.columns[0]

            # list all available cores for pH sheet (in timely order, e.g., not ordered in ascending/ descending order)
            self.ls_core = list(dict.fromkeys(ddata_update[ddata_update.columns[0]]))

            # import all measurements for given parameter
            [self.dEP_core, ls_nr,
             self.ls_colname] = dbs.load_measurements(dsheets=ddata_update, ls_core=self.ls_core, para=sheet_select)

            # order depth index ascending
            self.dEP_core = dict(map(lambda c: (c, dict(map(lambda s: (s, self.dEP_core[c][s].sort_index(ascending=True)),
                                                            self.dEP_core[c].keys()))), self.dEP_core.keys()))
            results['EP adjusted'] =  self.dEP_core

            # separate storage of raw data
            results['EP raw data'] = dict()
            for c in results['EP adjusted'].keys():
                ddic = dict()
                for i in results['EP adjusted'][c].keys():
                    df_i = pd.DataFrame(np.array(results['EP adjusted'][c][i]), index=results['EP adjusted'][c][i].index,
                                        columns=results['EP adjusted'][c][i].columns)
                    ddic[i] = df_i
                results['EP raw data'][c] = ddic
        else:
            self.reset_EPpage()
        return checked

    def load_additionalInfo(self):
        # convert potential str-list into list of strings
        if '[' in self.field("Data"):
            ls_file = [i.strip()[1:-1] for i in self.field("Data")[1:-1].split(',')]
        else:
            ls_file = list(self.field("Data"))

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

    def continue_EP(self):
        # update instruction
        self.setSubTitle("The measurement data are plotted below.  If you want to adjust the profiles, press the "
                         "Adjustements button.  If the drift correction shall be applied in the next step, press the "
                         "respective checkbox. \n")

        # set status for process control and load data
        self.status_EP += 1
        checked = self.load_EPdata()

        if checked is True:
            # adjust all the core plots to the same x-scale
            dfEP_scale = pd.concat([pd.DataFrame([(self.dEP_core[c][n]['EP_mV'].min(), self.dEP_core[c][n]['EP_mV'].max())
                                                  for n in self.dEP_core[c].keys()]) for c in self.dEP_core.keys()])
            self.scale0 = dfEP_scale[0].min(), dfEP_scale[1].max()
            # use self.scale0 for the initial plot but make it possible to update self.scale
            self.scale = scaleEP[min(self.ls_core)] if min(self.ls_core) in scaleEP.keys() else self.scale0
            # plot the pH profile for the first core
            ls = '-.' if self.status_EP < 2 else '-'
            figEP0 = plot_initalProfile(data=self.dEP_core, para='EP', unit='mV', core=min(self.ls_core), ls=ls,
                                        ls_core=self.ls_core, col_name='EP_mV', dobj_hidEP=dobj_hidEP, ax=self.axEP,
                                        fig=self.figEP)
            # slider initialized to first core
            self.sliderEP.setMinimum(int(min(self.ls_core))), self.sliderEP.setMaximum(int(max(self.ls_core)))
            self.sliderEP.setValue(int(min(self.ls_core)))
            self.sldEP_label.setText('{}: {}'.format(self.ls_colname[0], int(min(self.ls_core))))

            # when slider value change (on click), return new value and update figure plot
            self.sliderEP.valueChanged.connect(self.sliderEP_update)

            # update continue button to "update" in case the swi shall be updated
            self.updateEP_button.setEnabled(True), self.adjustEP_button.setEnabled(True), self.swi_edit.setEnabled(True)
            self.continueEP_button.disconnect()
            if self.driftEP_box.isChecked():
                self.continueEP_button.clicked.connect(self.continue_EPIIa)
            else:
                self.continueEP_button.clicked.connect(self.continue_EPIIb)
                self.swi_edit.setEnabled(True)

    def sliderEP_update(self):
        if self.ls_core:
            # allow only discrete values according to existing cores
            core_select = min(self.ls_core, key=lambda x: abs(x - self.sliderEP.value()))

            # update slider position and label
            self.sliderEP.setValue(int(core_select))
            self.sldEP_label.setText('{}: {}'.format(self.ls_colname[0], core_select))

            # update plot according to selected data set and core
            ls = '-.' if self.status_EP < 2 else '-'
            figEP0 = plot_initalProfile(data=results['EP adjusted'], para='EP', unit='mV', col_name='EP_mV', ls=ls,
                                        core=core_select, ls_core=self.ls_core, dobj_hidEP=dobj_hidEP, fig=self.figEP,
                                        ax=self.axEP)
            self.figEP.canvas.draw()

    def swi_correctionEP(self):
        # identify the data to adjust (SWI)
        data = results['EP adjusted']

        # identify closest value in list
        core_select = min(self.ls_core, key=lambda x: abs(x - self.sliderEP.value()))
        self.continueEP_button.setEnabled(True)

        if '--' in self.swi_edit.text() or len(self.swi_edit.text()) == 0:
            pass
        else:
            # correction of manually selected baseline
            for s in data[core_select].keys():
                # EP correction
                ynew = data[core_select][s].index - float(self.swi_edit.text())
                data[core_select][s].index = ynew

        # add to results dictionary
        results['EP adjusted'] = data

        # plot the pH profile for the first core
        ls = '-.' if self.status_EP < 2 else '-'
        figEP0 = plot_initalProfile(data=data, para='EP', unit='mV', core=core_select, ls_core=self.ls_core, ls=ls,
                                    col_name='EP_mV', dobj_hidEP=dobj_hidEP, fig=self.figEP, ax=self.axEP)

        # slider initialized to first core
        self.sliderEP.setValue(int(core_select))
        self.sldEP_label.setText('{}: {}'.format(self.ls_colname[0], int(core_select)))

    def continue_EPIIa(self):
        # update instruction
        self.setSubTitle("Now,  the surface water interface can be corrected.  In case the O2 project was assessed "
                         "before,  you can either use the depth determined there,  or use your own depth. \n")

        # update status for process control
        self.status_EP += 1

        # identify closest value in list
        self.core_select = dbs.closest_core(ls_core=self.ls_core, core=self.sliderEP.value())

        # drift correction in case it was selected
        self.drift_correctionEP()

        # end of EP preparation
        self.continueEP_button.setEnabled(False)

    def drift_correctionEP(self):
        # import meta-data info from excel file
        dsheets_add = self.load_additionalInfo()

        if dsheets_add:
            # additional window for packaged drift correction
            self.driftCorr_EP(df_meta=dsheets_add['meta data'])
        else:
            msgBox = QMessageBox()
            msgBox.setIcon(QMessageBox.Information)
            msgBox.setText("No metadata sheet found.  Continue without EP drift correction.")
            msgBox.setFont(QFont('Helvetica Neue', 11))
            msgBox.setWindowTitle("Warning")
            msgBox.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)

            returnValue = msgBox.exec()
            if returnValue == QMessageBox.Ok:
                pass

    def continue_EPIIb(self):
        # update instruction
        self.setSubTitle("Now,  the surface water interface can be corrected.  In case the O2 project was assessed "
                         "before,  you can either use the depth determined there,  or use your own depth. \n")

        # update status for process control
        self.status_EP += 1

        # identify closest value in list
        core_select = dbs.closest_core(ls_core=self.ls_core, core=self.sliderEP.value())

        # get correct profile data (drift corrected, if available or raw data)
        self.data = self.dEP_corr if 'EP drift corrected' in results.keys() else self.dEP_core

        # check whether a (manual) swi correction is required. SWI correction only for current core
        self.swi_correctionEP()

        # plot the pH profile for the first core
        dfEP_scale = pd.concat([pd.DataFrame([(self.data[c][n]['EP_mV'].min(), self.data[c][n]['EP_mV'].max())
                                              for n in self.data[c].keys()]) for c in self.data.keys()])
        scale_plot = dfEP_scale[0].min(), dfEP_scale[1].max()
        self.scale = scale_plot
        figEP0 = plot_initalProfile(data=self.data, para='EP', unit='mV', col_name='EP_mV', core=core_select,
                                    ls_core=self.ls_core, ls='-', dobj_hidEP=dobj_hidEP, fig=self.figEP, ax=self.axEP)
        self.figEP.canvas.draw()

        # slider initialized to first core
        self.sliderEP.setValue(int(core_select)), self.sldEP_label.setText('{}: {}'.format(self.ls_colname[0],
                                                                                           int(core_select)))

        # when slider value change (on click), return new value and update figure plot
        self.sliderEP.valueChanged.connect(self.sliderEP_update)

        # end of EP preparation
        self.continueEP_button.setEnabled(False)

        # add which profiles are classified as non-EP profiles
        results['EP hidden objects'] = dobj_hidEP

    def adjust_EP(self):
        # open dialog window to adjust data presentation
        global wAdjustEP
        wAdjustEP = AdjustWindowEP(self.sliderEP.value(), self.ls_core, results['EP adjusted'], self.scale0, 'EP_mV',
                                   self.figEP, self.axEP, self.swi_edit, self.status_EP)
        if wAdjustEP.isVisible():
            pass
        else:
            wAdjustEP.show()

    def driftCorr_EP(self, df_meta):
        # open dialog window to adjust data presentation
        global wDCep
        wDCep = DriftWindow(self.ls_core, results['EP adjusted'], df_meta, self.core_select, self.axEP,
                            self.figEP)
        if wDCep.isVisible():
            pass
        else:
            wDCep.show()

    def save_EPdata(self):
        # make a project folder for the specific analyte if it doesn't exist
        save_path = self.field("Storage path") + '/EP_project/'
        if not os.path.exists(save_path):
            os.makedirs(save_path)

        ls_saveData = list()
        [ls_saveData.append(i) for i in self.field('saving parameters').split(',') if 'fig' not in i]
        if len(ls_saveData) > 0:
            # all keys that shall be removed
            ls_removeKey = list()
            [ls_removeKey.append(i) for i in ls_allData if i not in ls_saveData]
            if 'fit_mV' in ls_removeKey:
                ls_removeKey.append('derivative_mV')

            # delete all keys not in that list regardless of whether it is in the dictionary
            [dout.pop(i, None) for i in ls_removeKey]

            # save to excel sheets
            dbs.save_rawExcel(dout=dout, file=self.field("Data"), savePath=save_path)

    def save_EP(self):
        global dout
        # preparation to save data
        dout = dbs.prepDataEPoutput(dout=dout, results=results)

        # actual saving of data and figures
        self.save_EPdata()
        self.save_EPfigure()

        # Information that saving was successful
        msgBox = QMessageBox()
        msgBox.setIcon(QMessageBox.Information)
        msgBox.setText("Selected data are saved successfully.")
        msgBox.setFont(QFont('Helvetica Neue', 11))
        msgBox.setWindowTitle("Successful")
        msgBox.setStandardButtons(QMessageBox.Ok)

        returnValue = msgBox.exec()
        if returnValue == QMessageBox.Ok:
            pass

    def save_EPfigure(self):
        ls_saveFig = list()
        [ls_saveFig.append(i) for i in self.field('saving parameters').split(',') if 'fig' in i]
        if len(ls_saveFig) > 0:
            save_path = self.field("Storage path") + '/Graphs/'
            # make folder "Graphs" if it doesn't exist
            if not os.path.exists(save_path):
                os.makedirs(save_path)

            # make a project folder for the specific analyte if it doesn't exist
            save_path = save_path + 'EP_project/'
            if not os.path.exists(save_path):
                os.makedirs(save_path)

            # generate images of all all samples (don't plot them)
            [dfigRaw, dfigBase, dfigDC,
             dfigFit] = fig4saving_EP(ls_core=self.ls_core, draw=results['EP raw data'], dadj=results['EP adjusted'],
                                      ddrift=results['EP profile drift'], dfit=results['EP drift correction'])

            # individual profiles / drift corrections
            if 'fig raw' in ls_saveFig:
                self.save_figraw(save_path=save_path, dfigRaw=dfigRaw)
            if 'fig adjusted' in ls_saveFig:
                self.save_figdepth(save_path=save_path, dfigBase=dfigBase)
            if 'fig fit' in ls_saveFig:
                self.save_figFit(save_path=save_path, dfigFit=dfigFit)
                self.save_figDC(save_path=save_path, dfigDC=dfigDC)

    def save_figraw(self, save_path, dfigRaw):
        # find the actual running number
        save_folder = dbs._actualFolderName(savePath=save_path, cfolder='rawProfile', rlabel='run')
        if not os.path.exists(save_folder):
            os.makedirs(save_folder)

        for f in dfigRaw.keys():
            for t in ls_figtype:
                name = save_folder + 'rawDepthprofile_core-{}.'.format(f) + t
                dfigRaw[f].savefig(name, bbox_inches='tight', pad_inches=0.1, dpi=dpi)

    def save_figdepth(self, save_path, dfigBase):
        # find the actual running number
        save_folder = dbs._actualFolderName(savePath=save_path, cfolder='DepthProfile', rlabel='run')
        if not os.path.exists(save_folder):
            os.makedirs(save_folder)

        for f in dfigBase.keys():
            for t in ls_figtype:
                name = save_folder + 'Depthprofile_core-{}_adjusted.'.format(f) + t
                dfigBase[f].savefig(name, bbox_inches='tight', pad_inches=0.1, dpi=dpi)

    def save_figFit(self, save_path, dfigFit):
        # find the actual running number
        save_folder = dbs._actualFolderName(savePath=save_path, cfolder='DriftCorrect', rlabel='run')
        if not os.path.exists(save_folder):
            os.makedirs(save_folder)

        for f in dfigFit.keys():
            for t in ls_figtype:
                name = save_folder + 'DriftCorrect_group-{}.'.format(f) + t
                dfigFit[f].savefig(name, bbox_inches='tight', pad_inches=0.1, dpi=dpi)

    def save_figDC(self, save_path, dfigDC):
        # find the actual running number
        save_folder = dbs._actualFolderName(savePath=save_path, cfolder='CurveReg', rlabel='run')
        if not os.path.exists(save_folder):
            os.makedirs(save_folder)

        for f in dfigDC.keys():
            for t in ls_figtype:
                name = save_folder + 'CurveReg_group-{}.'.format(f) + t
                # dfigDC[f].set_size_inches(18.5, 10.5)
                dfigDC[f].savefig(name, bbox_inches='tight', pad_inches=0.1, dpi=100)

    def reset_EPpage(self):
        # reset global parameter
        global scaleEP, dobj_hidEP
        dobj_hidEP, scaleEP = dict(), dict()

        self.setSubTitle("[Restart]  Press PLOT to start and display the initial EP profiles.  If a drift correction "
                         "shall be included,  make sure to check the checkbox.  At any case,  the profile can be "
                         "adjusted by trimming the depth range and removing outliers.")

        # update status for process control
        self.status_EP = 0
        dobj_hidEP.clear()

        # connect plot button to first part
        self.continueEP_button.disconnect()
        self.continueEP_button.clicked.connect(self.continue_EP), self.continueEP_button.setEnabled(True)
        self.adjustEP_button.setEnabled(False)
        self.swi_edit.setEnabled(False)
        self.updateEP_button.setEnabled(False)

        # reset slider
        self.count = 0
        if self.ls_core:
            self.sliderEP.setValue(int(min(self.ls_core))), self.sldEP_label.setText('group: --')
        self.sliderEP.disconnect()
        self.sliderEP.valueChanged.connect(self.sliderEP_update)

        # clear SWI correction
        self.swi_edit.setText('--')

        # reset drift correction
        self.driftEP_box.setChecked(False)

        # empty figure
        self.axEP.cla()
        self.axEP.set_xlabel('EP / mV'), self.axEP.set_ylabel('Depth / µm')
        self.axEP.invert_yaxis()
        self.figEP.tight_layout(pad=1.5)
        sns.despine()
        self.figEP.canvas.draw()

    def nextId(self) -> int:
        return wizard_page_index["charPage"]


class AdjustWindowEP(QDialog):
    def __init__(self, sliderValue, ls_core, ddata, scale, col, figEP, axEP, swiEP_edit, status):
        super().__init__()
        self.initUI()

        # get the transmitted data
        self.figEP, self.axEP, self.ddata, self.scale0, self.colEP = figEP, axEP, ddata, scale, col
        self.ls_core, self.status_EP = ls_core, status
        self.swiEP_edit = swiEP_edit
        self.ls = '-.' if self.status_EP <= 1.5 else '-'

        # return current core - and get the samples to plot (via slider selection)
        self.Core = min(self.ls_core, key=lambda x: abs(x - sliderValue))

        # plot all samples from current core
        ep_nr = min(self.ddata[self.Core].keys())

        # get pH data and in case apply depth correction in case it was done for H2S / total sulfide
        fig = plot_adjustEP(core=self.Core, sample=ep_nr, col=self.colEP, dfCore=self.ddata[self.Core],
                            scale=self.scale0, fig=self.figEPs, ax=self.axEPs)
        self.EPtrim_edit.setText(str(round(self.scale0[0], 2)) + ' - ' + str(round(self.scale0[1], 2)))

        # connect onclick event with function
        self.ls_out, self.ls_cropy = list(), list()
        self.figEPs.canvas.mpl_connect('button_press_event', self.onclick_updateEP)

        # update slider range to number of samples and set to first sample
        self.slider1EP.setMinimum(int(min(self.ddata[self.Core].keys())))
        self.slider1EP.setMaximum(int(max(self.ddata[self.Core].keys())))
        self.slider1EP.setValue(int(min(self.ddata[self.Core].keys())))
        self.sldEP1_label.setText('sample: ' + str(int(min(self.ddata[self.Core].keys()))))

        # when slider value change (on click), return new value and update figure plot
        self.slider1EP.valueChanged.connect(self.slider1EP_update)
        self.figEPs.canvas.draw()

        # connect checkbox and load file button with a function
        self.scale = list()
        self.adjust_button.clicked.connect(self.adjustEP)
        self.reset_button.clicked.connect(self.resetPlotEP)
        self.close_button.clicked.connect(self.close_windowEP)

    def initUI(self):
        self.setWindowTitle("Adjustment of data presentation")
        self.setGeometry(650, 50, 500, 300)

        # add description about how to use this window (slider, outlier detection, trim range)
        self.msg = QLabel("Use the slider to switch between samples belonging to the selected core. \nYou have the "
                          "following options to improve the fit: \n- Trim pH range (y-axis): press CONTROL/COMMAND + "
                          "select min/max \n- Remove outliers: press SHIFT + select individual points \n\nAt the end, "
                          "update the plot by pressing the button ADJUST.")
        self.msg.setWordWrap(True), self.msg.setFont(QFont('Helvetica Neue', int(fs_font*1.15)))

        # Slider for different cores and label on the right
        self.slider1EP = QSlider(Qt.Horizontal)
        self.slider1EP.setMinimumWidth(350), self.slider1EP.setFixedHeight(20)
        self.sldEP1_label = QLabel()
        self.sldEP1_label.setFixedWidth(70), self.sldEP1_label.setText('sample: --')

        # plot individual sample
        self.figEPs, self.axEPs = plt.subplots(figsize=(3, 2))
        self.figEPs.set_facecolor("none")
        self.canvasEPs = FigureCanvasQTAgg(self.figEPs)
        self.naviEPs = NavigationToolbar2QT(self.canvasEPs, self)
        self.axEPs.set_xlabel('EP / mV'), self.axEPs.set_ylabel('Depth / µm')
        self.axEPs.invert_yaxis()
        self.figEPs.subplots_adjust(bottom=0.2, right=0.95, top=0.85, left=0.25)
        sns.despine()

        # define pH range
        EPtrim_label = QLabel(self)
        EPtrim_label.setText('EP range: '), EPtrim_label.setFont(QFont('Helvetica Neue', 12))
        self.EPtrim_edit = QLineEdit(self)
        self.EPtrim_edit.setValidator(QRegExpValidator()), self.EPtrim_edit.setAlignment(Qt.AlignRight)
        self.EPtrim_edit.setMaximumHeight(int(fs_font*1.5))

        # swi correction for individual sample
        swiSample_label = QLabel(self)
        swiSample_label.setText('SWI correction sample: '), swiSample_label.setFont(QFont('Helvetica Neue', 12))
        self.swiSample_edit = QLineEdit(self)
        self.swiSample_edit.setValidator(QDoubleValidator()), self.swiSample_edit.setAlignment(Qt.AlignRight)
        self.swiSample_edit.setMaximumHeight(int(fs_font * 1.5)), self.swiSample_edit.setText('--')

        # close the window again
        self.close_button = QPushButton('OK', self)
        self.close_button.setFixedWidth(100), self.close_button.setFont(QFont('Helvetica Neue', fs_font))
        self.adjust_button = QPushButton('Adjust', self)
        self.adjust_button.setFixedWidth(100), self.adjust_button.setFont(QFont('Helvetica Neue', fs_font))
        self.reset_button = QPushButton('Reset', self)
        self.reset_button.setFixedWidth(100), self.reset_button.setFont(QFont('Helvetica Neue', fs_font))

        # create grid and groups
        mlayout2 = QVBoxLayout()
        vbox2_top, vbox2_bottom, vbox2_middle = QHBoxLayout(), QHBoxLayout(), QVBoxLayout()
        mlayout2.addLayout(vbox2_top), mlayout2.addLayout(vbox2_middle), mlayout2.addLayout(vbox2_bottom)

        # add items to the layout grid
        # top part
        MsgGp = QGroupBox()
        MsgGp.setFont(QFont('Helvetica Neue', 12))
        # MsgGp.setMinimumWidth(300)
        gridMsg = QGridLayout()
        vbox2_top.addWidget(MsgGp)
        MsgGp.setLayout(gridMsg)

        # add GroupBox to layout and load buttons in GroupBox
        gridMsg.addWidget(self.msg, 1, 0)

        # in-between for sample plot
        plotGp = QGroupBox()
        plotGp.setFont(QFont('Helvetica Neue', 12))
        plotGp.setMinimumHeight(450)
        gridFig = QGridLayout()
        vbox2_middle.addWidget(plotGp)
        plotGp.setLayout(gridFig)

        # add GroupBox to layout and load buttons in GroupBox
        gridFig.addWidget(self.slider1EP, 1, 1)
        gridFig.addWidget(self.sldEP1_label, 1, 0)
        gridFig.addWidget(self.canvasEPs, 2, 1)
        gridFig.addWidget(self.naviEPs, 3, 1)
        gridFig.addWidget(EPtrim_label, 4, 0)
        gridFig.addWidget(self.EPtrim_edit, 4, 1)
        gridFig.addWidget(swiSample_label, 5, 0)
        gridFig.addWidget(self.swiSample_edit, 5, 1)

        # bottom group for navigation panel
        naviGp = QGroupBox("Navigation panel")
        naviGp.setFont(QFont('Helvetica Neue', 12))
        # naviGp.setMinimumWidth(300), \
        naviGp.setFixedHeight(75)
        gridNavi = QGridLayout()
        vbox2_bottom.addWidget(naviGp)
        naviGp.setLayout(gridNavi)

        # add GroupBox to layout and load buttons in GroupBox
        gridNavi.addWidget(self.close_button, 1, 0)
        gridNavi.addWidget(self.adjust_button, 1, 1)
        gridNavi.addWidget(self.reset_button, 1, 2)

        # add everything to the window layout
        self.setLayout(mlayout2)

    def onclick_updateEP(self, event):
        modifiers = QtWidgets.QApplication.keyboardModifiers()
        if modifiers == Qt.ControlModifier:
            # change selected range when control is pressed on keyboard
            # in case there are more than 2 points selected -> clear list and start over again
            if len(self.ls_cropy) >= 2:
                self.ls_cropy.clear()
            self.ls_cropy.append(event.ydata)

            # mark range in grey
            self._markHLine()

        if modifiers == Qt.ShiftModifier:
            # mark outlier when shift is pressed on keyboard
            self.ls_out.append(event.ydata)

    def slider1EP_update(self):
        # clear lists for another trial
        self.ls_out, self.ls_cropy = list(), list()

        if len(self.EPtrim_edit.text().split('-')) > 1:
            # assume that negative numbers occur
            ls = re.findall(r"[-+]?(?:\d*\.\d+|\d+)", self.EPtrim_edit.text())
            self.scale = (float(ls[0]), float(ls[1]))
        else:
            self.scale = (float(self.EPtrim_edit.text().split('-')[0]),
                          float(self.EPtrim_edit.text().split('-')[1].strip()))

        # allow only discrete values according to existing cores
        sample_select = min(self.ddata[self.Core].keys(), key=lambda x: abs(x - self.slider1EP.value()))

        # update slider position and label
        self.slider1EP.setValue(sample_select)
        self.sldEP1_label.setText('sample: {}'.format(sample_select))

        fig = plot_adjustEP(core=self.Core, sample=sample_select, dfCore=self.ddata[self.Core], col=self.colEP,
                            scale=self.scale, fig=self.figEPs, ax=self.axEPs)
        self.figEPs.canvas.draw()

    def _markHLine(self):
        # in case too many boundaries are selected, use the minimal/maximal values
        if len(self.ls_cropy) > 2:
            ls_crop = [min(self.ls_cropy), max(self.ls_cropy)]
        else:
            ls_crop = sorted(self.ls_cropy)

        # current core, current sample
        c, s = self.Core, int(self.sldEP1_label.text().split(' ')[-1])

        # span grey area to mark outside range
        if len(ls_crop) == 1:
            sub = (self.ddata[self.Core][s].index[0] - ls_crop[-1], self.ddata[self.Core][s].index[-1] - ls_crop[-1])
            if np.abs(sub[0]) < np.abs(sub[1]):
                # left outer side
                self.axEPs.axhspan(self.ddata[self.Core][s].index[0], ls_crop[-1], color='gray', alpha=0.3)
            else:
                # right outer side
                self.axEPs.axhspan(ls_crop[-1], self.ddata[self.Core][s].index[-1], color='gray', alpha=0.3)
        else:
            if ls_crop[-1] < ls_crop[0]:
                # left outer side
                self.axEPs.axhspan(self.ddata[self.Core][s].index[0], ls_crop[-1], color='gray', alpha=0.3)
            else:
                # left outer side
                self.axEPs.axhspan(ls_crop[-1], self.ddata[self.Core][s].index[-1], color='gray', alpha=0.3)

        # draw vertical line to mark boundaries
        [self.axEPs.axhline(x, color='k', ls='--', lw=0.5) for x in ls_crop]
        self.figEPs.canvas.draw()

    def updateEPscale(self):
        # get pH range form LineEdit
        if '-' in self.EPtrim_edit.text():
            if len(self.EPtrim_edit.text().split('-')) > 1:
                # assume that negative numbers occur
                ls = re.findall(r"[-+]?(?:\d*\.\d+|\d+)", self.EPtrim_edit.text())
                scale = (float(ls[0]), float(ls[1]))
            else:
                scale = (float(self.EPtrim_edit.text().split('-')[0]),
                         float(self.EPtrim_edit.text().split('-')[1].strip()))

        elif ',' in self.EPtrim_edit.text():
            scale = (float(self.EPtrim_edit.text().split(',')[0]),
                     float(self.EPtrim_edit.text().split(',')[1].strip()))
        else:
            scale = (float(self.EPtrim_edit.text().split(' ')[0]),
                     float(self.EPtrim_edit.text().split(' ')[1].strip()))

        # if pH range was updated by the user -> update self.scale (prevent further down)
        if scale != self.scale:
            self.scale = scale

        # update global variable
        global scaleEP
        scaleEP[self.Core] = (round(self.scale[0], 2), round(self.scale[1], 2))

    def cropDF_EP(self, s):
        if self.ls_cropy:
            # in case there was only 1 point selected -> extend the list to the other end
            if len(self.ls_cropy) == 1:
                sub = (self.ddata[self.Core][s].index[0] - self.ls_cropy[0],
                       self.ddata[self.Core][s].index[-1] - self.ls_cropy[0])
                if np.abs(sub[0]) < np.abs(sub[1]):
                    self.ls_cropy = [self.ls_cropy[0], self.ddata[self.Core][s].index[-1]]
                else:
                    self.ls_cropy = [self.ddata[self.Core][s].index[0], self.ls_cropy[0]]

            # actually crop the depth profile to the area selected.
            # In case more than 2 points have been selected, choose the outer ones -> trim y-axis
            dcore_crop = self.ddata[self.Core][s].loc[min(self.ls_cropy): max(self.ls_cropy)]
        else:
            dcore_crop = self.ddata[self.Core][s]
        return dcore_crop

    def popData_EP(self, dcore_crop):
        ls_pop = [min(dcore_crop.index.to_numpy(), key=lambda x: abs(x - self.ls_out[p]))
                  for p in range(len(self.ls_out))]
        # drop in case value is still there
        [dcore_crop.drop(p, inplace=True) for p in ls_pop if p in dcore_crop.index]
        return dcore_crop

    def adjustEP(self):
        # check if the pH range (scale) changed
        self.updateEPscale()
        self.status_EP = 1

        # current core, current sample
        c, s = self.Core, int(self.sldEP1_label.text().split(' ')[-1])

        # crop dataframe to selected range
        dcore_crop = self.cropDF_EP(s=s)
        # pop outliers from depth profile
        df_pop = self.popData_EP(dcore_crop=dcore_crop) if self.ls_out else dcore_crop

        # check individual swi for sample
        if '--' in self.swiSample_edit.text():
            pass
        else:
            # correction of manually selected baseline and store adjusted pH
            ynew = df_pop.index - float(self.swiSample_edit.text())
            df_pop = pd.DataFrame(df_pop.to_numpy(), index=ynew, columns=df_pop.columns)
            self.swiSample_edit.setText('--')

        # update the general dictionary
        self.ddata[self.Core][s] = df_pop
        fig = plot_EPUpdate(core=self.Core, nr=s, df=df_pop, ddcore=self.ddata[self.Core], col=self.colEP,
                            scale=self.scale, ax=self.axEPs, fig=self.figEPs)
        self.figEPs.canvas.draw()

        #  update range for pH plot and plot in main window
        self.EPtrim_edit.setText(str(round(self.scale[0], 2)) + ' - ' + str(round(self.scale[1], 2)))
        ls = '-.' if self.status_EP < 1 else '-'
        fig0 = plot_initalProfile(data=self.ddata, para='EP', unit='mV', col_name='EP_mV', core=self.Core, ls=self.ls,
                                  ls_core=self.ddata.keys(), dobj_hidEP=dobj_hidEP, fig=self.figEP, ax=self.axEP,
                                  trimexact=True)
        self.figEP.canvas.draw()
        self.status_EP += 1

    def resetPlotEP(self):
        print('start all over again and use the raw data')

    def close_windowEP(self):
        self.hide()


class DriftWindow(QDialog):
    def __init__(self, ls_core, ddata, dsheets, core_select, axEP, figEP):
        super().__init__()
        self.initUI()

        # get the transmitted data
        self.ddata, self.ls_core, self.dsheets, self.Core = ddata, ls_core, dsheets, core_select
        self.axEP, self.figEP = axEP, figEP
        self.dataDP, self.dataDC, self.Fitdone, self.dFit = dict(), dict(), list(), dict()

        # create a similar dictionary as EP adjusted
        for c in self.ddata.keys():
            ddic = dict()
            for i in self.ddata[c].keys():
                df_i = pd.DataFrame(np.array(self.ddata[c][i]), index=self.ddata[c][i].index,
                                    columns=self.ddata[c][i].columns)
                ddic[i] = df_i
            self.dataDC[c] = ddic

        # start with first profile package
        self.nP = 1

        # get meta data
        df = self.dsheets[self.dsheets['EP'] > 0][['deployment', 'code', 'EP']]
        self.dorder = dict(map(lambda n: (n, list([(int(t[1].split(' ')[-1]), t[0]) for t in df[df['EP'] == n].values])),
                               list(dict.fromkeys(df['EP'].to_numpy()))))

        # set slider to initial value
        self.sliderTD.setValue(self.nP), self.sldTD_label.setText('group: {}'.format(self.nP))
        self.sliderTD.setMinimum(min(self.dorder.keys())), self.sliderTD.setMaximum(max(self.dorder.keys()))

        # plot time-drive of the first group
        self.dataDP[self.nP] = dbs._getProfileStack(nP=self.nP, dataEP=self.ddata, dorder=self.dorder) # dfP_, dfP
        fig, self.axTD = plot_profileTime(nP=self.nP, df_pack=self.dataDP[self.nP][1], resultsEP=self.ddata,
                                          dorder=self.dorder, fig=self.figTD, ax=self.axTD)

        # when slider value change (on click), return new value and update figure plot
        self.sliderTD.valueChanged.connect(self.sliderTD_update)
        self.figTD.canvas.draw(), self.figCF.canvas.draw()

        # connect checkbox and load file button with a function
        self.closeDC_button.clicked.connect(self.close_windowSD)
        self.fit_button.clicked.connect(self.applyDriftCorr)

    def initUI(self):
        self.setWindowTitle("Sensor drift correction")
        self.setGeometry(450, 100, 650, 650)

        # Slider for different cores and label on the right
        self.sliderTD = QSlider(Qt.Horizontal)
        self.sliderTD.setMinimumWidth(350), self.sliderTD.setFixedHeight(20)
        self.sldTD_label = QLabel()
        self.sldTD_label.setFixedWidth(70), self.sldTD_label.setText('group: --')

        # plot time-drive profile package
        self.figTD, self.axTD = plt.subplots(figsize=(7, 4))
        self.figTD.set_facecolor("none")
        self.canvasTD = FigureCanvasQTAgg(self.figTD)
        self.axTD.set_xlabel('measurement points'), self.axTD.set_ylabel('EP / mV')
        self.figTD.subplots_adjust(bottom=0.2, right=0.95, top=0.85, left=0.15)
        sns.despine()

        # plot curve fit
        self.figCF, self.axCF = plt.subplots(figsize=(3, 2)) # width, height
        self.figCF.set_facecolor("none")
        self.canvasCF = FigureCanvasQTAgg(self.figCF)
        self.axCF.set_xlabel('profile number'), self.axCF.set_ylabel('average EP / mV')
        # self.figCF.subplots_adjust(bottom=0.2, right=0.95, top=0.85, left=0.15)
        sns.despine()

        # drop-down menu for curve fit selection
        self.FitSelect_box = QComboBox(self)
        ls_Fit = ['2nd order polynomial fit', 'linear regression']
        self.FitSelect_box.addItems(ls_Fit), self.FitSelect_box.setEditable(False)
        # self.FitSelect_box.setInsertPolicy(QComboBox.InsertAlphabetically)

        # report section
        self.msg = QLabel("Details about the curve fit: \n\n\n\n") # fit chosen | fit parameter | chi-square
        self.msg.setWordWrap(True), self.msg.setFont(QFont('Helvetica Neue', int(fs_font*1.15)))

        # close the window again
        self.closeDC_button = QPushButton('OK', self)
        self.closeDC_button.setFixedWidth(100), self.closeDC_button.setFont(QFont('Helvetica Neue', fs_font))
        self.fit_button = QPushButton('Fit', self)
        self.fit_button.setFixedWidth(100), self.fit_button.setFont(QFont('Helvetica Neue', fs_font))

        # create grid and groups
        layoutDC = QGridLayout()

        # add GroupBox to layout and load buttons in GroupBox
        # widget, fromRow, fromColumn, rowSpan, columnSpan, alignment or widget, row, column, alignment
        layoutDC.addWidget(self.sliderTD, 0, 0, 1, 2)
        layoutDC.addWidget(self.sldTD_label, 0, 2)
        layoutDC.addWidget(self.canvasTD, 1, 0, 1, 3)
        layoutDC.addWidget(self.canvasCF, 2, 0, 4, 1)
        layoutDC.addWidget(self.FitSelect_box, 2, 1, 1, 2)
        layoutDC.addWidget(self.msg, 3, 1, 2, 2)
        layoutDC.addWidget(self.closeDC_button, 5, 1)
        layoutDC.addWidget(self.fit_button, 5, 2)

        # Set the layout on the application's window
        self.setLayout(layoutDC)

    def sliderTD_update(self):
        self.axTD.cla(), self.axCF.cla(), self.figTD.suptitle('')
        self.msg.setText('Details about the curve fit: \n\n\n\n\n\n')

        # update slider position and label
        self.nP = min(self.dorder.keys(), key=lambda x: abs(x - self.sliderTD.value()))
        self.sldTD_label.setText('group: {}'.format(int(self.nP)))

        # re-draw figure
        self.dataDP[self.nP] = dbs._getProfileStack(nP=self.nP, dataEP=self.ddata, dorder=self.dorder)
        fig, self.axTD = plot_profileTime(nP=self.nP, df_pack=self.dataDP[self.nP][1], resultsEP=self.ddata,
                                          dorder=self.dorder, fig=self.figTD, ax=self.axTD)
        # in case also plot the already corrected profile
        if self.nP in self.Fitdone:
            dfP2_ = [self.dataDC[p[0]][p[1]].sort_index(ascending=True) for p in self.dorder[self.nP]]
            self.axTD.plot(pd.concat(dfP2_, axis=0)['EP_mV'].to_numpy(), color='darkorange', lw=1., label='corrected')
        self.figTD.canvas.draw(), self.figCF.canvas.draw()

    def applyDriftCorr(self):
        # set layout and add information about fitted profile package
        self.msg.clear(), self.axTD.cla(), self.axCF.cla()
        self.Fitdone.append(self.nP)

        # plot time-drive of the first group
        fig, self.axTD = plot_profileTime(nP=self.nP, df_pack=self.dataDP[self.nP][1], resultsEP=self.ddata,
                                          dorder=self.dorder, fig=self.figTD, ax=self.axTD)

        # drift correction
        # !!!TODO: make selected points for fitting as user input
        [ydata, df_reg, chi_squared, arg,
         corr_f] = dbs.curveFitPack(dfP_=self.dataDP[self.nP][0], numP=3, nP=self.nP, dorder=self.dorder,
                                    resultsEP=self.dataDC, fit_select=self.FitSelect_box.currentText())
        # store results in dfit dictionary
        self.dFit[self.nP] = dict({'average EP': ydata, 'regression curve': df_reg, 'chi-square': chi_squared,
                                   'correction factor': corr_f, 'regression': self.FitSelect_box.currentText(),
                                   'fit parameter': arg})

        # update profile time-drive
        dfP2_ = [self.dataDC[p[0]][p[1]].sort_index(ascending=True) for p in self.dorder[self.nP]]
        self.axTD.plot(pd.concat(dfP2_, axis=0)['EP_mV'].to_numpy(), color='darkorange', lw=1., label='corrected')
        nmin = np.min([self.axTD.get_ylim()[0], np.min(pd.concat(dfP2_, axis=0)['EP_mV'].to_numpy())])
        nmax = np.max([self.axTD.get_ylim()[1], np.max(pd.concat(dfP2_, axis=0)['EP_mV'].to_numpy())])

        self.axTD.set_ylim(nmin, nmax)
        self.axTD.set_title(''), self.figTD.suptitle('EP drift corrected profile for group {}'.format(int(self.nP)))
        self.figTD.canvas.draw()

        # plot fit results
        figR, axR = plot_Fit(df_reg=df_reg, ydata=ydata, figR=self.figCF, axR=self.axCF, show=True)
        self.figCF.canvas.draw()

        # add results to the report
        if pd.isna(corr_f).all():
            self.msg.setText('Details about the curve fit: \n\nnothing to report\n\n\n\n')
        else:
            if self.FitSelect_box.currentText() == '2nd order polynomial fit':
                self.msg.setText('Details about the curve fit:\ngoodness of fit: {:.2e} \n\nfit parameter: \na = {:.2e}'
                                 '\n b = {:.2e}\n c = {:.2e}'.format(chi_squared, corr_f[0], corr_f[1], corr_f[2]))
            elif self.FitSelect_box.currentText() == 'linear regression':
                self.msg.setText('Details about the curve fit:\ngoodness of fit: {:.2e} \n\nfit parameter: '
                                 '\na = {:.2e}\nb = {:.2e}\n'.format(chi_squared, corr_f[0], corr_f[1]))

    def close_windowSD(self):
        results['EP adjusted'] = self.dataDC
        results['EP profile drift'] = self.dataDP
        results['EP drift correction'] = self.dFit
        results['EP order'] = self.dorder
        figEP0 = plot_initalProfile(data=self.dataDC, para='EP', unit='mV', core=self.Core, ls='-', col_name='EP_mV',
                                    ls_core=self.ls_core, dobj_hidEP=dobj_hidEP, ax=self.axEP, fig=self.figEP,
                                    trimexact=True)
        self.hide()


def fig4saving_EP(ls_core, draw, dadj, ddrift, dfit):
    dfigRaw, dfigBase, dfigDC, dfigFit = dict(), dict(), dict(), dict()
    # raw data and adjusted data
    for c in ls_core:
        dfigRaw[c] = plot_initalProfile(data=draw, para='EP', unit='mV', core=c, ls='-.', col_name='EP_mV', show=False,
                                        ls_core=ls_core, dobj_hidEP=dobj_hidEP, trimexact=True)
        dfigBase[c] = plot_initalProfile(data=dadj, para='EP', unit='mV', core=c, ls='-', col_name='EP_mV', show=False,
                                        ls_core=ls_core, dobj_hidEP=dobj_hidEP, trimexact=True)

    # profile drift for individual groups + curve fitting
    for g in ddrift.keys():
        df, ax = plot_profileTime(nP=g, df_pack=ddrift[g][1], resultsEP=dadj, dorder=results['EP order'], show=False)
        dfP2_ = [dadj[p[0]][p[1]].sort_index(ascending=True) for p in results['EP order'][g]]
        ax.plot(pd.concat(dfP2_, axis=0)['EP_mV'].to_numpy(), color='darkorange', lw=1., label='corrected')
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
            dfigDC[g] = figR

    return dfigRaw, dfigBase, dfigDC, dfigFit


def plot_profileTime(nP, df_pack, resultsEP, dorder, fig=None, ax=None, show=True):
    plt.ioff()
    # plot all profiles belonging to the same pacakge
    if ax is None:
        fig, ax = plt.subplots()
    else:
        ax.cla()
    ax.set_xlabel('measurement point'), ax.set_ylabel('EP / mV')
    ax.set_title('EP profile over time for selected group {}'.format(nP))

    # plotting
    a = ax.plot(df_pack['EP_mV'].to_numpy(), marker='.', lw=0, label='original profiles')

    # indicate horizontal axes after individual profiles and add profile information
    len_prof = [len(resultsEP[p[0]][p[1]].sort_index(ascending=True)) for p in dorder[nP]]
    ls_label = ['(' + str(p[0]) + '|' + str(p[1]) +')' for p in dorder[nP]]

    height = max(df_pack['EP_mV'].to_numpy())
    m, en = len_prof[0], 0
    for en, l in enumerate(len_prof):
        if en >= len(len_prof)-1:
            ax.annotate(ls_label[en], xy=(m - l /2, height), xytext=(0, 15),  textcoords='offset points', ha='center',
                        va='bottom', fontsize=6)
        else:
            ax.axvline(m, color='k', lw=0.75)
            ax.annotate(ls_label[en], xy=(m-l/2, height), xytext=(0, 15), textcoords='offset points', ha='center',
                        va='bottom', fontsize=6)
        m += l

    sns.despine(), plt.tight_layout(pad=0.5)
    ylim = ax.get_ylim()
    ax.set_ylim(ylim[0], ylim[1]*1.05)

    if show is True:
        fig.canvas.draw()
    else:
        plt.close()
    return fig, ax


def plot_Fit(df_reg, ydata, figR=None, axR=None, show=True):
    plt.ioff()
    if axR is None:
        figR, axR = plt.subplots(figsize=(5, 3))
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


def plot_initalProfile(data, para, unit, col_name, core, ls_core, dobj_hidEP, ls='-.', fig=None, ax=None, show=True,
                       trimexact=False):
    plt.ioff()
    lines = list()
    # identify closest value in list
    if isinstance(core, float) or isinstance(core, int):
        core = _findCoreLabel(option1=core, option2='core ' + str(core), ls=ls_core)
    core_select = dbs.closest_core(ls_core=ls_core, core=core)

    # initialize figure
    if ax is None:
        fig, ax = plt.subplots(figsize=(3, 4))
    else:
        ax.cla()
    ax.set_xlabel('{} / {}'.format(para, unit)), ax.set_ylabel('Depth / µm')
    ax.invert_yaxis()

    if core_select != 0:
        ax.title.set_text('{} depth profile for {} {}'.format(grp_label, para, core_select))
        ax.axhline(0, lw=.5, color='k')
        for en, nr in enumerate(data[core_select].keys()):
            if core_select in dobj_hidEP.keys():
                # if nr (sample) in dictionary of hidden samples, set alpha_ as .1 else as .6
                alpha_ = .0 if 'sample ' + str(nr) in dobj_hidEP[core_select] else .6
            else:
                alpha_ = .6
            lw = 0.75 if ls == '-.' else 1.
            mark = '.' if ls == '-.' else None

            line, = ax.plot(data[core_select][nr][col_name], data[core_select][nr].index, lw=lw, ls=ls, marker=mark,
                            alpha=alpha_, color=ls_col[en], label='sample ' + str(nr))
            lines.append(line)
        leg = ax.legend(frameon=True, fontsize=fs_*0.8)

        # ------------------------------------------------------------------
        # combine legend
        lined = dict()
        for legline, origline in zip(leg.get_lines(), lines):
            legline.set_picker(5)  # 5 pts tolerance
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
    if core_select in scaleEP.keys():
        min_ = np.nanmin(scaleEP[core_select])
        max_ = np.nanmax(scaleEP[core_select])
    else:
        min_ = np.nanmin([data[core_select][nr][col_name].min() for nr in data[core_select].keys()])
        max_ = np.nanmax([data[core_select][nr][col_name].max() for nr in data[core_select].keys()])

    if trimexact is False:
        min_, max_ = min_*0.985, max_*1.015
    ax.set_xlim(min_, max_)
    fig.tight_layout(pad=1.5)

    if show is True:
        fig.canvas.draw()
    else:
        plt.close()
    return fig


def plot_adjustEP(core, sample, col, dfCore, scale, fig=None, ax=None):
    # initialize first plot with first core and sample
    fig = GUI_adjustDepthEP(core=core, nr=sample, dfCore=dfCore, col=col, scale=scale, fig=fig, ax=ax)
    fig.canvas.draw()
    return fig


def plot_EPUpdate(core, nr, df, ddcore, scale, col, fig, ax):
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


def GUI_adjustDepthEP(core, nr, dfCore, scale, col, fig=None, ax=None, show=True):
    plt.ioff()
    # initialize figure plot
    if ax is None:
        fig, ax = plt.subplots(figsize=(5, 3))
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
    scale_min = -1 * scale[1]/10 if scale[0] == 0 else scale[0]*0.95
    #ax.set_xlim(scale_min, scale[1]*1.015)
    ax.invert_yaxis(), sns.despine(), fig.subplots_adjust(bottom=0.2, right=0.95, top=0.8, left=0.215)

    if show is False:
        plt.close(fig)
    else:
        fig.canvas.draw()
    return fig


# -----------------------------------------------
class charPage(QWizardPage):
    def __init__(self, parent=None):
        super(charPage, self).__init__(parent)
        self.setTitle("Further sediment characterization")
        self.setSubTitle("On the next slide, you will first select which profiles shall be used for averaging for an "
                         "individual group,  e.g.  core. Then,  you can choose to plot different parameters together"
                         " in a joint plot. \n")

        # create layout
        # self.initUI()

        # when all conditions are met, enable NEXT button
        self.ls_next = QLineEdit()

    # def initUI(self):
        # creating window layout
        # w2 = QWidget()
        # mlayout2 = QVBoxLayout(w2)
        # vbox_top, vbox_middle, vbox_bottom = QHBoxLayout(), QHBoxLayout(), QHBoxLayout()
        # mlayout2.addLayout(vbox_top), mlayout2.addLayout(vbox_middle), mlayout2.addLayout(vbox_bottom)
        #
        # para_settings = QGroupBox("Sediment analysis and output")
        # grid_set = QGridLayout()
        # para_settings.setFont(QFont('Helvetica Neue', 12))
        # vbox_middle.addWidget(para_settings)
        # para_settings.setFixedHeight(150)
        # para_settings.setLayout(grid_set)
        # self.setLayout(mlayout2)

    def nextId(self) -> int:
        return wizard_page_index["averageLP"]


# -----------------------------------------------
class avProfilePage(QWizardPage):
    def __init__(self, parent=None):
        super(avProfilePage, self).__init__(parent)
        self.setTitle("Average depth profiles")
        self.setSubTitle("The averaging is done for each anaylte and each core.  First load all available profiles by"
                         "pressing Update.  Now,  you can deselect all profiles,  that shall not be considered for "
                         "averaging.  You can do so either by clearing the respective cell or by inserting an N.")

        # create layout
        self.initUI()
        self.dcore = dict()

        # fill the table in the different tabs
        self.fill_tabula()

        # connect checkbox and load file button with a function
        self.update_btn.clicked.connect(self.fill_tabula)
        self.average_btn.clicked.connect(self.average_profiles)
        self.clear_btn.clicked.connect(self.reset_tabula)
        self.save_btn.clicked.connect(self.save_avProfiles)

    def initUI(self):
        # create update button
        self.update_btn = QPushButton('Update', self)
        self.update_btn.setFixedWidth(100), self.update_btn.setFont(QFont('Helvetica Neue', fs_font))
        self.average_btn = QPushButton('Averaging', self)
        self.average_btn.setFixedWidth(100), self.average_btn.setFont(QFont('Helvetica Neue', fs_font))
        self.clear_btn = QPushButton('Clear', self)
        self.clear_btn.setFixedWidth(100), self.clear_btn.setFont(QFont('Helvetica Neue', fs_font))
        self.save_btn = QPushButton('Save', self)
        self.save_btn.setFixedWidth(100), self.save_btn.setFont(QFont('Helvetica Neue', fs_font))

        # initiate tables of available core / sample profiles for all parameters
        self.tabula_O2, self.tabula_pH, self.tabula_H2S = self.Tablula(), self.Tablula(), self.Tablula()
        self.tabula_EP = self.Tablula()

        # creating window layout
        w = QWidget()
        mlayout2 = QVBoxLayout(w)
        vbox_top, vbox = QHBoxLayout(), QVBoxLayout()
        mlayout2.addLayout(vbox_top), mlayout2.addLayout(vbox)

        # table of core / available sample profiles and a column to select the profiles to be averaged
        self.tabs_1 = QTabWidget()
        self.tab1_1, self.tab2_1, self.tab3_1, self.tab4_1 = QWidget(), QWidget(), QWidget(), QWidget()

        # Add tabs
        self.tabs_1.addTab(self.tab1_1, "O2")
        self.tabs_1.addTab(self.tab2_1, "pH")
        self.tabs_1.addTab(self.tab3_1, "H2S/total sulfide ΣS2")
        self.tabs_1.addTab(self.tab4_1, "EP")

        # Add tabs to widget
        vbox.addWidget(self.tabs_1)
        # add tables to respective tab
        self.O2vbox = QVBoxLayout(self.tab1_1)
        self.O2vbox.addWidget(self.tabula_O2)
        self.pHvbox = QVBoxLayout(self.tab2_1)
        self.pHvbox.addWidget(self.tabula_pH)
        self.H2Svbox = QVBoxLayout(self.tab3_1)
        self.H2Svbox.addWidget(self.tabula_H2S)
        self.EPvbox = QVBoxLayout(self.tab4_1)
        self.EPvbox.addWidget(self.tabula_EP)

        # add update button to the layout
        vbox_top.addWidget(self.update_btn)
        vbox_top.addWidget(self.average_btn)
        vbox_top.addWidget(self.clear_btn)
        vbox_top.addWidget(self.save_btn)

        self.setLayout(mlayout2)

    def Tablula(self):
        tabula = QTableWidget(self)
        tabula.setColumnCount(3), tabula.setRowCount(1)
        tabula.setHorizontalHeaderLabels(['Group', 'Profile-ID', 'Include for averaging'])
        tabula.resizeColumnsToContents(), tabula.resizeRowsToContents()
        tabula.adjustSize()
        return tabula

    def _getProfileLabels(self, para):
        ls_par = list()
        [ls_par.append(k) for k in results.keys() if para in k]

        # get information on group / profile-ID
        dcore = None
        if ls_par and para == 'O2':
            dcore = dict()
            for c in results[ls_par[0]].keys():
                ls = list()
                [ls.append(i[0]) if isinstance(i, tuple) else ls.append(i) for i in results[ls_par[0]][c].keys()]
                dcore[intLab(c)] = ls
        elif ls_par and para != 'O2':
                dcore = dict(map(lambda c: (intLab(c), list(results[ls_par[0]][c].keys())), results[ls_par[0]].keys()))
        return dcore

    def _fill_tabula(self, dcore, tabula_par):
        # get number of columns in table
        new_row = tabula_par.rowCount()
        x0 = new_row - 1
        # check whether this (last) row is empty
        item = tabula_par.item(x0, 0)
        x = x0 if not item or not item.text() else x0 + 1

        # add the number of rows according to keys in dictionary
        nrows = np.sum([len(dcore[n]) for n in list(dcore.keys())])
        tabula_par.setRowCount(nrows)

        # actually fill the table
        for k in dcore.keys():
            itemGrp = QTableWidgetItem(str(k))
            itemGrp.setTextAlignment(Qt.AlignRight)
            for en, p in enumerate(dcore[k]):
                item = QTableWidgetItem(str(p))
                item.setTextAlignment(Qt.AlignRight)

                # per default all profiles are used for averaging
                itemSel = QTableWidgetItem(str('Y'))
                itemSel.setTextAlignment(Qt.AlignRight)

                # item structure: row, table, content
                tabula_par.setItem(x, 0, itemGrp)   # fill in the group label information
                tabula_par.setItem(x, 1, item)      # fill in the profile ID
                tabula_par.setItem(x, 2, itemSel)   # fill in a default "Y" selection

                # go to the next row
                x += 1

    def fill_tabula(self):
        # actually fill current table with information
        if self.tabs_1.currentIndex() == 0:
            dcore = self._getProfileLabels(para='O2')
            self.dcore['O2'] = dcore
            if dcore:
                self._fill_tabula(dcore=dcore, tabula_par=self.tabula_O2)
                self.tabula_O2.resizeColumnsToContents(), self.tabula_O2.resizeRowsToContents()
        elif self.tabs_1.currentIndex() == 1:
            dcore = self._getProfileLabels(para='pH')
            self.dcore['pH'] = dcore
            if dcore:
                self._fill_tabula(dcore=dcore, tabula_par=self.tabula_pH)
                self.tabula_pH.resizeColumnsToContents(), self.tabula_pH.resizeRowsToContents()
        elif self.tabs_1.currentIndex() == 2:
            dcore = self._getProfileLabels(para='H2S')
            self.dcore['H2S'] = dcore
            if dcore:
                self._fill_tabula(dcore=dcore, tabula_par=self.tabula_H2S)
                self.tabula_H2S.resizeColumnsToContents(), self.tabula_H2S.resizeRowsToContents()
        else:
            dcore = self._getProfileLabels(para='EP')
            self.dcore['EP'] = dcore
            if dcore:
                self._fill_tabula(dcore=dcore, tabula_par=self.tabula_EP)
                self.tabula_EP.resizeColumnsToContents(), self.tabula_EP.resizeRowsToContents()

    def _specifyFilter(self, analyte):
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

    def averageRemains(self, analyte, col, k, dav_par, dav_):
        if len(dav_.keys()) > 1:
            df = pd.concat([dav_[i] for i in dav_.keys()], axis=1).astype(float)
            if self._specifyFilter(analyte=analyte) in df.keys():
                dav_par[k] = df[self._specifyFilter(analyte=analyte)].mean(axis=1, skipna=True)
            else:
                if 'O2' in analyte:
                    filter_ = 'O2_µmol/L'
                elif 'H2S' in analyte:
                    filter_ = 'total sulfide zero corr_µmol/L'
                else:
                    filter_ = None
                dav_par[k] = df[filter_].mean(axis=1, skipna=True)
        else:
            dav_par[k] = pd.DataFrame(dav_[col])
        return dav_par

    def _getAverageProfile(self, searchK, ls_pop):
        dav_par = dict()
        for k in results[searchK].keys():
            dav_par_ = dict()
            for p in results[searchK][k].keys():
                if isinstance(p, tuple):
                    if p[0] not in ls_pop:
                        col = p[0]
                        dav_par_[col] = results[searchK][k][col]
                else:
                    if p not in ls_pop:
                        col = p
                        dav_par_[col] = results[searchK][k][col]

            # average the remaining profiles
            dav_par = self.averageRemains(analyte=searchK, col=col, k=k, dav_par=dav_par, dav_=dav_par_)
        return dav_par

    def exeAverageProfileTab(self, tab, searchK1, searchK2):
        # get information which profiles to remove
        ls_pop = list()
        for c in range(tab.rowCount()):
            if tab.item(c, 2).text() in ['N', 'n', '']:
                ls_pop.append(int(tab.item(c, 1).text()))

        # average remaining profiles (adjusted if in list else raw)
        if searchK1 in list(results.keys()):
            dav_par = self._getAverageProfile(searchK=searchK1, ls_pop=ls_pop)
        else:
            if searchK2 in list(results.keys()):
                dav_par = self._getAverageProfile(searchK=searchK2, ls_pop=ls_pop)
            else:
                dav_par = None
        return dav_par

    def average_profiles(self):
        global dav
        if self.tabs_1.currentIndex() == 0:
            dav_o2 = self.exeAverageProfileTab(tab=self.tabula_O2, searchK1='O2 profile', searchK2='O2 raw data')
            dav['O2'] = dav_o2
        if self.tabs_1.currentIndex() == 1:
            dav_pH = self.exeAverageProfileTab(tab=self.tabula_O2, searchK1='pH adjusted',
                                               searchK2='pH profile raw data')
            dav['pH'] = dav_pH
        if self.tabs_1.currentIndex() == 2:
            dav_h2s = self.exeAverageProfileTab(tab=self.tabula_O2, searchK1='H2S adjusted',
                                                searchK2='H2S profile raw data')
            dav['H2S'] = dav_h2s
        else:
            dav_ep = self.exeAverageProfileTab(tab=self.tabula_O2, searchK1='EP adjusted', searchK2='EP raw data')
            dav['EP'] = dav_ep

        # return message to continue
        msgBox = QMessageBox()
        msgBox.setIcon(QMessageBox.Information)
        msgBox.setText("Averaging successful!  Please continue to the tab or the next sheet and select the parameters "
                       "that shall be plotted together.")
        msgBox.setFont(QFont('Helvetica Neue', 11))
        msgBox.setWindowTitle("Great job!")
        msgBox.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
        msgBox.exec()

    def save_avProfiles(self):
        # make a project folder for the specific analyte if it doesn't exist
        save_path = self.field("Storage path")
        if not os.path.exists(save_path):
            os.makedirs(save_path)

        # make for each analyte a separate sheet
        dout_av = dict()
        for c in dav.keys():
            if dav[c]:
                dout_av[c] = pd.concat(dav[c], axis=1)

        savename = dbs._actualFileName(savePath=save_path, file=self.field("Data"))
        savename = savename.split('.')[0] + '_avProfiles.xlsx'

        # actually saving DataFrame to excel
        writer = pd.ExcelWriter(savename)
        for key in dout_av.keys():
            dout_av[key].to_excel(writer, sheet_name=key)
        writer.save()
        writer.close()

    def reset_tabula(self):
        global dav
        dav = dict()
        self.dcore = dict()

        #!!!TODO: how to make it still reachable?
        if self.tabs_1.currentIndex() == 0:
            self.tabula_O2.clearContents()
        elif self.tabs_1.currentIndex() == 1:
            self.tabula_pH.clearContents()
        elif self.tabs_1.currentIndex() == 2:
            self.tabula_H2S.clearContents()
        else:
            self.tabula_EP.clearContents()

    def nextId(self) -> int:
        return wizard_page_index['joint plots']


# -----------------------------------------------
class jointPlotPage(QWizardPage):
    def __init__(self, parent=None):
        super(jointPlotPage, self).__init__(parent)
        self.setTitle("Joint plots of different parameters")
        self.setSubTitle("\n")
        self.initUI()

        # create required parameters
        self.ls_jPlot = list()

        # connect checkbox and load file button with a function
        self.o2_bx.clicked.connect(self.paraCollection)
        self.ph_bx.clicked.connect(self.paraCollection)
        self.h2s_bx.clicked.connect(self.paraCollection)
        self.ep_bx.clicked.connect(self.paraCollection)
        self.spec_btn.clicked.connect(self.specifyGroups)
        self.plot_btn.clicked.connect(self.plot_joProfile)
        self.adj_btn.clicked.connect(self.adjust_profile)
        self.clear_btn.clicked.connect(self.clear_profile)
        # self.save_btn.clicked.connect(self.save_jointProfiles)

    def initUI(self):
        # checkbox for which parameters shall be plotted together
        self.o2_bx = QCheckBox('Oxygen O2', self)
        self.ph_bx = QCheckBox('pH', self)
        self.h2s_bx = QCheckBox('total sulfide ΣS2- / H2S', self)
        self.ep_bx = QCheckBox('EP', self)
        self.o2_bx.setFont(QFont('Helvetica Neue', 12)), self.ph_bx.setFont(QFont('Helvetica Neue', 12)),
        self.h2s_bx.setFont(QFont('Helvetica Neue', 12)), self.ep_bx.setFont(QFont('Helvetica Neue', 12))

        # open additional window to classify which cores shall be plotted together
        self.spec_btn = QPushButton('Specify joint groups', self)
        self.spec_btn.setFixedWidth(150), self.spec_btn.setFont(QFont('Helvetica Neue', fs_font))
        self.plot_btn = QPushButton('Plot', self)
        self.plot_btn.setFixedWidth(100), self.plot_btn.setFont(QFont('Helvetica Neue', fs_font))
        self.adj_btn = QPushButton('Adjust', self)
        self.adj_btn.setFixedWidth(150), self.adj_btn.setFont(QFont('Helvetica Neue', fs_font))
        self.clear_btn = QPushButton('Clear', self)
        self.clear_btn.setFixedWidth(100), self.clear_btn.setFont(QFont('Helvetica Neue', fs_font))
        self.save_btn = QPushButton('Save', self)
        self.save_btn.setFixedWidth(100), self.save_btn.setFont(QFont('Helvetica Neue', fs_font))

        # Slider for different cores and label on the right
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setMinimumWidth(350), self.slider.setFixedHeight(20)
        self.sld_label = QLabel()
        self.sld_label.setFixedWidth(55)
        self.sld_label.setText('group: --')

        # creating main window (GUI)
        w = QWidget()
        # create layout grid
        mlayout = QVBoxLayout(w)
        vbox_top, vbox_middle, vbox_bottom = QVBoxLayout(), QHBoxLayout(), QHBoxLayout()
        mlayout.addLayout(vbox_top), mlayout.addLayout(vbox_middle), mlayout.addLayout(vbox_bottom)

        btn_grp = QGroupBox()
        grid_btn = QGridLayout()
        btn_grp.setFont(QFont('Helvetica Neue', 12)), btn_grp.setFixedHeight(75)
        btn_grp.setMinimumWidth(650)
        vbox_top.addWidget(btn_grp)
        btn_grp.setLayout(grid_btn)

        # include widgets in the layout
        grid_btn.addWidget(self.o2_bx, 0, 0)
        grid_btn.addWidget(self.ph_bx, 0, 1)
        grid_btn.addWidget(self.h2s_bx, 0, 2)
        grid_btn.addWidget(self.ep_bx, 0, 3)

        grid_btn.addWidget(self.spec_btn, 2, 0)
        grid_btn.addWidget(self.plot_btn, 2, 1)
        grid_btn.addWidget(self.adj_btn, 2, 2)
        grid_btn.addWidget(self.clear_btn, 2, 3)
        grid_btn.addWidget(self.save_btn, 2, 4)

        # draw additional "line" to separate parameters from plots and to separate navigation from rest
        vline = QFrame()
        vline.setFrameShape(QFrame.HLine | QFrame.Raised)
        vline.setLineWidth(2)
        vbox_middle.addWidget(vline)

        # plotting area
        self.figJ, self.axJ = plt.subplots(figsize=(3, 4))
        self.axJ1 = self.axJ.twiny()
        self.canvasJ = FigureCanvasQTAgg(self.figJ)
        self.axJ.set_ylabel('Depth / µm'), self.axJ.set_xlabel('analyte'), self.axJ1.set_xlabel('analyte 2')
        self.axJ.invert_yaxis()
        self.figJ.subplots_adjust(bottom=0.2, right=0.95, top=0.75, left=0.15)

        JPlot_grp = QGroupBox("Joint depth profile")
        JPlot_grp.setMinimumHeight(500)
        grid_jPlot = QGridLayout()

        # add GroupBox to layout and load buttons in GroupBox
        vbox_bottom.addWidget(JPlot_grp)
        JPlot_grp.setLayout(grid_jPlot)
        grid_jPlot.addWidget(self.slider, 1, 0)
        grid_jPlot.addWidget(self.sld_label, 1, 1)
        grid_jPlot.addWidget(self.canvasJ, 2, 0)
        self.setLayout(mlayout)

    def paraCollection(self):
        if self.o2_bx.isChecked():
            self.ls_jPlot.append('O2')
        if self.ph_bx.isChecked():
            self.ls_jPlot.append('pH')
        if self.h2s_bx.isChecked():
            self.ls_jPlot.append('H2S')
        if self.ep_bx.isChecked():
            self.ls_jPlot.append('EP')
        self.ls_jPlot = list(dict.fromkeys(self.ls_jPlot))

    def _getParaGroups(self):
        lsGrp1, lsGrp2, lsGrp3, lsGrp4 = None, None, None, None
        for p in self.ls_jPlot:
            lsGrp = list(dav[p].keys())
            if p == 'O2':
                lsGrp1 = lsGrp
            elif p == 'pH':
                lsGrp2 = lsGrp
            elif p == 'H2S':
                lsGrp3 = lsGrp
            elif p == 'EP':
                lsGrp4 = lsGrp
        return lsGrp1, lsGrp2, lsGrp3, lsGrp4

    def specifyGroups(self):
        # get the group labels of each selected parameter (maximum four parameters)
        lsGrp1, lsGrp2, lsGrp3, lsGrp4 = self._getParaGroups()

        # open new window and have a click collection for each profile of the first parameter
        global wSpecGp
        wSpecGp = specGroup(lsGrp1, lsGrp2, lsGrp3, lsGrp4, self.ls_jPlot)
        if wSpecGp.isVisible():
            pass
        else:
            wSpecGp.show()

    def adjust_profile(self):
        print('make trimming of yaxis and xaxis scaling for individual parameter possible')
        global wAdj_jP
        wAdj_jP = AdjustjPWindow()
        if wAdj_jP.isVisible():
            pass
        else:
            wAdj_jP.show()

    def slider_update(self):
        global tabcorr
        # allow only discrete values according to existing cores
        grp_select = min(np.arange(0, len(tabcorr.index)), key=lambda x: abs(x - self.slider.value()))

        # update slider position and label
        self.slider.setValue(int(grp_select))
        self.sld_label.setText('group: {}'.format(grp_select))
        self._plot_joProfile1Core(sval=grp_select)
        self.figJ.canvas.draw()

    def plot_joProfile(self):
        global tabcorr
        # slider initialized to first core
        self.slider.setMinimum(0), self.slider.setMaximum(int(len(tabcorr.index)-1))
        self.slider.setValue(0)
        self.sld_label.setText('group: {}'.format(0))

        # plot initial joint plot for group 0
        self._plot_joProfile1Core(sval=self.slider.value())

        # when slider value change (on click), return new value and update figure plot
        self.slider.valueChanged.connect(self.slider_update)

        # in case the FitWindow is open -> update figFit according to selected sliderValue
        # self.slider.sliderReleased.connect(self.wFit_update)
        self.figJ.canvas.draw()

    def _plot_joProfile1Core(self, sval):
        # clear all previous plots in figure
        [ax.cla() for ax in self.figJ.axes]
        self.axJ.invert_yaxis()

        # get the profiles and correlation matrix for the different parameters
        global tabcorr
        self.ls_jPlot = list(dict.fromkeys(self.ls_jPlot))

        # create a template of the figure including required additional axes
        self.templateFigure()
        ls_axes = self.figJ.axes # axes labels: 0: O2, 1: pH, 2: EP, 3: H2S
        # remove surplus axes
        self.removeIdleAxes(ls_axes)

        # fill the axes with averaged profiles
        em = 0
        for en, para in enumerate(self.ls_jPlot):
            em += en
            self.sld_label.setText('group: {}'.format(sval))
            # !!! Make sure the counting / parameter to axes arrangement is correct - it isn't right now (en)
            pkeys = tabcorr[para].to_numpy()
            colK = _findCoreLabel(option1=pkeys[sval], option2='core {}'.format(pkeys[sval]), ls=list(dav[para].keys()))

            if para == 'H2S':
                ls_axes[en+1].plot(dav[para][colK].values, dav[para][colK].index, lw=0.75, color=ls_col[em])
                ls_axes[en+1].xaxis.label.set_color(ls_col[em]), ls_axes[en+1].tick_params(axis='x', colors=ls_col[em])
            elif para == 'EP':
                ls_axes[en-1].plot(dav[para][colK].values, dav[para][colK].index, lw=0.75, color=ls_col[em])
                ls_axes[en-1].xaxis.label.set_color(ls_col[em]), ls_axes[en-1].tick_params(axis='x', colors=ls_col[em])
            else:
                ls_axes[en].plot(dav[para][colK].values, dav[para][colK].index, lw=0.75, color=ls_col[em])
                ls_axes[en].xaxis.label.set_color(ls_col[em]), ls_axes[en].tick_params(axis='x', colors=ls_col[em])

            ls_axes[en].axhline(0, color='k', lw=0.5)

        # make it a pretty layout
        if len(ls_axes) > 2:
            self.layout4Axes()

        self.axJ.invert_yaxis()
        self.figJ.subplots_adjust(bottom=0.25, right=0.9, top=0.7, left=0.15)
        self.figJ.canvas.draw()

    def removeIdleAxes(self, ls_axes):
        if 'O2' not in self.ls_jPlot:
            ls_axes[0].set_axis_off()
        if 'pH' not in self.ls_jPlot:
            ls_axes[1].set_axis_off()
        if 'EP' not in self.ls_jPlot:
            ls_axes[2].set_axis_off()
        if 'H2S' not in self.ls_jPlot:
            ls_axes[3].set_axis_off()

    def layout4Axes(self):
        self.axJ2.set_xlabel('EP / mV', fontsize=fs_, color='k', labelpad=15)  # EP at additional bottom axes
        self.axJ3.set_xlabel('total sulfide or H2S / µmol/L', fontsize=fs_, color='k')  # H2S at additional top axes

        # make positioning of (additional) axes right
        self.axJ2.spines["top"].set_position(("axes", 1.25))
        makePatchSpinesInVis(ax=self.axJ2), makePatchSpinesInVis(ax=self.axJ3)

        self.axJ3.xaxis.set_ticks_position('bottom'), self.axJ3.xaxis.set_label_position('bottom')
        self.axJ3.spines['bottom'].set_position(('outward', 36))

        self.axJ2.spines["top"].set_visible(True), self.axJ3.spines["bottom"].set_visible(True)

    def templateFigure(self):
        # always four axes but remove axes the ones that are not needed. That way, you make sure that the same parameter
        # is always at the same position
        ls_axes = self.figJ.axes
        ls_axes[0].set_xlabel('O2 concentration / µmol/L', fontsize=fs_, color='k')  # O2 at bottom axes
        ls_axes[1].set_xlabel('pH', fontsize=fs_, color='k')  # pH at top axes

        if len(ls_axes) <= 2:
            self.axJ2, self.axJ3 = self.axJ.twiny(), self.axJ.twiny()
            self.layout4Axes()
        self.axJ1.spines["top"].set_visible(True), self.axJ.spines["bottom"].set_visible(True)
        self.axJ.spines["top"].set_visible(True), self.axJ1.spines["bottom"].set_visible(True)

        # layout and final drawing
        self.axJ.set_ylabel('Depth / µm'), self.axJ.invert_yaxis()
        self.figJ.tight_layout(pad=1.5) # subplots_adjust(bottom=0.25, right=0.95, top=0.75, left=0.15)
        self.figJ.canvas.draw()

    def clear_profile(self):
        [ax.cla() for ax in self.figJ.axes]
        for ax in self.figJ.axes:
            [t.set_color('k') for t in ax.xaxis.get_ticklines()]
            [t.set_color('k') for t in ax.xaxis.get_ticklabels()]
        self.templateFigure()
        self.figJ.canvas.draw()

        # deselect all parameters
        self.o2_bx.setChecked(False), self.ph_bx.setChecked(False)
        self.h2s_bx.setChecked(False), self.ep_bx.setChecked(False)

        # re-create (empty) required parameters
        self.ls_jPlot = list()

    def nextId(self) -> int:
        return wizard_page_index['final page']


class specGroup(QDialog):
    def __init__(self, lsGrp1, lsGrp2, lsGrp3, lsGrp4, ls_jPlot):
        super().__init__()

        # setting title
        self.setWindowTitle("Correlation of group profiles")
        self.setGeometry(800, 100, 500, 500)

        # getting the parameter
        self.lsCore1, self.lsCore2, self.lsCore3, self.lsCore4 = lsGrp1, lsGrp2, lsGrp3, lsGrp4
        self.ls_para = ls_jPlot

        # calling method
        self.initUI()

        # connect checkbox and load file button with a function
        self.ok_button.clicked.connect(self.close)
        self.clear_button.clicked.connect(self.clear)

    def initUI(self):
        # calibration of one core applied to all others -> select core
        self.ok_button = QPushButton('OK', self)
        self.ok_button.setFixedWidth(100)
        self.clear_button = QPushButton('Clear', self)
        self.clear_button.setFixedWidth(100)

        # initiate table of available parameters
        self.tabCorr = self.Tablula()

        # creating window layout
        w = QWidget()
        mlayout2 = QVBoxLayout(w)
        vbox_top, vbox_middle, vbox_bottom = QHBoxLayout(), QVBoxLayout(), QVBoxLayout()
        mlayout2.addLayout(vbox_top), mlayout2.addLayout(vbox_middle), mlayout2.addLayout(vbox_bottom)

        # add items to the layout grid
        MsgGp = QGroupBox()
        MsgGp.setFont(QFont('Helvetica Neue', 12))
        gridMsg = QGridLayout()
        vbox_top.addWidget(MsgGp)
        MsgGp.setLayout(gridMsg)

        # add GroupBox to layout and load buttons in GroupBox
        gridMsg.addWidget(self.tabCorr, 0, 0)

        # draw additional "line" to separate parameters from plots and to separate navigation from rest
        vline = QFrame()
        vline.setFrameShape(QFrame.HLine | QFrame.Raised)
        vline.setLineWidth(2)
        vbox_middle.addWidget(vline)

        # add items to the layout grid
        NavGp = QGroupBox()
        NavGp.setFont(QFont('Helvetica Neue', 12))
        gridNav = QGridLayout()
        vbox_bottom.addWidget(NavGp)
        NavGp.setLayout(gridNav)

        gridNav.addWidget(self.ok_button, 0, 1)
        gridNav.addWidget(self.clear_button, 0, 2)

        # add everything to the window layout
        self.setLayout(mlayout2)

    def Tablula(self):
        # get RowCount as maximum of available groups
        rows = np.max([len(self.lsCore1 or ''), len(self.lsCore2 or ''), len(self.lsCore3 or ''),
                       len(self.lsCore4 or '')])

        # create table
        tabula = QTableWidget(self)
        tabula.setColumnCount(4), tabula.setRowCount(rows)
        tabula.setHorizontalHeaderLabels(['O2', 'pH', 'total sulfide ΣS2- / H2S', 'EP'])

        # get the options for each parameter
        para1 = sorted([str(s) for s in self.lsCore1]) if isinstance(self.lsCore1, list) else ['--']
        para2 = sorted([str(s) for s in self.lsCore2]) if isinstance(self.lsCore2, list) else ['--']
        para3 = sorted([str(s) for s in self.lsCore3]) if isinstance(self.lsCore3, list) else ['--']
        para4 = sorted([str(s) for s in self.lsCore4]) if isinstance(self.lsCore4, list) else ['--']

        # change the para options and remove any group label information
        global grp_label
        para1 = dbs.removeGrpLabel(ls=para1, grp_label=grp_label, sep=' ')
        para2 = dbs.removeGrpLabel(ls=para2, grp_label=grp_label, sep=' ')
        para3 = dbs.removeGrpLabel(ls=para3, grp_label=grp_label, sep=' ')
        para4 = dbs.removeGrpLabel(ls=para4, grp_label=grp_label, sep=' ')

        # fill table items with combo boxes
        for index in range(rows):
            self.combo1, self.combo2, self.combo3, self.combo4 = QComboBox(), QComboBox(), QComboBox(), QComboBox()
            [self.combo1.addItem(t) for t in para1]
            tabula.setCellWidget(index, 0, self.combo1)

            [self.combo2.addItem(t) for t in para2]
            tabula.setCellWidget(index, 1, self.combo2)

            [self.combo3.addItem(t) for t in para3]
            tabula.setCellWidget(index, 2, self.combo3)

            [self.combo4.addItem(t) for t in para4]
            tabula.setCellWidget(index, 3, self.combo4)

        tabula.resizeRowsToContents(), tabula.adjustSize()
        return tabula

    def clear(self):
        # clear the table
        self.tabCorr.clearContents()

    def close(self):
        # fill the dataframe
        tab_corr = pd.DataFrame(columns=['O2', 'pH', 'H2S', 'EP'], index=range(self.tabCorr.rowCount()))
        for i in range(self.tabCorr.rowCount()):
            for en, j in enumerate(tab_corr.columns):
                choice = self.tabCorr.cellWidget(i, en).currentText()
                tab_corr.loc[i, j] = choice if choice == '--' else int(choice)
        # store dataframe in global variable
        global tabcorr
        tabcorr = tab_corr

        # close the window
        self.hide()


class AdjustjPWindow(QDialog):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setWindowTitle("Adjust individual profiles")
        self.setGeometry(650, 50, 600, 300) # x-position, y-position, width, height

        # add description about how to use this window (slider, outlier detection, cropping area)
        self.msg = QLabel("Use the tab to switch between analytes belonging to the selected group. \nYou can trim the "
                          "data range: press CONTROL/COMMAND + select min/max or you can adjust the general depth shown"
                          "in the plot. \nAt the end,  update the plot by pressing the button UPDATE")

        self.msg.setWordWrap(True)

        self.close_button = QPushButton('Fit OK', self)
        self.close_button.setFixedWidth(100)
        self.adjust_button = QPushButton('adjust data', self)
        self.adjust_button.setFixedWidth(100)


# -----------------------------------------------
class FinalPage(QWizardPage):
    def __init__(self, parent=None):
        super(FinalPage, self).__init__(parent)
        self.setTitle("Final page")
        self.setSubTitle("Thanks for visiting.\n\n"
                         "Tak for besøget.")


# -----------------------------------------------
class SalConvWindowO2(QDialog):
    def __init__(self, temp_edit_degC, salinity_edit):
        super().__init__()
        # get transferred parameter
        self.temp_degC = temp_edit_degC
        self.salinity = salinity_edit

        # initiate layout
        self.initUI()

        # connect button with function
        self.calc_button.clicked.connect(self.salinity_calculationO2)
        self.close_button.clicked.connect(self.close_window)
        self.reset_button.clicked.connect(self.reset_window)

    def initUI(self):
        self.setWindowTitle("Conversion conductivity to salinity")
        self.setGeometry(650, 180, 300, 200)

        # add description about how to use this window (slider, outlier detection, trim range)
        self.msg = QLabel("Required information:  pressure in bar and the conductivity in S/m")
        self.msg.setWordWrap(True), self.msg.setFont(QFont('Helvetica Neue'))

        # input
        cnd_label, cnd_unit_label = QLabel(self), QLabel(self)
        cnd_label.setText('Conductivity: '), cnd_unit_label.setText('S/m')
        self.cnd_edit = QLineEdit(self)
        self.cnd_edit.setValidator(QDoubleValidator()), self.cnd_edit.setAlignment(Qt.AlignRight)
        self.cnd_edit.setMaximumWidth(100), self.cnd_edit.setText('')

        atm_label, atm_unit_label = QLabel(self), QLabel(self)
        atm_label.setText('Actual pressure: '), atm_unit_label.setText('bar')
        self.atm_edit = QLineEdit(self)
        self.atm_edit.setValidator(QDoubleValidator()), self.atm_edit.setAlignment(Qt.AlignRight)
        self.atm_edit.setMaximumWidth(100), self.atm_edit.setText('')

        temp_label, temp_unit_label = QLabel(self), QLabel(self)
        temp_label.setText('Temperature: '), temp_unit_label.setText('degC')
        self.temp_edit = QLineEdit(self)
        self.temp_edit.setValidator(QDoubleValidator()), self.temp_edit.setAlignment(Qt.AlignRight)
        self.temp_edit.setMaximumWidth(100), self.temp_edit.setText(str(self.temp_degC.text()))

        sal_label, sal_unit_label = QLabel(self), QLabel(self)
        sal_label.setText('Salinity: '), sal_unit_label.setText('PSU')
        self.sal_edit = QLineEdit(self)
        self.sal_edit.setValidator(QDoubleValidator()), self.sal_edit.setAlignment(Qt.AlignRight)
        self.sal_edit.setMaximumWidth(100), self.sal_edit.setEnabled(False), self.sal_edit.setText('--')

        # close the window again
        self.calc_button = QPushButton('Calculate', self)
        self.calc_button.setFixedWidth(100)
        self.close_button = QPushButton('OK', self)
        self.close_button.setFixedWidth(100)
        self.reset_button = QPushButton('Reset', self)
        self.reset_button.setFixedWidth(100)

        # create grid and groups
        mlayout2 = QVBoxLayout()
        vbox2_top, vbox2_bottom, vbox2_middle = QHBoxLayout(), QHBoxLayout(), QVBoxLayout()
        mlayout2.addLayout(vbox2_top), mlayout2.addLayout(vbox2_middle), mlayout2.addLayout(vbox2_bottom)

        # add items to the layout grid
        # top part
        MsgGp = QGroupBox()
        MsgGp.setFont(QFont('Helvetica Neue', 12))
        # MsgGp.setMinimumWidth(300)
        gridMsg = QGridLayout()
        vbox2_top.addWidget(MsgGp)
        MsgGp.setLayout(gridMsg)

        # add GroupBox to layout and load buttons in GroupBox
        gridMsg.addWidget(self.msg, 1, 0)

        # in-between for input parameter
        plotGp = QGroupBox("User input")
        plotGp.setFont(QFont('Helvetica Neue', 12))
        # plotGp.setMinimumWidth(250), \
        plotGp.setMinimumHeight(200)
        grid_para = QGridLayout()
        vbox2_middle.addWidget(plotGp)
        plotGp.setLayout(grid_para)

        # add GroupBox to layout and load buttons in GroupBox
        grid_para.addWidget(temp_label, 1, 0)
        grid_para.addWidget(self.temp_edit, 1, 1)
        grid_para.addWidget(temp_unit_label, 1, 2)
        grid_para.addWidget(atm_label, 2, 0)
        grid_para.addWidget(self.atm_edit, 2, 1)
        grid_para.addWidget(atm_unit_label, 2, 2)
        grid_para.addWidget(cnd_label, 3, 0)
        grid_para.addWidget(self.cnd_edit, 3, 1)
        grid_para.addWidget(cnd_unit_label, 3, 2)

        grid_para.addWidget(sal_label, 5, 0)
        grid_para.addWidget(self.sal_edit, 5, 1)
        grid_para.addWidget(sal_unit_label, 5, 2)

        # bottom group for navigation panel
        naviGp = QGroupBox("Navigation panel")
        naviGp.setFont(QFont('Helvetica Neue', 12))
        # naviGp.setMinimumWidth(250), \
        naviGp.setFixedHeight(75)
        gridNavi = QGridLayout()
        vbox2_bottom.addWidget(naviGp)
        naviGp.setLayout(gridNavi)

        # add GroupBox to layout and load buttons in GroupBox
        gridNavi.addWidget(self.close_button, 1, 0)
        gridNavi.addWidget(self.calc_button, 1, 1)
        gridNavi.addWidget(self.reset_button, 1, 2)

        # add everything to the window layout
        self.setLayout(mlayout2)

    def salinity_calculationO2(self):
        # required parameter by user
        # atm = 1.01325   # atmospheric pressure in bar | convert bar in decibar: 1bar == 10 dbar
        # cnd = 1         # conductivity ratio (for salinity 35, temp_degC=15, atm -> cnd = 1)
        if len(self.atm_edit.text().strip()) == 0 or len(self.cnd_edit.text().strip()) == 0 or \
                len(self.temp_edit.text().strip()) == 0:
            pass
        else:
            salinity = sal.SalCon_Converter(temp_degC=float(self.temp_edit.text().strip()),  M=0,
                                            cnd=float(self.cnd_edit.text()), p_dbar=10/1*float(self.atm_edit.text()))
            self.sal_edit.setText(str(round(salinity, 3)))
            results['salinity PSU'] = salinity
            results['temperature degC'] = float(self.temp_edit.text().strip())

    def reset_window(self):
        # reset input parameter
        self.cnd_edit.setText(' ')
        self.atm_edit.setText(' ')
        self.temp_edit.setText(str(self.temp_degC))

        # reset salinity calculation
        self.sal_edit.setText('--')

    def close_window(self):
        self.hide()
        self.salinity.setText(str(round(results['salinity PSU'], 3)))
        self.temp_degC.setText(str(results['temperature degC']))


# --------------------------------------------------------------
def _loadGlobData(file_str):
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
    ls_dsheets = dict(map(lambda f: (f[0], dbs.loadMeas4GUI(file=f[1])), enumerate(ls_file)))

    dsheets = ls_dsheets[0]
    for en in range(len(ls_file)-1):
        dsheets = merge(dsheets, ls_dsheets[en+1])

    # get the information how the columns for depth, concentration, and signal are labeled for each analyte
    global dcol_label
    if bool(dcol_label) is False:
        for a in dsheets.keys():
            dcol_label[a] = list(dsheets[a].columns[2:])
    return dsheets, dignore


def _findCoreLabel(option1, option2, ls):
    if option1 in ls:
        labCore = option1
    elif option2 in ls:
        labCore = option2
    else:
        labCore = None
    return labCore


def intLab(c):
    if isinstance(c, str):
        cnew = int(c.split(' ')[1])
    else:
        cnew = c
    return cnew


def checkDatavsPara(sheet_select, par):
    checked = False
    try:
        if sheet_select is None:
            msgBox = QMessageBox()
            msgBox.setIcon(QMessageBox.Information)
            msgBox.setText(
                "No measurement data found for selected parameter {}.  Please,  provide the raw measurement "
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


def makePatchSpinesInVis(ax):
    ax.set_frame_on(True)
    ax.patch.set_visible(False)
    for sp in ax.spines.values():
        sp.set_visible(False)


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


# ---------------------------------------------------------------------------------------------------------------------
if __name__ == '__main__':
    import sys

    app = QtWidgets.QApplication(sys.argv)
    # !!!TODO: hard coded path must be included in system files
    path = os.path.join('/Users/au652733/Python/Project_julia/', 'Figure4icon.jpg')
    app.setWindowIcon(QIcon(path))
    app.setStyle('QtCurve') # options: 'Breeze', 'Oxygen', 'QtCurve', 'Windows', 'Fusion'

    Wizard = MagicWizard()
    # screen Size adjustment
    screen = app.primaryScreen()
    rect = screen.availableGeometry()
    Wizard.setMaximumHeight(int(rect.height() * 0.9))

    # show wizard
    Wizard.show()
    sys.exit(app.exec_())

#%
