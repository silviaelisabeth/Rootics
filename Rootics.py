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
from PyQt5.QtWidgets import (QCheckBox, QComboBox, QFileDialog, QFrame, QGridLayout, QGroupBox, QHBoxLayout, QLabel,
                             QLineEdit, QDialog, QMessageBox, QPushButton, QSlider, QVBoxLayout, QWidget, QWizard,
                             QWizardPage, QTabWidget, QTableWidget, QTableWidgetItem)
from PyQt5.QtCore import Qt, QRegExp
from PyQt5.QtGui import *
import numpy as np
import seaborn as sns
import pandas as pd
from lmfit import Model
import os
import re
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT, FigureCanvasQTAgg
from datetime import datetime

import functions_dbs as dbs
import function_salinity as sal
import functions_O2 as fO2
import functions_pH as fph
import functions_H2S as fh2s
import functions_EP as fep
import function_joints as fj

# global parameter
GUI_size = (200, 150)               # width and height of the graphical user interface
lim, lim_min, steps = 150, -1, 0.5
convC2K = 273.15                    # temperature conversion from degC into Kelvin
gof_accept = 10.                    # acceptable goodness of fit to result to reasonable depth profiles (SWI correction)
gof_top = 3.                        # excellent goodness of fit to result to reasonable depth profiles (SWI correction)
ls_allData = ['meta data', 'raw data', 'fit_mV', 'adjusted data', 'penetration depth']
grp_label = None                    # global definition of group label
dunit = dict()                      # which parameter has which unit at the end. Conversion from V to µmol/L or without?
dyrange = list()                    # joint plot - save information about depth range

# color list for samples: grey, orange, petrol, green, yellow, light grey, blue
ls_col = list(['#4c5558', '#eb9032', '#21a0a8', '#9ec759', '#f9d220', '#96a6ab', '#1B08AA', '#3D14E1', '#D20D41',
               '#E87392', '#40A64A'])
dcolor = dict({'O2': '#4c5558', 'pH': '#eb9032', 'H2S': '#9ec759', 'EP': '#1B08AA'})
ls_figtype = ['png', 'tiff']
dpi = 300
font, font_button, fs_font, fs_ = 'Arimo', 'Helvetica Neue', 10, 8

# plot style / layout
sns.set_context('paper'), sns.set_style('ticks')

# global variables for individual projects
dcol_label, results, dout, dav = dict(), dict(), dict(), dict()

# O2 project
core_select, userCal, ret = None, None, None
dobj_hid, dO2_core, dpen_glob = dict(), dict(), dict()

# pH project
scalepH = dict()

# H2S project
dobj_hidH2S, scaleh2s, tabcorr = dict(), dict(), None
# sulfidic front defined as percentage above the base value (in the water column)
sFront = 10

# EP project
dobj_hidEP, scaleEP = dict(), dict()

# wizard architecture - how are the pages arranged and parameters listed?
wizard_page_index = {"IntroPage": 0, "o2Page": 1, "phPage": 2, "h2sPage": 3, "epPage": 4, "charPage": 5, "averageLP": 6,
                     "joint plots": 7, "final page": 8}
ls_para_global = ['O2', 'pH', 'H2S', 'EP']


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

        # add a background image
        path = os.path.join('/Users/au652733/Python/Project_CEMwizard/ready2buildApp/', 'logo_v1.png')
        pixmap = QtGui.QPixmap(path)
        pixmap = pixmap.scaled(400, 400, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
        self.setPixmap(QWizard.BackgroundPixmap, pixmap)


class IntroPage(QWizardPage):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle("InfoPage")
        self.setSubTitle("Enter the path to your measurement file(s) and select which of the parameters should be "
                         "analyzed.\nWe will then guide you through the analysis.\n\n")
        # create layout
        self.initUI()

        # connect checkbox and load file button with a function
        self.load_button.clicked.connect(self.load_data)
        self.save_button.clicked.connect(self.save_path)
        self.set_button.clicked.connect(self.save_settings)
        self.h2s_box.stateChanged.connect(self.total_sulfide)
        self.ph_box.stateChanged.connect(self.pH_check)
        self.o2_box.clicked.connect(self.parameter_selection)
        self.ph_box.clicked.connect(self.parameter_selection)
        self.h2s_box.clicked.connect(self.parameter_selection)
        self.ep_box.clicked.connect(self.parameter_selection)
        self.combo_box.stateChanged.connect(self.combo_plot_selection)

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
        self.o2_box = QCheckBox('oxygen O2', self)
        self.ph_box = QCheckBox('pH', self)
        self.h2s_box = QCheckBox('total sulfide ΣS2- / H2S', self)
        self.ep_box = QCheckBox('EP', self)
        self.combo_box = QCheckBox('joint plots', self)
        self.o2_box.setFont(QFont(font_button, fs_font)), self.ph_box.setFont(QFont(font_button, fs_font)),
        self.h2s_box.setFont(QFont(font_button, fs_font)), self.ep_box.setFont(QFont(font_button, fs_font))
        self.combo_box.setFont(QFont(font_button, fs_font))

        # path for measurement file (csv)
        self.load_button = QPushButton('Load meas. file', self)
        self.load_button.setFixedWidth(150), self.load_button.setFont(QFont(font_button, fs_font))
        self.inputFileLineEdit = QLineEdit(self)
        self.inputFileLineEdit.setValidator(QtGui.QDoubleValidator())
        self.inputFileLineEdit.setMinimumWidth(300), self.inputFileLineEdit.setMinimumHeight(10)
        self.inputFileLineEdit.setAlignment(Qt.AlignRight)
        self.inputFileLineEdit.setFont(QFont(font_button, fs_font))

        # directory to store files
        self.save_button = QPushButton('Storage path', self)
        self.save_button.setFixedWidth(150), self.save_button.setFont(QFont(font_button, fs_font))
        self.inputSaveLineEdit = QLineEdit(self)
        self.inputSaveLineEdit.setValidator(QtGui.QDoubleValidator())
        self.inputSaveLineEdit.setMinimumWidth(300), self.inputSaveLineEdit.setMinimumHeight(10)
        self.inputSaveLineEdit.setAlignment(Qt.AlignRight)
        self.inputSaveLineEdit.setFont(QFont(font_button, fs_font))

        # saving options
        self.set_button = QPushButton('Settings', self)
        self.set_button.setFixedWidth(150), self.set_button.setFont(QFont(font_button, fs_font))

        # pre-define list of save options
        self.ls_saveOp = QLineEdit()
        self.ls_saveOp.setText(','.join(['meta data', 'raw data', 'fit_mV', 'adjusted data', 'penetration depth']))

        # creating main window (GUI)
        w = QWidget()
        # create layout grid
        mlayout = QVBoxLayout(w)
        vbox_top, vbox_middle, vbox_bottom = QVBoxLayout(), QVBoxLayout(), QVBoxLayout()
        mlayout.addLayout(vbox_top), mlayout.addLayout(vbox_middle), mlayout.addLayout(vbox_bottom)

        meas_settings = QGroupBox("Parameter selection for analysis")
        grid_load = QGridLayout()
        meas_settings.setMinimumHeight(200), meas_settings.setMinimumWidth(650)
        meas_settings.setFont(QFont(font_button, fs_font))
        vbox_top.addWidget(meas_settings)
        meas_settings.setLayout(grid_load)

        # include widgets in the layout
        grid_load.addWidget(self.o2_box, 0, 0)
        grid_load.addWidget(self.ph_box, 1, 0)
        grid_load.addWidget(self.h2s_box, 2, 0)
        grid_load.addWidget(self.ep_box, 3, 0)
        grid_load.addWidget(self.combo_box, 4, 0)

        meas_file = QGroupBox("Define directories")
        grid_file = QGridLayout()
        meas_file.setMinimumHeight(150), meas_file.setMinimumWidth(650)
        meas_file.setFont(QFont(font_button, fs_font))
        vbox_middle.addWidget(meas_file)
        meas_file.setLayout(grid_file)

        # include widgets in the layout
        grid_file.addWidget(self.load_button, 0, 0)
        grid_file.addWidget(self.inputFileLineEdit, 0, 1)
        grid_file.addWidget(self.save_button, 1, 0)
        grid_file.addWidget(self.inputSaveLineEdit, 1, 1)
        grid_file.addWidget(self.set_button, 2, 0)
        vbox_middle.addStretch()

        self.setLayout(mlayout)

    def load_data(self):
        # load all files at a time that shall be analyzed together
        fname, filter = QFileDialog.getOpenFileNames(parent=self, filter='Excel File (*.xlsx *.xls)',
                                                     caption='Select specific excel files for measurement analysis',
                                                     directory=os.getcwd(), initialFilter='Excel File (*.xlsx, *.xls)')
        self.fname.setText(str(fname))
        if fname:
            self.inputFileLineEdit.setText(str(fname))
            self.fname.setText(str(fname))

    def save_path(self):
        fsave = QtWidgets.QFileDialog.getExistingDirectory(parent=self, directory=os.getcwd(), caption='Select Folder')
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
        if self.h2s_box.isChecked() is True and self.ph_box.isChecked() is False and self.combo_box.isChecked() is False:
            msgBox = QMessageBox()
            msgBox.setIcon(QMessageBox.Information)
            msgBox.setText("Total sulfide ΣS2- can only be calculated, when the pH is provided as well. Otherwise you"
                           " will only get the H2S concentration.")
            msgBox.setFont(QFont(font_button, fs_font))
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

    def combo_plot_selection(self):
        if self.combo_box.isChecked() is True:
            self.o2_box.setChecked(False), self.ph_box.setChecked(False), self.h2s_box.setChecked(False)
            self.ep_box.setChecked(False)
            self.ls_para.setText('combo')

    def parameter_selection(self):
        global dunit
        dunit, ls_para = dict(), list()
        ls_para_checked = [self.o2_box.isChecked(), self.ph_box.isChecked(), self.h2s_box.isChecked(),
                           self.ep_box.isChecked()]

        if self.combo_box.isChecked() is True and any(ls_para_checked) is True:
            self.combo_box.setChecked(False)
        if self.o2_box.isChecked() is True:
            self.pHfromo2.setText('True')
            ls_para.append('o2')
        if self.h2s_box.isChecked() is True:
            ls_para.append('h2s')
        if self.ph_box.isChecked() is True:
            ls_para.append('ph')
        if self.ep_box.isChecked() is True:
            ls_para.append('ep')
        self.ls_para.setText(','.join(ls_para))

    def nextId(self) -> int:
        ls_para = list(self.field('parameter selected').split(','))
        if self.field('parameter selected'):
            if 'o2' in self.field('parameter selected'):
                return wizard_page_index["o2Page"]
            elif 'ph' in self.field('parameter selected'):
                return wizard_page_index["phPage"]
            elif 'h2s' in self.field('parameter selected'):
                return wizard_page_index["h2sPage"]
            elif 'ep' in self.field('parameter selected'):
                return wizard_page_index["epPage"]
            elif 'combo' in self.field('parameter selected'):
                return wizard_page_index["joint plots"]
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
        self.close_button.setFixedWidth(100), self.close_button.setFont(QFont(font_button, fs_font))

        # checkboxes for possible data tables and figures to save
        self.meta_box = QCheckBox('Meta data', self)
        self.meta_box.setChecked(True), self.meta_box.setFont(QFont(font, 10))
        self.rdata_box = QCheckBox('Raw data', self)
        self.rdata_box.setChecked(True), self.rdata_box.setFont(QFont(font, 10))
        self.fit_box = QCheckBox('Fit data', self)
        self.fit_box.setChecked(True), self.fit_box.setFont(QFont(font, 10))
        self.adj_box = QCheckBox('Adjusted data', self)
        self.adj_box.setChecked(True), self.adj_box.setFont(QFont(font, 10))
        self.pen_box = QCheckBox('Penetration depth', self)
        self.pen_box.setChecked(True), self.pen_box.setFont(QFont(font, 10))

        self.swiRaw_box = QCheckBox('Raw profile', self)
        self.swiRaw_box.setChecked(False), self.swiRaw_box.setFont(QFont(font, 10))
        self.swiF_box = QCheckBox('Adjusted profile', self)
        self.swiF_box.setChecked(False), self.swiF_box.setFont(QFont(font, 10))
        self.fitF_box = QCheckBox('Fit plot', self)
        self.fitF_box.setChecked(False), self.fitF_box.setFont(QFont(font, 10))
        self.penF_box = QCheckBox('Penetration depth', self)
        self.penF_box.setChecked(False), self.penF_box.setFont(QFont(font, 10))

        # creating window layout
        mlayout2 = QVBoxLayout()
        vbox2_top, vbox2_middle, vbox2_bottom = QHBoxLayout(), QHBoxLayout(), QHBoxLayout()
        mlayout2.addLayout(vbox2_top), mlayout2.addLayout(vbox2_middle), mlayout2.addLayout(vbox2_bottom)

        data_settings = QGroupBox("Data tables")
        grid_data = QGridLayout()
        data_settings.setFont(QFont(font_button, fs_font))
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
        fig_settings.setFont(QFont(font_button, fs_font))
        vbox2_middle.addWidget(fig_settings)
        fig_settings.setLayout(grid_fig)

        # include widgets in the layout
        grid_fig.addWidget(self.swiRaw_box, 0, 0)
        grid_fig.addWidget(self.swiF_box, 1, 0)
        grid_fig.addWidget(self.fitF_box, 2, 0)
        grid_fig.addWidget(self.penF_box, 4, 0)

        ok_settings = QGroupBox("")
        grid_ok = QGridLayout()
        ok_settings.setFont(QFont(font_button, fs_font))
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
            ls_setSave.append('fit_mV'), ls_setSave.append('derivative_mV')
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


# ---------------------------------------------------------------------------------------------------------------------
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
        self.dfig_out, self.dcore_pen = dict(), dict()

        # connect checkbox and load file button with a function
        self.dtab_sal, self.count = None, 0
        self.salcon_button.clicked.connect(self.conductivity_converterO2)
        self.slider.valueChanged.connect(self.label_core_select)
        self.continue_button.clicked.connect(self.continue_process)
        self.save_button.clicked.connect(self.save)
        self.reset_button.clicked.connect(self.reset_o2page)

    def initUI(self):
        # define validator
        validator = QDoubleValidator(-9990, 9990, 4)
        validator.setLocale(QtCore.QLocale("en_US"))
        validator.setNotation(QDoubleValidator.StandardNotation)
        validator_pos = QDoubleValidator(0., 9990, 4)
        validator_pos.setLocale(QtCore.QLocale("en_US"))
        validator_pos.setNotation(QDoubleValidator.StandardNotation)

        # plot window, side panel for user input, and continue button
        temperature_label, temperature_unit_label = QLabel(self), QLabel(self)
        temperature_label.setText('Temperature'), temperature_unit_label.setText('degC')
        self.temperature_edit = QLineEdit(self)
        self.temperature_edit.setValidator(validator), self.temperature_edit.setAlignment(Qt.AlignRight)
        self.temperature_edit.setText(str(results['temperature degC']))

        salinity_label, salinity_unit_label = QLabel(self), QLabel(self)
        salinity_label.setText('Salinity'), salinity_unit_label.setText('PSU')
        self.salinity_edit = QLineEdit(self)
        self.salinity_edit.setValidator(validator_pos), self.salinity_edit.setAlignment(Qt.AlignRight)
        self.salinity_edit.setText(str(results['salinity PSU']))

        pene2_label, pene2_unit_label = QLabel(self), QLabel(self)
        pene2_label.setText('Sensor LoD'), pene2_unit_label.setText('µmol/L')
        self.pene2_edit = QLineEdit(self)
        self.pene2_edit.setValidator(validator_pos), self.pene2_edit.setAlignment(Qt.AlignRight)
        self.pene2_edit.setText('0.5'), self.pene2_edit.editingFinished.connect(self.updatePene)

        # storage for comparison
        self.salcon_button = QPushButton('Converter', self)
        self.salcon_button.setFixedWidth(100), self.salcon_button.setFont(QFont(font_button, fs_font))
        self.O2_penetration = float(self.pene2_edit.text())
        self.continue_button = QPushButton('Continue', self)
        self.continue_button.setFixedWidth(100), self.continue_button.setFont(QFont(font_button, fs_font))
        self.save_button = QPushButton('Save', self)
        self.save_button.setFixedWidth(100), self.save_button.setFont(QFont(font_button, fs_font))
        self.reset_button = QPushButton('Reset', self)
        self.reset_button.setFixedWidth(100), self.reset_button.setFont(QFont(font_button, fs_font))
        self.checkFit_button = QPushButton('Check fit', self)
        self.checkFit_button.setFixedWidth(100), self.checkFit_button.setFont(QFont(font_button, fs_font))
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
        para_settings.setFont(QFont(font_button, fs_font)), para_settings.setFixedHeight(150)
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
        self.figO2, self.axO2 = plt.subplots()
        self.canvasO2 = FigureCanvasQTAgg(self.figO2)
        self.axO2.set_xlabel('O2 / mV'), self.axO2.set_ylabel('Depth / µm')
        self.axO2.invert_yaxis()
        self.figO2.subplots_adjust(bottom=0.2, right=0.95, top=0.9, left=0.15)
        sns.despine()

        O2_group = QGroupBox("O2 depth profile")
        O2_group.setMinimumHeight(400)
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
        self.o2_dis = fO2.dissolvedO2_calc(T=float(self.temperature_edit.text()), sal=float(self.salinity_edit.text()))

    def User4Calibration(self):
        global userCal, dunit, results, steps
        dunit['O2'] = 'µmol/L'

        if userCal:
            pass
        else:
            userCal = QMessageBox.question(self, 'Calibration',
                                           'Shall we use the calibration from the measurement file? \nIf not,  the '
                                           'sensor will be recalibrated based on the given temperature & salinity.',
                                           QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)

        if userCal == QMessageBox.Yes:
            # define for output metadata
            self.typeCalib = 'internal calibration from measurement file'

            # calibration from excel file
            dO2_core.update(fO2.O2rearrange(df=self.ddata_shift, unit='µmol/L'))
            results['O2 profile'] = dO2_core

            # update fit and derivative accordingly
            results = fO2.updateBaseline_O2Fit(results=results, dunit=dunit, steps=steps, gmod=self.gmod)

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
                msgBox1.setFont(QFont(font_button, fs_font))
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
                dO2_core.update(fO2.O2converter4conc(data_shift=self.ddata_shift, o2_dis=self.o2_dis, lim_min=lim_min,
                                                     lim=lim, unit='µmol/L'))
                for c in dO2_core.keys():
                    for i in dO2_core[c].columns:
                        # get the right columns:
                        col2sub = [k for k in results['O2 profile'][c][i[0]].columns if 'M' in k or 'mol' in k][0]
                        results['O2 profile'][c][i[0]][col2sub] = dO2_core[c][i].dropna().to_numpy()

                # update fit and derivative accordingly
                results = fO2.updateBaseline_O2Fit(results=results, dunit=dunit, steps=steps, gmod=self.gmod)

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

    def continue_process(self):
        global dunit, dcol_label, grp_label, steps, results
        # store relevant information
        results['temperature degC'] = float(self.temperature_edit.text())
        results['salinity PSU'] = float(self.salinity_edit.text())

        # set the initial unit for O2 as mV
        dunit['O2'] = 'mV'

        if self.count == 0:
            # determine min/max dissolved O2 according to set temperature and salinity
            self.pre_check_calibration()

            # update subtitle for progress report
            self.setSubTitle("The analysis starts with the correction of the surface-water interface (SWI).  If the "
                             "correction looks good,  press CONTINUE.  Otherwise,  press CHECK FIT for adjustments. \n")
            # load data from excel sheet depending on the type (measurement file or prepared file)
            ddata, sheet_select, checked, grp_label = fO2.load_O2data(data=self.field("Data"), grp_label=grp_label,
                                                                      dcol_label=dcol_label)

            if checked is True:
                # determine best sigmoidal fit for given dataset
                [self.ls_core, self.ls_colname, self.gmod, self.dic_dcore, self.dic_deriv,
                 self.dfit, results] = fO2.sigmoidalFit(ddata=ddata, sheet_select=sheet_select, dunit=dunit,
                                                        results=results, steps=steps)

                # update group label
                self.sld_label.setText('{}: {}'.format(self.ls_colname[0], min(self.ls_core)))

                # apply baseline shift and plot updated data
                self.baselineShift()

                # enable button to click and investigate the derivative / fit
                self.checkFit_button.setEnabled(True)
                self.checkFit_button.clicked.connect(self.checkFitWindow)

                # enable next step in O2 analysis
                self.count += 1
            else:
                # reset page as nothing was found
                self.reset_o2page()

        elif self.count == 1:
            # update subtitle for progress report
            self.setSubTitle("Depth correction (SWI) done.  Now,  continue with calibration. \n \n")

            # get user input on calibration - convert O2 potential into concentration
            self.User4Calibration()

    def baselineShift(self):
        # baseline shift of all samples (of all cores)
        self.ddata_shift = fO2.baseline_shift(dic_dcore=results['O2 profile'], dfit=self.dfit)
        results['O2 SWI corrected'], results['O2 profile'] = self.ddata_shift, self.ddata_shift

        # plot baseline corrected depth profiles
        global dunit
        _ = fO2.GUI_baslineShift(data_shift=self.ddata_shift, core=min(self.ls_core), ls_core=self.ls_core, fs=10,
                                 fig=self.figO2, ax=self.axO2, plot_col=dunit['O2'], grp_label=self.ls_colname[0])

        # slider initialized to first core
        self.slider.setMinimum(int(min(self.ls_core))), self.slider.setMaximum(int(max(self.ls_core)))
        self.slider.setValue(int(min(self.ls_core)))
        self.sld_label.setText('{}: {}'.format(self.ls_colname[0], int(min(self.ls_core))))

        # when slider value change (on click), return new value and update figure plot
        self.slider.valueChanged.connect(self.slider_update)

        # in case the fit window is open -> update figFit according to selected sliderValue
        self.slider.sliderReleased.connect(self.wFit_update)
        self.figO2.canvas.draw()

    def continue_processI(self):
        global results, dunit, steps
        # possible responses include either "core" or only the number -> find pattern with re
        dO2_core.update(fO2.O2calc4conc_one4all(core_sel=int(core_select), lim_min=lim_min, lim=lim, unit='µmol/L',
                                                o2_dis=self.o2_dis, data_shift=self.ddata_shift))
        results['O2 profile'] = dO2_core

        # update fit and derivative accordingly
        results = fO2.updateBaseline_O2Fit(results=results, dunit=dunit, steps=steps, gmod=self.gmod)

        # define for output metadata
        self.typeCalib = 'recalibration one core ' + str(core_select) + ' to all'

        # continue with the process - first execute without any click
        self.continue_processII()
        self.continue_button.disconnect()
        self.continue_button.clicked.connect(self.continue_processII)

    def continue_processII(self):
        global dpen_glob, grp_label, dobj_hid
        if self.count == 1:
            # determine penetration depth according to given O2 concentration
            self.O2_penetration = float(self.pene2_edit.text())
            self.dcore_pen, _ = fO2.GUI_calcO2penetration(dO2_core=results['O2 profile'], unit='µmol/L', steps=steps,
                                                          gmod=self.gmod, O2_pen=float(self.pene2_edit.text()),
                                                          dpen_glob=dpen_glob)
            results['O2 penetration depth'] = self.dcore_pen

            # update subtitle for progress report
            self.setSubTitle("For each core,  select all samples to be considered for calculation of the average "
                             "penetration depth. Then press CONTINUE.\n")

            # slider initialized to first core
            self.slider.setValue(int(min(self.ls_core)))
            self.sld_label.setText('{}: {}'.format(self.ls_colname[0], int(min(self.ls_core))))

            # initialize first plot with first core
            _, dobj_hid = fO2.GUI_O2depth(core=int(min(self.ls_core)), ls_core=self.ls_core, dcore_pen=self.dcore_pen,
                                          fs_=fs_, dobj_hid=dobj_hid, dO2_core=results['O2 profile'], ax=self.axO2,
                                          fig=self.figO2, grp_label=grp_label)
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
        global dpen_glob
        # double check, whether definition of penetration depth has changed
        if self.O2_penetration != float(self.pene2_edit.text()):
            [self.dcore_pen,
             _] = fO2.GUI_calcO2penetration(dO2_core=results['O2 profile'], unit='µmol/L', steps=steps, gmod=self.gmod,
                                            O2_pen=float(self.pene2_edit.text()), dpen_glob=dpen_glob)

        # slider initialized to first core
        self.slider.setValue(int(min(self.ls_core)))
        self.sld_label.setText('{}: {}'.format(self.ls_colname[0], int(min(self.ls_core))))

        # initialize first plot with first core
        fig2, mean_ = GUI_penetration_av(core=int(min(self.ls_core)), ls_core=self.ls_core, dcore_pen=self.dcore_pen,
                                         fig=self.figO2, ax=self.axO2)

        if np.nan in mean_:
            self.setSubTitle("WARNING! It was not possible to determine the average penetration depth. Maybe, try "
                             "a higher O2 concentration.")

        # when slider value change (on click), return new value and update figure plot
        self.slider.valueChanged.disconnect(self.slider_update1)
        self.slider.valueChanged.connect(self.slider_update2)
        self.figO2.canvas.draw()

    def updatePene(self):
        if self.count == 0:  # only in the last step, count is set to 0
            self._CalcPenetration()

    def wFit_update(self):
        if self.ls_core:
            # allow only discrete values according to existing cores
            core_select = min(self.ls_core, key=lambda x: abs(x - self.slider.value()))

            # if fit window is visible --> update figFit according to selected core
            global wFit
            try:
                wFit.isVisible()
                wFit = FitWindow(core_select, self.count, self.ls_core, results['O2 profile'], results['O2 fit'],
                                 results['O2 derivative'], self.ddata_shift[self.ls_colname[-1]], self.figO2, self.axO2,
                                 self.field("Storage path"))
            except:
                pass

    def slider_update(self):
        if self.ls_core:
            global core_select
            # allow only discrete values according to existing cores
            core_select = min(self.ls_core, key=lambda x: abs(x - self.slider.value()))

            # update slider position and label
            self.slider.setValue(int(core_select))
            self.sld_label.setText('{}: {}'.format(self.ls_colname[0], core_select))

            # update plot according to selected core
            global dunit
            _ = fO2.GUI_baslineShift(data_shift=self.ddata_shift, core=core_select, ls_core=self.ls_core,
                                     fig=self.figO2, ax=self.axO2, plot_col=dunit['O2'], grp_label=grp_label)
            self.figO2.canvas.draw()

    def slider_update1(self):
        # pre-check whether count status is >= 1:
        if self.count == 0:
            return
        else:
            # update global parameter before usage
            global dobj_hid, grp_label

            # allow only discrete values according to existing cores
            core_select = min(self.ls_core, key=lambda x: abs(x - self.slider.value()))

            # update slider position and label
            self.slider.setValue(int(core_select))
            self.sld_label.setText('{}: {}'.format(self.ls_colname[0], core_select))

            # update plot according to selected core
            _, dobj_hid = fO2.GUI_O2depth(core=core_select, ls_core=self.ls_core, dcore_pen=self.dcore_pen, fs_=fs_,
                                          dobj_hid=dobj_hid, dO2_core=results['O2 profile'], grp_label=grp_label,
                                          ax=self.axO2, fig=self.figO2)
            self.figO2.canvas.draw()

    def slider_update2(self):
        # allow only discrete values according to existing cores
        core_select = min(self.ls_core, key=lambda x: abs(x - self.slider.value()))

        # update slider position and label
        self.slider.setValue(int(core_select))
        self.sld_label.setText('{}: {}'.format(self.ls_colname[0], core_select))

        # update plot according to selected core
        _, _ = GUI_penetration_av(core=core_select, ls_core=self.ls_core, dcore_pen=self.dcore_pen, fig=self.figO2,
                                  ax=self.axO2)
        self.figO2.canvas.draw()

    def checkFitWindow(self):
        global wFit
        wFit = FitWindow(self.slider.value(), self.count, self.ls_core, results['O2 profile'], results['O2 fit'],
                         results['O2 derivative'], self.ddata_shift, self.figO2, self.axO2, self.field("Storage path"))
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

    def save(self):
        global dout, dpen_glob, results, dobj_hid, grp_label, dunit
        # preparation - make own function out at the end
        dout = dbs.prep4saveRes(dout=dout, results=results, typeCalib=self.typeCalib, o2_dis=self.o2_dis,
                                temperature=float(self.temperature_edit.text()), pene2=float(self.pene2_edit.text()),
                                salinity=float(self.salinity_edit.text()), dpenStat=dpen_glob)

        # extract saving options for data / figures - according to user input
        self.save_data(analyte='O2')
        fO2.save_figure(save_params=self.field('saving parameters'), path_save=self.field("Storage path"), analyte='O2',
                        results=results, ls_core=self.ls_core, dic_deriv=self.dic_deriv, ddata_shift=self.ddata_shift,
                        dcore_pen=self.dcore_pen, dO2_core=results['O2 profile'], dobj_hid=dobj_hid, dunit=dunit,
                        grp_label=grp_label, dpen_glob=dpen_glob)

        # Information that saving was successful
        msgBox = QMessageBox()
        msgBox.setIcon(QMessageBox.Information)
        msgBox.setText("Selected data are saved successfully.")
        msgBox.setFont(QFont(font_button, fs_font))
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
            self.pene2_edit.setText('0.5')
            self.O2_penetration = float(self.pene2_edit.text())
            self.o2_dis, self.dtab_sal = None, None
            self.ls_core, self.data_shift = None, dict()
            dobj_hid.clear()
            dpen_glob.clear()
            dO2_core.clear()

            # clear figure
            self.axO2.cla()
            self.axO2.title.set_text('')
            self.axO2.set_xlabel('dissolved O2 / mV'), self.axO2.set_ylabel('Depth / µm')
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
    def __init__(self, sliderValue, cstatus, ls_core, dfCore, dfFit, dfDeriv, data_shift, figO2, axO2, storage_path):
        super().__init__()
        self.initUI()

        if cstatus > 2:
            self.update_button.setEnabled(False)
            self.adjust_button.setEnabled(False)

        # return current core - and get the samples to plot (via slider selection)
        self.Core = min(ls_core, key=lambda x: abs(x - sliderValue))

        # get the transmitted data
        self.dShift, self.figO2, self.axO2, self.storage_path = data_shift, figO2, axO2, storage_path
        self.dfCore, self.FitCore, self.DerivCore = dfCore[self.Core], dfFit[self.Core], dfDeriv[self.Core]

        # generate an independent dictionary of cores in case of updateFit is used
        self.dfCoreFit = dict()
        if isinstance(self.dfCore, dict):
            for c in self.dfCore.keys():
                df_c = pd.DataFrame(np.array(self.dfCore[c]), index=self.dfCore[c].index, columns=self.dfCore[c].columns)
                self.dfCoreFit[c] = df_c
        else:
            # dataframe with multi columns
            for c in self.dfCore.columns:
                df_c = pd.DataFrame(np.array(self.dfCore[c[0]]), index=self.dfCore.index, columns=[c[1]])
                self.dfCoreFit[c[0]] = df_c

        self.dShiftFit = dict()
        for c in self.dShift.keys():
            dicS = dict()
            for s in self.dShift[c].keys():
                df_s = pd.DataFrame(np.array(self.dShift[c][s]), index=self.dShift[c][s].index,
                                    columns=self.dShift[c][s].columns)
                dicS[s] = df_s
            self.dShiftFit[c] = dicS

        # plot all samples from current core
        global dunit, grp_label
        _ = fO2.plot_Fitselect(core=self.Core, sample=min(self.FitCore.keys()), dfCore=self.dfCore, dfFit=self.FitCore,
                               dfDeriv=self.DerivCore, fig=self.figFit, ax=self.axFit, ax1=self.ax1Fit, dunit=dunit,
                               grp_label=grp_label)
        # connect onclick event with function
        self.ls_out, self.ls_cropx = list(), list()
        self.figFit.canvas.mpl_connect('button_press_event', self.onclick_updateFit)

        # update slider range to number of samples and set to first sample
        self.slider1.setMinimum(int(min(self.FitCore.keys()))), self.slider1.setMaximum(int(max(self.FitCore.keys())))
        self.slider1.setValue(int(min(self.FitCore.keys())))
        self.sld1_label.setText('sample: ' + str(int(min(self.FitCore.keys()))))
        chi2 = self.FitCore[int(min(self.FitCore.keys()))][0].redchi
        self.chi2.setText('Goodness of fit (reduced χ2): ' + str(round(chi2, 2)))

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
                          " the fit by pressing either the button UPDATE FIT (temporal) or ADJUST DATA (permanently)")
        self.msg.setWordWrap(True)

        self.close_button = QPushButton('Fit OK', self)
        self.close_button.setFont(QFont(font_button, fs_font)), self.close_button.setFixedWidth(100)
        self.update_button = QPushButton('update fit', self)
        self.update_button.setFont(QFont(font_button, fs_font)), self.update_button.setFixedWidth(100)
        self.adjust_button = QPushButton('adjust data', self)
        self.adjust_button.setFont(QFont(font_button, fs_font)), self.adjust_button.setFixedWidth(100)
        self.save1_button = QPushButton('Save', self)
        self.save1_button.setFont(QFont(font_button, fs_font)), self.save1_button.setFixedWidth(100)

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
        self.figFit, self.axFit = plt.subplots(figsize=(5, 3), linewidth=0)
        self.ax1Fit = self.axFit.twinx()
        self.figFit.set_facecolor("none")
        self.canvasFit = FigureCanvasQTAgg(self.figFit)
        self.naviFit = NavigationToolbar2QT(self.canvasFit, self, coordinates=False)
        self.axFit.set_xlabel('Depth / µm'), self.axFit.set_ylabel('dissolved O2 / mV')
        self.ax1Fit.set_ylabel('1st derivative', color='#0077b6')

        self.axFit.invert_yaxis()
        self.figFit.subplots_adjust(bottom=0.2, right=0.95, top=0.9, left=0.15)
        sns.despine()

        # add items to the layout grid
        # top part
        MsgGp = QGroupBox()
        MsgGp.setFont(QFont(font_button, fs_font))
        gridMsg = QGridLayout()
        vbox2_top.addWidget(MsgGp)
        MsgGp.setLayout(gridMsg)

        # add GroupBox to layout and load buttons in GroupBox
        gridMsg.addWidget(self.msg, 1, 0)

        # in-between for chi-2
        ChiGp = QGroupBox()
        ChiGp.setFont(QFont(font_button, fs_font))
        ChiGp.setFixedHeight(60)
        gridChi = QGridLayout()
        vbox2_middle.addWidget(ChiGp)
        ChiGp.setLayout(gridChi)

        # add GroupBox to layout and load buttons in GroupBox
        gridChi.addWidget(self.chi2_bx, 1, 0)
        gridChi.addWidget(self.chi2, 1, 1)

        # middle part
        FitGp = QGroupBox("Sigmoidal fit and 1st derivative")
        FitGp.setFont(QFont(font_button, fs_font))
        FitGp.setMinimumWidth(350), FitGp.setMinimumHeight(500)
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
        BtnGp.setFixedHeight(75)
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
        global dunit
        gmod = Model(fO2._gompertz_curve_adv)
        res, df_fit_crop, df_fitder = fO2.baseline_finder_DF(dic_dcore=dcore_crop, dunit_O2=dunit['O2'], steps=steps,
                                                             model=gmod, adv=True)

        # update red.chi2
        self.chi2.setText('Goodness of fit (reduced χ2): ' + str(round(res.redchi, 3)))
        return df_fit_crop, df_fitder

    def adjustData(self):
        global dunit, grp_label
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
        _ = fO2.plot_FitUpdate(core=self.Core, nr=s, dic_dcore=dcore_crop, dfit=df_fit_crop, dic_deriv=df_fitder,
                               ax1=self.ax1Fit, ax=self.axFit, fig=self.figFit, grp_label=grp_label, dunit=dunit)
        self.figFit.canvas.draw()

        # exchange the updated depth profile to the dictionary (to plot all)
        self.dShift[c][s] = pd.DataFrame(np.array(dcore_crop), index=dcore_crop.index - df_fitder.idxmin().values[0],
                                         columns=dcore_crop.columns)
        # plot baseline corrected depth profiles for special sample
        _ = fO2.GUI_baslineShiftCore(data_shift=self.dShift[c], core_select=self.Core, plot_col=dunit['O2'],
                                     fig=self.figO2, ax=self.axO2, grp_label=grp_label)
        self.figO2.canvas.draw()

    def updateFit(self):
        global dunit, grp_label
        # only uses data for calculating the swi (applying trim, mark outliers, etc.) but does not trim or remove
        # data from the original profile (NO OVERWRITING) while adjust data actually adjusts data in the profile

        # current core, current sample
        c, s = self.Core, int(self.sld1_label.text().split(' ')[-1])

        # crop dataframe to selected range
        dcore_crop = self.cropDF(s=s, df=self.dfCore)
        self.ls_cropx = list()

        # pop outliers from depth profile
        if self.ls_out:
            dcore_crop = self.popOutlier(dcore_crop=dcore_crop)
            self.ls_out = list()

        # re-do fitting - curve fit and baseline finder
        df_fit_crop, df_fitder = self.reFit(dcore_crop=dcore_crop)

        # re-draw fit plot
        _ = fO2.plot_FitUpdate(core=self.Core, nr=s, dic_dcore=dcore_crop, dfit=df_fit_crop, dic_deriv=df_fitder,
                               ax1=self.ax1Fit, ax=self.axFit, fig=self.figFit, grp_label=grp_label, dunit=dunit)
        self.figFit.canvas.draw()
        # exchange the updated depth profile to the dictionary (to plot all)
        self.dShiftFit[c][s] = pd.DataFrame(np.array(dcore_crop), index=dcore_crop.index - df_fitder.idxmin().values[0],
                                            columns=dcore_crop.columns)
        self.dShift[c][s] = pd.DataFrame(np.array(self.dShift[c][s]), index=self.dShift[c][s].index,
                                         columns=self.dShift[c][s].columns)
        # plot baseline corrected depth profiles for special sample
        _ = fO2.GUI_baslineShiftCore(data_shift=self.dShift[c], core_select=self.Core, plot_col=dunit['O2'],
                                     fig=self.figO2, ax=self.axO2, grp_label=grp_label)
        self.figO2.canvas.draw()

    def slider1_update(self):
        global dunit, grp_label
        # clear lists for another trial
        self.ls_out, self.ls_cropx = list(), list()

        # allow only discrete values according to existing cores
        sample_select = min(self.FitCore.keys(), key=lambda x: abs(x - self.slider1.value()))
        # update slider position and label
        self.slider1.setValue(sample_select)
        self.sld1_label.setText('sample: {}'.format(sample_select))

        # update goodness of fit (red. chi-2 for actual fit)
        self.chi2.setText('Goodness of fit (reduced χ2): ' + str(round(self.FitCore[int(sample_select)][0].redchi, 3)))

        # update plot according to selected core
        _ = fO2.plot_Fitselect(core=self.Core, sample=sample_select, dfCore=self.dfCore, dfFit=self.FitCore,
                               dfDeriv=self.DerivCore, fig=self.figFit, ax=self.axFit, ax1=self.ax1Fit, dunit=dunit,
                               grp_label=grp_label)
        self.figFit.canvas.draw()

    def close_window(self):
        self.hide()

    def save_fit(self):
        # create folder (for figure and lmfit-results) if it does not exist
        save_path = self.storage_path + '/O2_project/Fit_results/'
        if not os.path.exists(save_path):
            os.makedirs(save_path)

        save_path_fig = self.storage_path + '/Graphs/O2_project/'
        if not os.path.exists(save_path_fig):
            os.makedirs(save_path_fig)
        save_folder_fig = dbs._actualFolderName(savePath=save_path_fig, cfolder='Fit_results', rlabel='run')
        if not os.path.exists(save_folder_fig):
            os.makedirs(save_folder_fig)

        # create save_name (figure and lmfit results) with an extension to indicate how it was saved
        sample_select = min(self.FitCore.keys(), key=lambda x: abs(x - self.slider1.value()))
        for t in ls_figtype:
            name_fig = save_folder_fig + 'Fit-result_core-{}_sample-{}.'.format(self.Core, sample_select) + t
            # Initiate lmfit figure and store it in figure frame
            plt.ioff()
            fig = plt.figure(figsize=(5, 6), linewidth=0)
            self.FitCore[sample_select][0].plot(fig=fig)
            plt.tight_layout()
            plt.close()
            # save figure
            fig.savefig(name_fig, bbox_inches='tight', pad_inches=0.1, dpi=dpi)

        # save lmfit report as txt file
        name_res0 = save_path + 'Fit-result_core-{}_sample-{}.'.format(self.Core, sample_select) + 'txt'
        name_res = dbs._actualFileName(save_path, file=name_res0, clabel='Fit-result_core', rlabel='run')
        with open(name_res.split('.')[0] + '.txt', 'w') as fh:
            fh.write(self.FitCore[sample_select][0].fit_report())

        # response to user - successfully saved
        msgBox = QMessageBox()
        msgBox.setIcon(QMessageBox.Information)
        msgBox.setText("Selected data are saved successfully.")
        msgBox.setFont(QFont(font_button, fs_font))
        msgBox.setWindowTitle("Successful")
        msgBox.setStandardButtons(QMessageBox.Ok)


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
        MsgGp.setFont(QFont(font_button, fs_font))
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


def GUI_penetration_av(core, ls_core, dcore_pen, fig=None, ax=None, show=True):
    global dobj_hid, dpen_glob
    mean_ = None
    # -----------------------------------------------------------
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
        ls_remain = fO2._supplPlot(core_select=core_select, dobj_hid=dobj_hid, dpen_glob=dpen_glob)

        # re-plot only the ones that are shown
        df = pd.concat([dcore_pen[core_select]['{}-Fit'.format(s[0])] for s in dO2_core[core_select].keys()], axis=1)
        df.columns = [i[0] for i in dO2_core[core].keys()]
        for en, s in enumerate(df.columns):
            if s in ls_remain:
                ax.plot(df[s].dropna(), df[s].dropna().index, color=ls_col[en], lw=1.5, alpha=0.5,
                        label='sample-' + str(s))
        leg = ax.legend(frameon=True, fancybox=True, fontsize=fs_*0.8)
        leg.get_frame().set_linewidth(0.5)

        # indicate penetration depth mean + std according to visible curves
        [dpen_glob, mean_,
         std_] = fO2.av_penetrationDepth(dpen_glob=dpen_glob, core_select=core_select, ls_remain=ls_remain)
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
            plt.close(fig)
        else:
            fig.canvas.draw()
    return fig, mean_


# ---------------------------------------------------------------------------------------------------------------------
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
        # define validator
        validator = QDoubleValidator(-9990, 9990, 4)
        validator.setLocale(QtCore.QLocale("en_US"))
        validator.setNotation(QDoubleValidator.StandardNotation)

        # manual baseline correction
        swi_label, swi_unit_label = QLabel(self), QLabel(self)
        swi_label.setText('Actual correction: '), swi_unit_label.setText('µm')
        self.swi_edit = QLineEdit(self)
        self.swi_edit.setValidator(validator), self.swi_edit.setAlignment(Qt.AlignRight)
        self.swi_edit.setMaximumWidth(100), self.swi_edit.setText('--'), self.swi_edit.setEnabled(False)

        # Action button
        self.savepH_button = QPushButton('Save', self)
        self.savepH_button.setFixedWidth(100), self.savepH_button.setFont(QFont(font_button, fs_font))
        self.continuepH_button = QPushButton('Plot', self)
        self.continuepH_button.setFixedWidth(100), self.continuepH_button.setFont(QFont(font_button, fs_font))
        self.adjustpH_button = QPushButton('Adjustments', self)
        self.adjustpH_button.setFixedWidth(100), self.adjustpH_button.setEnabled(False)
        self.adjustpH_button.setFont(QFont(font_button, fs_font))
        self.updatepH_button = QPushButton('Update SWI', self)
        self.updatepH_button.setFixedWidth(100), self.updatepH_button.setEnabled(False)
        self.updatepH_button.setFont(QFont(font_button, fs_font))
        self.resetpH_button = QPushButton('Reset', self)
        self.resetpH_button.setFixedWidth(100), self.resetpH_button.setFont(QFont(font_button, fs_font))

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
        swiarea.setFont(QFont(font_button, fs_font))
        vbox1_top.addWidget(swiarea)
        swiarea.setLayout(grid_swi)

        # include widgets in the layout
        grid_swi.addWidget(swi_label, 0, 0)
        grid_swi.addWidget(self.swi_edit, 0, 1)
        grid_swi.addWidget(swi_unit_label, 0, 2)
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
        self.figpH, self.axpH = plt.subplots()
        self.canvaspH = FigureCanvasQTAgg(self.figpH)
        self.axpH.set_xlabel('pH value', fontsize=fs_), self.axpH.set_ylabel('Depth / µm', fontsize=fs_)
        self.axpH.invert_yaxis()
        self.figpH.tight_layout(pad=2.5)
        sns.despine()

        pH_group = QGroupBox("pH depth profile")
        pH_group.setMinimumHeight(410)
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
                self.continuepH_button.setEnabled(False)

    def continue_pH(self):
        global dcol_label, grp_label, results, dunit, fs_
        self.setSubTitle("Now,  the SWI can be set.  Either choose the depth determined in the O2 project,  or set "
                         "your own depth wisely.  Press PLOT to continue. \n")

        # set status for process control
        self.status_pH = 0

        # load data
        [checked, grp_label, results, self.ls_colname,
         self.ls_core] = fph.load_pHdata(dcol_label=dcol_label, grp_label=grp_label, data=self.field("Data"),
                                         results=results)

        # save the unit (1 or None) in dunit
        dunit['pH'] = ''

        if checked is True:
            # adjust all the core plots to the same x-scale
            dic_raw = results['pH profile raw data']
            dfpH_scale = pd.concat([pd.DataFrame([(dic_raw[c][n]['pH'].min(), dic_raw[c][n]['pH'].max())
                                                  for n in dic_raw[c].keys()]) for c in dic_raw.keys()])
            self.scale0 = dfpH_scale[0].min(), dfpH_scale[1].max()
            self.scale = self.scale0
            # plot the pH profile for the first core
            _ = fph.plot_pHProfile(data_pH=dic_raw, core=min(self.ls_core), ls_core=self.ls_core, scale=self.scale,
                                   fig=self.figpH, ax=self.axpH, grp_label=grp_label, fs_=fs_)
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
        else:
            # reset page as nothing was found
            self.reset_pHpage()

    def continue_pHII(self):
        global grp_label, fs_
        # update status for process control
        self.status_pH += 1

        # identify closest value in list
        core_select = dbs.closest_core(ls_core=self.ls_core, core=self.sliderpH.value())

        # plot the pH profile for the first core
        if core_select in scalepH.keys():
            scale_plot = self.scale0 if len(scalepH[core_select]) == 0 else scalepH[core_select]
        else:
            scale_plot = self.scale0
        _ = fph.plot_pHProfile(data_pH=results['pH adjusted'], core=core_select, ls_core=self.ls_core, scale=scale_plot,
                               ls='-', fig=self.figpH, ax=self.axpH, grp_label=grp_label, fs_=fs_)
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

        global fs_, grp_label
        _ = fph.plot_pHProfile(data_pH=results['pH adjusted'], core=core_select, ls_core=self.ls_core, ls='-', fs_=fs_,
                               scale=scale_plot, fig=self.figpH, ax=self.axpH, grp_label=grp_label)
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
            global grp_label, fs_
            _ = fph.plot_pHProfile(data_pH=results['pH adjusted'], core=core_select, ls_core=self.ls_core, ls=ls,
                                   scale=scale_plot, fig=self.figpH, ax=self.axpH, grp_label=grp_label, fs_=fs_)
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
        global results, grp_label

        # make a project folder for the specific analyte if it doesn't exist
        save_path = self.field("Storage path") + '/pH_project/'
        if not os.path.exists(save_path):
            os.makedirs(save_path)

        # save data and figures
        fph.save_pHdata(save_path=save_path, save_params=self.field('saving parameters'), data=self.field("Data"),
                        results=results)
        fph.save_pHfigures(save_para=self.field('saving parameters'), path_save=self.field("Storage path"), fs_=fs_,
                           results=results, grp_label=grp_label)

        # Information about successful saving
        msgBox = QMessageBox()
        msgBox.setIcon(QMessageBox.Information)
        msgBox.setText("Selected data are saved successfully.")
        msgBox.setFont(QFont(font_button, fs_font))
        msgBox.setWindowTitle("Successful")
        msgBox.setStandardButtons(QMessageBox.Ok)

        returnValue = msgBox.exec()
        if returnValue == QMessageBox.Ok:
            pass

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
        self.Core, self.rawPlot = min(ls_core, key=lambda x: abs(x - sliderValue)), True

        # get the transmitted data
        self.figpH, self.axpH, self.scaleS0, self.status_pH = figpH, axpH, scale, status_pH

        # plot all samples from current core
        global grp_label
        df = results['pH adjusted'] # results['pH profile raw data'] if self.rawPlot is True else
        _ = fph.plot_adjustpH(core=self.Core, sample=min(df[self.Core].keys()), ax=self.axpHs, scale=self.scaleS0,
                              dfCore=df[self.Core], fig=self.figpHs, grp_label=grp_label)
        # set the range for pH
        self.pHtrim_edit.setText(str(round(self.scaleS0[0], 2)) + ' - ' + str(round(self.scaleS0[1], 2)))

        # connect onclick event with function
        self.ls_out, self.ls_cropy = list(), list()
        self.figpHs.canvas.mpl_connect('button_press_event', self.onclick_updatepH)

        # update slider range to number of samples and set to first sample
        self.slider1pH.setMinimum(int(min(df[self.Core].keys())))
        self.slider1pH.setMaximum(int(max(df[self.Core].keys())))
        self.slider1pH.setValue(int(min(df[self.Core].keys())))
        self.sldpH1_label.setText('sample: ' + str(int(min(df[self.Core].keys()))))

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
        self.msg.setWordWrap(True), self.msg.setFont(QFont(font_button, fs_font))

        # Slider for different cores and label on the right
        self.slider1pH = QSlider(Qt.Horizontal)
        self.slider1pH.setMinimumWidth(350), self.slider1pH.setFixedHeight(20)
        self.sldpH1_label = QLabel()
        self.sldpH1_label.setFixedWidth(70), self.sldpH1_label.setText('sample: --')

        # plot individual sample
        self.figpHs, self.axpHs = plt.subplots(figsize=(3, 2), linewidth=0)
        self.figpHs.set_facecolor("none")
        self.canvaspHs = FigureCanvasQTAgg(self.figpHs)
        self.navipHs = NavigationToolbar2QT(self.canvaspHs, self, coordinates=False)
        self.axpHs.set_xlabel('pH value', fontsize=fs_), self.axpHs.set_ylabel('Depth / µm', fontsize=fs_)
        self.axpHs.invert_yaxis()
        self.figpHs.subplots_adjust(bottom=0.2, right=0.95, top=0.9, left=0.15)
        sns.despine()

        # define validator
        validator = QDoubleValidator(-9990, 9990, 4)
        validator.setLocale(QtCore.QLocale("en_US"))
        validator.setNotation(QDoubleValidator.StandardNotation)

        # define pH range
        pHtrim_label = QLabel(self)
        pHtrim_label.setText('pH range: '), pHtrim_label.setFont(QFont(font_button, fs_font))
        self.pHtrim_edit = QLineEdit(self)
        self.pHtrim_edit.setValidator(QRegExpValidator())
        self.pHtrim_edit.setAlignment(Qt.AlignRight), self.pHtrim_edit.setMaximumHeight(int(fs_font*1.5))

        # swi correction for individual sample
        swiSample_label = QLabel(self)
        swiSample_label.setText('SWI correction sample: '), swiSample_label.setFont(QFont(font_button, fs_font))
        self.swiSample_edit = QLineEdit(self)
        self.swiSample_edit.setValidator(validator), self.swiSample_edit.setAlignment(Qt.AlignRight)
        self.swiSample_edit.setMaximumHeight(int(fs_font*1.5)), self.swiSample_edit.setText('--')

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
        MsgGp.setFont(QFont(font_button, fs_font))
        gridMsg = QGridLayout()
        vbox2_top.addWidget(MsgGp)
        MsgGp.setLayout(gridMsg)

        # add GroupBox to layout and load buttons in GroupBox
        gridMsg.addWidget(self.msg, 1, 0)

        # in-between for sample plot
        plotGp = QGroupBox()
        plotGp.setFont(QFont(font_button, fs_font))
        plotGp.setMinimumHeight(500)
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
        naviGp.setFont(QFont(font_button, fs_font))
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
        global grp_label
        df = results['pH profile raw data'] if self.rawPlot is True else results['pH adjusted']
        _ = fph.plot_adjustpH(core=self.Core, sample=sample_select, dfCore=df[self.Core], scale=self.scale,
                              fig=self.figpHs, ax=self.axpHs, grp_label=grp_label)
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
        self.rawPlot = False
        # check if the pH range (scale) changed
        self.updatepHscale()

        # current core and sample
        c, s = self.Core, int(self.sldpH1_label.text().split(' ')[-1])

        # crop dataframe to selected range
        df_crop = self.cropDF_pH(s=s)

        # pop outliers from depth profile
        df_pop = self.popData_pH(df_crop=df_crop, s=s) if self.ls_out else df_crop

        # check individual swi for sample
        try:
            int(self.swiSample_edit.text())
            # correction of manually selected baseline and store adjusted pH
            ynew = df_pop.index - float(self.swiSample_edit.text())
            df_pop = pd.DataFrame(df_pop.to_numpy(), index=ynew, columns=df_pop.columns)
            self.swiSample_edit.setText('--')
        except:
            try:
                float(self.swiSample_edit.text())
                # correction of manually selected baseline and store adjusted pH
                ynew = df_pop.index - float(self.swiSample_edit.text())
                df_pop = pd.DataFrame(df_pop.to_numpy(), index=ynew, columns=df_pop.columns)
                self.swiSample_edit.setText('--')
            except:
                pass

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
        global grp_label
        df = results['pH profile raw data'] if self.rawPlot is True else results['pH adjusted']
        _ = fph.plot_pHUpdate(core=self.Core, nr=s, df_pHs=df[self.Core][s], scale=self.scale, ddcore=df[self.Core],
                              ax=self.axpHs, fig=self.figpHs, grp_label=grp_label)
        self.figpHs.canvas.draw()

        # update range for pH plot and plot in main window
        self.pHtrim_edit.setText(str(round(self.scale[0], 2)) + ' - ' + str(round(self.scale[1], 2)))
        ls = '-.' if self.status_pH < 1 else '-'
        _ = fph.plot_pHProfile(data_pH=df, core=self.Core, ls_core=df.keys(), scale=self.scale, fig=self.figpH,
                               ax=self.axpH, trimexact=True, grp_label=grp_label, fs_=fs_, ls=ls)
        self.figpH.canvas.draw()

    def resetPlot(self):
        # plot_status as initialization hint
        self.rawPlot = True
        # reset texts
        self.pHtrim_edit.setText(str(round(self.scaleS0[0], 2)) + ' - ' + str(round(self.scaleS0[1], 2)))
        self.swiSample_edit.setText('--')
        # set slider to actual value
        sample_select = min(results['pH adjusted'][self.Core].keys(), key=lambda x: abs(x - self.slider1pH.value()))
        self.slider1pH.setValue(sample_select)

        # re-set plot to raw data
        _ = fph.plot_adjustpH(core=self.Core, sample=sample_select, scale=self.scaleS0, grp_label=grp_label,
                              dfCore=results['pH profile raw data'][self.Core], fig=self.figpHs, ax=self.axpHs)
        self.figpHs.canvas.draw()
        # re-plot profiles in main window
        ls = '-.' if self.status_pH < 1 else '-'
        _ = fph.plot_pHProfile(data_pH=results['pH profile raw data'], core=self.Core, grp_label=grp_label, fs_=fs_,
                               ls_core=results['pH profile raw data'].keys(), scale=self.scale, fig=self.figpH, ls=ls,
                               ax=self.axpH, trimexact=True)
        self.figpH.canvas.draw()

    def close_window(self):
        self.hide()


# ---------------------------------------------------------------------------------------------------------------------
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

    def initUI(self):
        # define validator
        validator = QDoubleValidator(-9990, 9990, 4)
        validator.setLocale(QtCore.QLocale("en_US"))
        validator.setNotation(QDoubleValidator.StandardNotation)
        validator_pos = QDoubleValidator(0., 9990, 4)
        validator_pos.setLocale(QtCore.QLocale("en_US"))
        validator_pos.setNotation(QDoubleValidator.StandardNotation)

        # plot window, side panel for user input, and continue button
        tempC_label, tempC_unit_label = QLabel(self), QLabel(self)
        tempC_label.setText('Temperature'), tempC_unit_label.setText('degC')
        self.tempC_edit = QLineEdit(self)
        self.tempC_edit.setValidator(validator), self.tempC_edit.setAlignment(Qt.AlignRight)
        self.tempC_edit.setMaximumWidth(100), self.tempC_edit.setText(str(results['temperature degC']))

        sal_label, sal_unit_label = QLabel(self), QLabel(self)
        sal_label.setText('Salinity'), sal_unit_label.setText('PSU')
        self.sal_edit = QLineEdit(self)
        self.sal_edit.setValidator(validator_pos), self.sal_edit.setAlignment(Qt.AlignRight)
        self.sal_edit.setMaximumWidth(100)
        if 'salinity PSU' in results.keys():
            self.sal_edit.setText(str(results['salinity PSU']))
        else:
            self.sal_edit.setText('0.')

        # manual baseline correction
        swih2s_label, swih2s_unit_label = QLabel(self), QLabel(self)
        swih2s_label.setText('Actual correction: '), swih2s_unit_label.setText('µm')
        self.swih2s_edit = QLineEdit(self)
        self.swih2s_edit.setValidator(validator), self.swih2s_edit.setAlignment(Qt.AlignRight)
        self.swih2s_edit.setMaximumWidth(100), self.swih2s_edit.setText('--'), self.swih2s_edit.setEnabled(False)

        # define concentration for sulfidic front
        sFh2s_label, sFh2s_unit_label = QLabel(self), QLabel(self)
        sFh2s_label.setText('Sulfidic Front: '), sFh2s_unit_label.setText('µmol/L')
        self.sFh2s_edit = QLineEdit(self)
        self.sFh2s_edit.setValidator(validator_pos), self.sFh2s_edit.setAlignment(Qt.AlignRight)
        self.sFh2s_edit.setMaximumWidth(100), self.sFh2s_edit.setText('0.5'), self.sFh2s_edit.setEnabled(False)

        # Action button
        self.salcon_button = QPushButton('Converter', self)
        self.salcon_button.setFixedWidth(100), self.salcon_button.setFont(QFont(font_button, fs_font))
        self.saveh2s_button = QPushButton('Save', self)
        self.saveh2s_button.setFixedWidth(100), self.saveh2s_button.setFont(QFont(font_button, fs_font))
        self.continueh2s_button = QPushButton('Plot', self)
        self.continueh2s_button.setFixedWidth(100), self.continueh2s_button.setFont(QFont(font_button, fs_font))
        self.adjusth2s_button = QPushButton('Adjust profile', self)
        self.adjusth2s_button.setFixedWidth(100), self.adjusth2s_button.setEnabled(False)
        self.adjusth2s_button.setFont(QFont(font_button, fs_font))
        self.updateh2s_button = QPushButton('Update SWI', self)
        self.updateh2s_button.setFixedWidth(100), self.updateh2s_button.setEnabled(False)
        self.updateh2s_button.setFont(QFont(font_button, fs_font))
        self.reseth2s_button = QPushButton('Reset', self)
        self.reseth2s_button.setFixedWidth(100), self.reseth2s_button.setFont(QFont(font_button, fs_font))

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
        para_settings.setFont(QFont(font_button, fs_font))
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
        self.figh2s, self.axh2s = plt.subplots()
        self.canvash2s = FigureCanvasQTAgg(self.figh2s)
        self.axh2s.set_xlabel('H2S / µmol/L', fontsize=fs_), self.axh2s.set_ylabel('Depth / µm', fontsize=fs_)
        self.axh2s.invert_yaxis()
        self.figh2s.subplots_adjust(bottom=0.2, right=0.95, top=0.9, left=0.15)
        sns.despine()

        H2S_group = QGroupBox("H2S depth profile")
        H2S_group.setMinimumHeight(340), H2S_group.setMinimumWidth(550)
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

    def conductivity_converter(self):
        # open dialog window for conductivity -> salinity conversion
        global wConv
        wConv = SalConvWindowO2(self.tempC_edit, self.sal_edit)
        if wConv.isVisible():
            pass
        else:
            wConv.show()

    def continue_H2S(self):
        global results, dunit, grp_label, dcol_label
        # get relevant information from previous projects if possible
        ssal = str(round(results['salinity PSU'], 4)) if 'salinity PSU' in results.keys() else '0.'
        self.sal_edit.setText(ssal)

        # set status for process control
        self.status_h2s = 0

        # initial unit / analyte of this project is H2S and mV
        dunit['H2S'] = 'µmol/L'

        # update subtitle in case the pH profile was present as well
        if 'pH profile raw data' in results.keys():
            self.setSubTitle("You reached the sediment-water interface correction.  You can manually adjust the surface"
                             " and update the profile by clicking the update button.\n")

        # load data - mV and µM
        [checked, self.ls_core, results, self.ls_colname, self.dH2S_core,
         grp_label] = fh2s.load_H2Sdata(data=self.field("Data"), dcol_label=dcol_label, grp_label=grp_label,
                                        results=results)
        if checked is True:
            # adjust all the core plots to the same x-scale (uncalibrated)
            c = list(self.dH2S_core.keys())[0]
            nr = list(self.dH2S_core[c].keys())[0]
            self.colH2S = self.dH2S_core[c][nr].columns[1]
            dfH2S_scale = pd.concat([pd.DataFrame([(self.dH2S_core[c][n][self.colH2S].min(),
                                                    self.dH2S_core[c][n][self.colH2S].max())
                                                   for n in self.dH2S_core[c].keys()]) for c in self.dH2S_core.keys()])
            self.scale0 = dfH2S_scale[0].min(), dfH2S_scale[1].max()
            self.scale = self.scale0

            # plot the pH profile for the first core
            global dobj_hidH2S
            dobj_hidH2S = fh2s.plot_H2SProfile(data_H2S=self.dH2S_core, core=min(self.ls_core), ls_core=self.ls_core,
                                               col=self.colH2S, scale=self.scale0, dobj_hidH2S=dobj_hidH2S, fs_=fs_,
                                               fig=self.figh2s, ax=self.axh2s, grp_label=grp_label, dunit=dunit)[-1]

            # update results for a intermediate H2S baseline set
            results['H2S profile interim'] = dict()
            for c in results['H2S adjusted'].keys():
                ddic = dict(map(lambda i: (i, pd.DataFrame(np.array(results['H2S adjusted'][c][i]),
                                                           index=results['H2S adjusted'][c][i].index,
                                                           columns=results['H2S adjusted'][c][i].columns)),
                                results['H2S adjusted'][c].keys()))
                results['H2S profile interim'][c] = ddic

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
                dsheets_add = fh2s.load_additionalInfo_h2s(data=self.field("Data"))
                results['pH - H2S correlation'] = dsheets_add['pH - H2S correlation']

                # calculation of total sulfide possible
                self.continueh2s_button.clicked.connect(self.continue_H2SIIa)
            else:
                # skip total sulfide but allow swi correction
                self.continueh2s_button.clicked.connect(self.continue_H2SIIb)
        else:
            self.reset_H2Spage()

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
                msgBox.setFont(QFont(font_button, fs_font))
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
            msgBox.setFont(QFont(font_button, fs_font))
            msgBox.setWindowTitle("Warning")
            msgBox.setStandardButtons(QMessageBox.Ok)

            returnValue = msgBox.exec()
            if returnValue == QMessageBox.Ok:
                pass

        return df_correl

    def continue_H2SIIa(self):
        global grp_label, dunit, dobj_hidH2S, scaleh2s, results
        self.updateh2s_button.setEnabled(False), self.swih2s_edit.setEnabled(False)

        # update subtitle for swi correction
        self.setSubTitle("The total sulfide ΣS2- is calculated based on H2S as well as the temperature and salinity.  "
                         "Please make sure both parameters are correct..\n")

        # update status for process control
        self.status_h2s = 1

        # update the analyte that is used
        dunit['total sulfide'] = 'µmol/L'

        # identify closest value in list
        core_select = dbs.closest_core(ls_core=self.ls_core, core=self.sliderh2s.value())

        # convert H2S into total sulfide in case pH was measured
        dsulfide, results = fh2s.calc_total_sulfide(results=results, dH2S_core=self.dH2S_core, sal_edit=self.sal_edit,
                                                    tempC_edit=self.tempC_edit, convC2K=convC2K)
        results['H2S profile total sulfide'] = dsulfide

        # create a total sulfide adjusted DF
        lab_raw = 'H2S profile total sulfide'
        results['H2S total sulfide adjusted'] = dict()
        for c in results[lab_raw].keys():
            ddic = dict(map(lambda i:
                            (i, pd.DataFrame(np.array(results[lab_raw][c][i]), index=results[lab_raw][c][i].index,
                                             columns=results[lab_raw][c][i].columns)), results[lab_raw][c].keys()))
            results['H2S total sulfide adjusted'][c] = ddic

        # update pH profile plot for the first core
        para = 'total sulfide zero corr_µmol/L'
        dscale = dict()
        for c in dsulfide.keys():
            l = np.array([(dsulfide[c][nr][para].min(), dsulfide[c][nr][para].max()) for nr in dsulfide[c].keys()])
            # outlier test
            l = l[(l > np.quantile(l, 0.1)) & (l < np.quantile(l, 0.75))].tolist()

            # summarize for absolute min/max analysis
            dscale[c] = pd.DataFrame((np.nanmin(l), np.nanmax(l)))

        self.scaleS0 = (pd.concat(dscale, axis=1).T[0].min(), pd.concat(dscale, axis=1).T[1].max())
        self.col2 = para

        # update column name that shall be plotted
        te = True if core_select in scaleh2s.keys() else False
        dobj_hidH2S = fh2s.plot_H2SProfile(data_H2S=dsulfide, core=core_select, ls_core=self.ls_core, dunit=dunit,
                                           scale=self.scaleS0, ls='-', fig=self.figh2s, ax=self.axh2s, col=self.col2,
                                           dobj_hidH2S=dobj_hidH2S, trimexact=te, fs_=fs_, grp_label=grp_label)[-1]

        # slider initialized to first core
        self.sliderh2s.setMinimum(int(min(self.ls_core))), self.sliderh2s.setMaximum(int(max(self.ls_core)))
        self.sliderh2s.setValue(int(min(self.ls_core)))
        self.sldh2s_label.setText('{}: {}'.format(self.ls_colname[0], int(min(self.ls_core))))

        # when slider value change (on click), return new value and update figure plot
        scaleh2s = dict()
        self.sliderh2s.valueChanged.connect(self.sliderh2s_updateII)

        # update continue button as well as adjustment button in case the swi shall be updated
        self.adjusth2s_button.disconnect()
        self.adjusth2s_button.clicked.connect(self.adjust_H2SII)
        self.continueh2s_button.disconnect()
        self.continueh2s_button.clicked.connect(self.sulfidicFront)

    def continue_H2SIIb(self):
        global scaleh2s, grp_label, dunit, dobj_hidH2S, results
        self.updateh2s_button.setEnabled(False), self.swih2s_edit.setEnabled(False)

        # update status for process control
        self.status_h2s = 2

        # update layout
        self.swih2s_edit.setEnabled(True)

        # update subtitle for swi correction
        self.setSubTitle("You can manually adjust the surface and update the profile by clicking the update button.\n\n")

        # identify closest value in list
        core_select = dbs.closest_core(ls_core=self.ls_core, core=self.sliderh2s.value())
        # identify data, that shall be plotted
        self.data = results['H2S profile total sulfide'] if 'H2S profile total sulfide' in results.keys() else self.dH2S_core

        # plot the pH profile for the first core
        core_select_ = dbs._findCoreLabel(option1=core_select, option2='core ' + str(core_select), ls=scaleh2s.keys())
        if core_select_ in scaleh2s.keys():
            scale_plot = self.scale0 if len(scaleh2s[core_select_]) == 0 else scaleh2s[core_select_]
        else:
            scale_plot = self.scale0
        te = True if core_select_ in scaleh2s.keys() else False
        dobj_hidH2S = fh2s.plot_H2SProfile(data_H2S=self.data, core=core_select, ls_core=self.ls_core, scale=scale_plot,
                                           ls='-', fig=self.figh2s, ax=self.axh2s, col=self.colH2S, dunit=dunit,
                                           dobj_hidH2S=dobj_hidH2S, grp_label=grp_label, trimexact=te, fs_=fs_)[-1]
        self.figh2s.canvas.draw()

        # update continue button as well as adjustment button in case the swi shall be updated
        self.continueh2s_button.disconnect()
        self.continueh2s_button.clicked.connect(self.sulfidicFront)

    def swi_correctionH2S(self):
        global scaleh2s
        # identify the data to adjust (SWI)
        data = results['H2S adjusted']

        # identify closest value in list
        core_select = min(self.ls_core, key=lambda x: abs(x - self.sliderh2s.value()))
        self.continueh2s_button.setEnabled(True)

        if '--' in self.swih2s_edit.text() or len(self.swih2s_edit.text()) == 0:
            pass
        else:
            # correction of manually selected baseline
            core_select = dbs._findCoreLabel(option1=core_select, option2='core '+str(core_select),
                                             ls=list(data.keys()))
            for s in data[core_select].keys():
                # H2S correction
                ynew = data[core_select][s].index - float(self.swih2s_edit.text())
                data[core_select][s].index = ynew

        # add to results dictionary
        label1, label2 = 'H2S total sulfide adjusted', 'H2S adjusted'
        if label1 in results.keys():
            results[label1] = data
        else:
            results[label2] = data

        # plot the pH profile for the first core
        ls = '-.' if self.status_h2s < 1 else '-'
        te = True if core_select in scaleh2s.keys() else False
        global grp_label, dunit, dobj_hidH2S
        dobj_hidH2S = fh2s.plot_H2SProfile(data_H2S=data, core=core_select, ls_core=self.ls_core, col=self.colH2S,
                                           ax=self.axh2s, scale=self.scale0, dobj_hidH2S=dobj_hidH2S, fig=self.figh2s,
                                           grp_label=grp_label, fs_=fs_, dunit=dunit, trimexact=te, ls=ls)[-1]
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
        label1, label2 = 'H2S total sulfide adjusted', 'H2S adjust'
        df_sulfFront = results[label1] if label1 in results.keys() else results[label2]
        df_sFront = dict()
        for coreS in df_sulfFront.keys():
            ls_sample = list()
            for en, s in enumerate(df_sulfFront[coreS].keys()):
                df_, col = df_sulfFront[coreS][s], df_sulfFront[coreS][s].columns[-1]
                sulFront = df_[col][df_[col] >= float(self.sFh2s_edit.text())]
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
            if np.nanmean(dfCore.loc[smp_all]) >= 0:
                dfCore.loc['mean', 'sulfidic front'] = np.nanmean(dfCore.loc[smp_all])
            else:
                dfCore.loc['mean', 'sulfidic front'] = 0
            dfCore.loc['std', 'sulfidic front'] = np.nanstd(dfCore.loc[smp_all])
            df_sFront[coreS] = dfCore
        results['H2S sulfidic front'], results['H2S hidden objects'] = df_sFront, dobj_hidH2S

        # identify closest value in list
        core_select = dbs.closest_core(ls_core=self.ls_core, core=self.sliderh2s.value())

        # indicate sulfidic front in plot
        global grp_label
        fh2s.plot_sulfidicFront(df_Front=results['H2S sulfidic front'], core_select=core_select, grp_label=grp_label,
                                fig=self.figh2s, ax=self.axh2s)

        # when slider value change (on click), return new value and update figure plot
        self.adjusth2s_button.disconnect(), self.adjusth2s_button.setEnabled(False)
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
            global scaleh2s
            if core_select in scaleh2s.keys():
                scale_plot = self.scale0 if len(scaleh2s[core_select]) == 0 else scaleh2s[core_select]
            else:
                scale_plot = self.scale0
            ls = '-.' if self.status_h2s < 1 else '-'
            te = True if core_select in scaleh2s.keys() else False
            global grp_label, dunit, dobj_hidH2S, results
            dobj_hidH2S = fh2s.plot_H2SProfile(data_H2S=results['H2S adjusted'], core=core_select, scale=scale_plot,
                                               ls=ls, fig=self.figh2s, ax=self.axh2s, dobj_hidH2S=dobj_hidH2S,
                                               ls_core=self.ls_core, col=self.colH2S, trimexact=te, grp_label=grp_label,
                                               dunit=dunit, fs_=fs_)[-1]
            self.figh2s.canvas.draw()

    def sliderh2s_updateII(self):
        global scaleh2s
        if self.ls_core:
            # allow only discrete values according to existing cores
            core_select = min(self.ls_core, key=lambda x: abs(x - self.sliderh2s.value()))

            # update slider position and label
            self.sliderh2s.setValue(int(core_select))
            self.sldh2s_label.setText('{}: {}'.format(self.ls_colname[0], core_select))

            # update plot according to selected core
            core_select_ = dbs._findCoreLabel(option1=core_select, option2='core ' + str(core_select),
                                              ls=scaleh2s.keys())
            if core_select_ in scaleh2s.keys():
                scale_plot = self.scale0 if len(scaleh2s[core_select_]) == 0 else scaleh2s[core_select_]
            else:
                scale_plot = self.scaleS0
            te = True if core_select_ in scaleh2s.keys() else False
            global grp_label, dunit, dobj_hidH2S, results
            dobj_hidH2S = fh2s.plot_H2SProfile(data_H2S=results['H2S total sulfide adjusted'], core=core_select, ls='-',
                                               ls_core=self.ls_core, col=self.col2, scale=scale_plot, fig=self.figh2s,
                                               ax=self.axh2s, fs_=fs_, dunit=dunit, dobj_hidH2S=dobj_hidH2S,
                                               trimexact=te, grp_label=grp_label)[-1]
            self.figh2s.canvas.draw()

    def sliderh2s_updateIII(self):
        if self.ls_core:
            # allow only discrete values according to existing cores
            core_select = min(self.ls_core, key=lambda x: abs(x - self.sliderh2s.value()))

            # update slider position and label
            self.sliderh2s.setValue(int(core_select))
            self.sldh2s_label.setText('{}: {}'.format(self.ls_colname[0], core_select))

            # update plot according to selected core
            global grp_label
            fh2s.plot_sulfidicFront(df_Front=results['H2S sulfidic front'], core_select=core_select, ax=self.axh2s,
                                    grp_label=grp_label, fig=self.figh2s)
            self.figh2s.canvas.draw()

    def adjust_H2S(self):
        # open dialog window to adjust data presentation
        global wAdjustS, results
        res_pH = results['pH - H2S correlation'] if 'pH - H2S correlation' in results.keys() else None
        df_H2S_raw = results['H2S adjusted']
        wAdjustS = AdjustpHWindowS(self.sliderh2s.value(), self.ls_core, df_H2S_raw, self.colH2S, self.figh2s,
                                   self.axh2s, res_pH, self.swih2s_edit, 0)
        if wAdjustS.isVisible():
            pass
        else:
            wAdjustS.show()

    def adjust_H2SII(self):
        # open dialog window to adjust data presentation
        global wAdjustS, results
        res_pH = results['pH - H2S correlation'] if 'pH - H2S correlation' in results.keys() else None
        df_H2S_raw = self.dH2S_core if 'H2S total sulfide adjusted' in results else results['H2S profile total sulfide']
        wAdjustS = AdjustpHWindowS(self.sliderh2s.value(), self.ls_core, df_H2S_raw, self.col2, self.figh2s, self.axh2s,
                                   res_pH, self.swih2s_edit, self.status_h2s)
        if wAdjustS.isVisible():
            pass
        else:
            wAdjustS.show()

    def save_H2S(self):
        global dout, ls_allData, grp_label, dunit, results, dobj_hidH2S
        # preparation to save data
        dout = fh2s.prepDataH2Soutput(dout=dout, results=results)

        # actual saving of data and figures
        fh2s.save_H2Sdata(save_path=self.field("Storage path"), save_para=self.field('saving parameters'), dout=dout,
                          data=self.field("Data"), ls_allData=ls_allData)
        fh2s.save_H2Sfigure(save_para=self.field('saving parameters'), save_path=self.field("Storage path"), fs_=fs_,
                            ls_core=self.ls_core, grp_label=grp_label, dunit=dunit, dobj_hidH2S=dobj_hidH2S,
                            results=results)

        # Information that saving was successful
        msgBox = QMessageBox()
        msgBox.setIcon(QMessageBox.Information)
        msgBox.setText("Selected data are saved successfully.")
        msgBox.setFont(QFont(font_button, fs_font))
        msgBox.setWindowTitle("Successful")
        msgBox.setStandardButtons(QMessageBox.Ok)

        returnValue = msgBox.exec()
        if returnValue == QMessageBox.Ok:
            pass

    def reset_H2Spage(self):
        # reset global parameter
        global scaleh2s, dobj_hidH2S
        scaleh2s, dobj_hidH2S = dict(), dict()

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
        if 'H2S profile interim' in results.keys():
            results.pop('H2S profile interim')
        if 'H2S total sulfide adjusted' in results.keys():
            results.pop('H2S total sulfide adjusted')

        results['H2S adjusted'] = dict()
        for c in results['pH profile raw data'].keys():
            ddic = dict(map(lambda i: (i, pd.DataFrame(np.array(results['pH profile raw data'][c][i]),
                                                       index=results['pH profile raw data'][c][i].index,
                                                       columns=results['pH profile raw data'][c][i].columns)),
                            results['pH profile raw data'][c].keys()))
            results['H2S adjusted'][c] = ddic

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
        if self.status_h2s < 2:
            self.continueh2s_button.disconnect()
        self.continueh2s_button.clicked.connect(self.continue_H2S)
        self.continueh2s_button.setEnabled(True)
        self.adjusth2s_button.clicked.connect(self.adjust_H2S)
        self.adjusth2s_button.setEnabled(False)
        self.saveh2s_button.clicked.connect(self.save_H2S)
        self.updateh2s_button.setEnabled(False), self.swih2s_edit.setEnabled(False)
        self.sFh2s_edit.setText('0.5'), self.sFh2s_edit.setEnabled(False)

        # reset slider
        self.count = 0
        self.sliderh2s.setValue(int(min(self.ls_core)))
        self.sldh2s_label.setText('group: --')
        self.sliderh2s.disconnect()
        self.sliderh2s.valueChanged.connect(self.sliderh2s_update)

        # clear pH range (scale), SWI correction
        self.swih2s_edit.setText('--')

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
        self.status_h2s = 0

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


class AdjustpHWindowS(QDialog):
    def __init__(self, sliderValue, ls_core, dic_H2S, col, figH2S, axH2S, df_correl, swih2s_edit, status):
        super().__init__()
        self.initUI()

        # get the transmitted data
        global grp_label, results
        self.rawPlot = True
        self.figH2S, self.axH2S, self.dic_H2S, self.colH2S = figH2S, axH2S, dic_H2S, col
        self.df_correl, self.ls_core, self.swih2s_edit, self.status_ph = df_correl, ls_core, swih2s_edit, status
        self.ls = '-.' if self.status_ph == 0 else '-'

        # return current core - and get the samples to plot (via slider selection)
        self.Core = min(self.ls_core, key=lambda x: abs(x - sliderValue))

        # plot all samples from current core
        self.Core = dbs._findCoreLabel(option1=self.Core, option2='core ' +str(self.Core), ls=self.dic_H2S)
        h2s_nr = min(self.dic_H2S[self.Core].keys())
        if self.df_correl is None:
            pH_sample, pH_core = None, None
        else:
            pH_sample = self.df_correl[self.df_correl['H2S Nr'] == h2s_nr]['pH Nr'].to_numpy()[0]
            c = dbs._findCoreLabel(option1=self.Core, option2='core '+str(self.Core),
                                   ls=self.df_correl['H2S code'].to_numpy())
            pH_core = self.df_correl[self.df_correl['H2S code'] == c]['pH code'].to_numpy()[0]

        # get pH data and in case apply depth correction in case it was done for H2S / total sulfide
        self.pH_data = results['pH adjusted'] if 'pH adjusted' in results.keys() else None
        if self.pH_data:
            results = fh2s.swi_correctionpHII(results=results, pH_data=self.pH_data)
        df = fh2s.select_h2sDF_core(core=self.Core, results=results, dic_H2S=self.dic_H2S, rawPlot=self.rawPlot)[-1]
        _, self.ax1, self.scale = fh2s.plot_adjustH2S(core=self.Core, sample=h2s_nr, col=self.colH2S, results=results,
                                                      dfCore=df, pH=self.pH_data, pH_sample=pH_sample, pH_core=pH_core,
                                                      grp_label=grp_label, ls='-.', fig=self.figH2Ss, ax=self.axH2Ss)
        # set the range for pH
        self.H2Strim_edit.setText(str(round(self.scale[0], 2)) + ' - ' + str(round(self.scale[1], 2)))

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
        self.msg.setWordWrap(True), self.msg.setFont(QFont(font_button, fs_font))

        # Slider for different cores and label on the right
        self.slider1H2S = QSlider(Qt.Horizontal)
        self.slider1H2S.setMinimumWidth(350), self.slider1H2S.setFixedHeight(20)
        self.sldH2S1_label = QLabel()
        self.sldH2S1_label.setFixedWidth(70), self.sldH2S1_label.setText('sample: --')

        # plot individual sample
        self.figH2Ss, self.axH2Ss = plt.subplots(figsize=(3, 2.5), linewidth=0)
        self.figH2Ss.set_facecolor("none")
        self.canvasH2Ss = FigureCanvasQTAgg(self.figH2Ss)
        self.naviH2Ss = NavigationToolbar2QT(self.canvasH2Ss, self, coordinates=False)
        self.axH2Ss.set_xlabel('H2S / µmol/L', fontsize=fs_), self.axH2Ss.set_ylabel('Depth / µm', fontsize=fs_)
        self.axH2Ss.invert_yaxis()
        self.figH2Ss.subplots_adjust(bottom=0.2, right=0.95, top=0.85, left=0.15)
        sns.despine()

        # define pH range
        H2Strim_label = QLabel(self)
        H2Strim_label.setText('H2S range: '), H2Strim_label.setFont(QFont(font_button, fs_font))
        self.H2Strim_edit = QLineEdit(self)
        self.H2Strim_edit.setValidator(QRegExpValidator()), self.H2Strim_edit.setAlignment(Qt.AlignRight)
        self.H2Strim_edit.setMaximumHeight(int(fs_font*1.5))

        # define validator
        validator = QDoubleValidator(-9990, 9990, 4)
        validator.setLocale(QtCore.QLocale("en_US"))
        validator.setNotation(QDoubleValidator.StandardNotation)

        # swi correction for individual sample
        swiSample_label = QLabel(self)
        swiSample_label.setText('SWI correction sample: '), swiSample_label.setFont(QFont(font_button, fs_font))
        self.swiSample_edit = QLineEdit(self)
        self.swiSample_edit.setValidator(validator), self.swiSample_edit.setAlignment(Qt.AlignRight)
        self.swiSample_edit.setMaximumHeight(int(fs_font*1.5)), self.swiSample_edit.setText('--')

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
        MsgGp.setFont(QFont(font_button, fs_font))
        gridMsg = QGridLayout()
        vbox2_top.addWidget(MsgGp)
        MsgGp.setLayout(gridMsg)

        # add GroupBox to layout and load buttons in GroupBox
        gridMsg.addWidget(self.msg, 1, 0)

        # in-between for sample plot
        plotGp = QGroupBox()
        plotGp.setFont(QFont(font_button, fs_font))
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
        naviGp.setFont(QFont(font_button, fs_font))
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
        global grp_label
        # clear lists for another trial
        self.ls_out, self.ls_cropy = list(), list()

        # get actual scale
        if self.H2Strim_edit.text():
            if len(self.H2Strim_edit.text().split('-')) > 1:
                # assume that negative numbers occur
                ls = re.findall(r"[-+]?(?:\d*\.\d+|\d+)", self.H2Strim_edit.text())
                self.scale = (-0.5, float(ls[1]))
            else:
                self.scale = (-0.5, float(self.H2Strim_edit.text().split('-')[1].strip()))

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
            c = dbs._findCoreLabel(option1=self.Core, option2='core ' + str(self.Core),
                                   ls=self.df_correl['H2S code'].to_numpy())
            pH_core = self.df_correl[self.df_correl['H2S code'] == c]['pH code'].to_numpy()[0]
        pH_data = results['pH profile raw data'] if 'pH profile raw data' in results.keys() else None
        df = fh2s.select_h2sDF_core(core=self.Core, results=results, dic_H2S=self.dic_H2S, rawPlot=self.rawPlot)[-1]
        _, self.ax1, self.scale = fh2s.plot_adjustH2S(core=self.Core, sample=sample_select, dfCore=df, pH=pH_data,
                                                      results=results, pH_sample=pH_sample, pH_core=pH_core, ls='-.',
                                                      fig=self.figH2Ss, ax1=self.ax1, ax=self.axH2Ss, col=self.colH2S,
                                                      grp_label=grp_label)

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

    def adjustH2S(self):
        # collect global parameter
        global results, grp_label, grp_label, dunit, scaleh2s
        self.rawPlot = False

        # check if the pH range (scale) changed
        scaleh2s, self.scale = fh2s.updateH2Sscale(H2Strim_edit=self.H2Strim_edit, scaleh2s=scaleh2s, scale_=self.scale,
                                                   Core=self.Core)
        self.status_ph = 1

        # current core, current sample
        c, s = self.Core, int(self.sldH2S1_label.text().split(' ')[-1])

        # crop df to selected range
        dcore_crop, results, self.ls_cropy = fh2s.cropDF_H2S(s=s, ls_cropy=self.ls_cropy, Core=self.Core,
                                                             dic_H2S=self.dic_H2S, results=results)
        # pop outliers from depth profile
        if self.ls_out:
            dcore_crop = fh2s.popData_H2S(dcore_crop=dcore_crop, ls_out=self.ls_out)

        # check individual swi for sample
        try:
            int(self.swiSample_edit.text())
            swiS = float(self.swiSample_edit.text())
            xnew = dcore_crop.index - swiS
            dcore_crop.index = xnew
            self.swiSample_edit.setText('--')
        except:
            try:
                float(self.swiSample_edit.text())
                swiS = float(self.swiSample_edit.text())
                xnew = dcore_crop.index - swiS
                dcore_crop.index = xnew
                self.swiSample_edit.setText('--')
            except:
                pass

        # update the general dictionary and store adjusted pH
        self.dic_H2S[self.Core][s] = dcore_crop

        # re-draw pH profile plot
        if self.df_correl is None:
            pH_sample, pH_core = None, None
        else:
            pH_sample = self.df_correl[self.df_correl['H2S Nr'] == s]['pH Nr'].to_numpy()[0]
            c = dbs._findCoreLabel(option1=self.Core, option2='core ' + str(self.Core),
                                   ls=self.df_correl['H2S code'].to_numpy())
            pH_core = self.df_correl[self.df_correl['H2S code'] == c]['pH code'].to_numpy()[0]
        self.pH_data = results['pH profile raw data'] if 'pH profile raw data' in results.keys() else None

        if 'H2S profile swi corrected pH' in results and self.pH_data:
            results = fh2s.swi_correctionpHII(results=results, pH_data=self.pH_data)
        df = fh2s.select_h2sDF_core(core=self.Core, results=results, dic_H2S=self.dic_H2S, rawPlot=self.rawPlot)[-1]
        _, self.ax1, self.scale = fh2s.plot_H2SUpdate(core=self.Core, nr=s, ddcore=df, results=results, pH=self.pH_data,
                                                      df_H2Ss=dcore_crop, pHnr=pH_sample, grp_label=grp_label,
                                                      pH_core=pH_core, ax=self.axH2Ss, fig=self.figH2Ss, ax1=self.ax1,
                                                      trimexact=False, scale=None)
        self.figH2Ss.canvas.draw()

        #  update range for pH plot and plot in main window
        if self.scale:
            self.H2Strim_edit.setText(str(round(self.scale[0], 2)) + ' - ' + str(round(self.scale[1], 2)))
        global dobj_hidH2S
        dic, df = fh2s.select_h2sDF_core(core=self.Core, results=results, dic_H2S=self.dic_H2S, rawPlot=True, main=True)
        dobj_hidH2S = fh2s.plot_H2SProfile(data_H2S=dic, core=self.Core, ls_core=self.dic_H2S.keys(), scale=None,
                                           fig=self.figH2S, ax=self.axH2S, col=self.colH2S, fs_=fs_, dunit=dunit,
                                           dobj_hidH2S=dobj_hidH2S, grp_label=grp_label, ls=self.ls)[-1]
        self.figH2S.canvas.draw()
        self.status_ph += 1

    def resetPlotH2S(self):
        global dobj_hidH2S, results
        self.swiSample_edit.setText('--')

        # get relevant parameter for plotting
        h2s_nr = min(self.dic_H2S[self.Core].keys(), key=lambda x: abs(x - self.slider1H2S.value()))
        pH_sample = self.df_correl[self.df_correl['H2S Nr'] == h2s_nr]['pH Nr'].to_numpy()[0]
        c = dbs._findCoreLabel(option1=self.Core, option2='core ' + str(self.Core),
                               ls=self.df_correl['H2S code'].to_numpy())
        pH_core = self.df_correl[self.df_correl['H2S code'] == c]['pH code'].to_numpy()[0]

        # re-set plot to raw data
        df = fh2s.select_h2sDF_core(core=self.Core, results=results, dic_H2S=self.dic_H2S, rawPlot=True, reset=True)[-1]
        fig, self.ax1, self.scale = fh2s.plot_adjustH2S(core=self.Core, sample=h2s_nr, col=self.colH2S, results=results,
                                                        dfCore=df, fig=self.figH2Ss, ax1=self.ax1, ax=self.axH2Ss,
                                                        pH=self.pH_data, pH_sample=pH_sample, pH_core=pH_core, ls='-.',
                                                        grp_label=grp_label, reset=True)
        self.figH2Ss.canvas.draw()

        # re-plot profiles in main window
        dic, df = fh2s.select_h2sDF_core(core=self.Core, results=results, dic_H2S=self.dic_H2S, rawPlot=True, main=True,
                                         reset=True)
        dobj_hidH2S = fh2s.plot_H2SProfile_sample(data_H2S=df, core=self.Core, sample=h2s_nr, fs_=fs_, col=self.colH2S,
                                                  grp_label=grp_label, dunit=dunit, ls=self.ls, dobj_hidH2S=dobj_hidH2S,
                                                  fig=self.figH2S, ax=self.axH2S)[-1]
        self.figH2S.canvas.draw()

        # re-set H2S adjusted for selected core/sample profile
        results['H2S adjusted'][self.Core][h2s_nr] = df[h2s_nr]

        # set the range for pH
        self.H2Strim_edit.setText(str(round(self.scale[0], 2)) + ' - ' + str(round(self.scale[1], 2)))
        self.rawPlot, self.ls, self.pH_status = True, '-.', 0

    def close_windowH2S(self):
        results['H2S adjusted'] = self.dic_H2S

        # update results for a intermediate H2S baseline set
        results['H2S profile interim'] = dict()
        for c in self.dic_H2S.keys():
            ddic = dict(map(lambda i: (i, pd.DataFrame(np.array(self.dic_H2S[c][i]), index=self.dic_H2S[c][i].index,
                                                       columns=self.dic_H2S[c][i].columns)), self.dic_H2S[c].keys()))
            results['H2S profile interim'][c] = ddic

        self.hide()


# ---------------------------------------------------------------------------------------------------------------------
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
        # define validator
        validator = QDoubleValidator(-9990, 9990, 4)
        validator.setLocale(QtCore.QLocale("en_US"))
        validator.setNotation(QDoubleValidator.StandardNotation)
        validator_pos = QDoubleValidator(0., 9990, 4)
        validator_pos.setLocale(QtCore.QLocale("en_US"))
        validator_pos.setNotation(QDoubleValidator.StandardNotation)

        # manual baseline correction
        swi_label, swi_unit_label = QLabel(self), QLabel(self)
        swi_label.setText('Actual correction: '), swi_unit_label.setText('µm')
        self.swi_edit = QLineEdit(self)
        self.swi_edit.setValidator(validator), self.swi_edit.setAlignment(Qt.AlignRight)
        self.swi_edit.setMaximumWidth(100), self.swi_edit.setText('--'), self.swi_edit.setEnabled(False)

        self.updateEP_button = QPushButton('Update SWI', self)
        self.updateEP_button.setFont(QFont(font_button, fs_font)), self.updateEP_button.setFixedWidth(100)
        self.updateEP_button.setEnabled(False)

        # user option to consider drift correction
        drift_label, self.driftEP_box = QLabel(self), QCheckBox('Yes, please', self)
        drift_label.setText('Drift correction')
        self.driftEP_box.setFont(QFont(font_button, fs_font))
        self.driftEP_box.setChecked(False)

        # Action button
        self.saveEP_button = QPushButton('Save', self)
        self.saveEP_button.setFixedWidth(100), self.saveEP_button.setFont(QFont(font_button, fs_font))
        self.continueEP_button = QPushButton('Plot', self)
        self.continueEP_button.setFixedWidth(100), self.continueEP_button.setFont(QFont(font_button, fs_font))
        self.adjustEP_button = QPushButton('Adjustments', self)
        self.adjustEP_button.setFixedWidth(100), self.adjustEP_button.setEnabled(False)
        self.adjustEP_button.setFont(QFont(font_button, fs_font))
        self.resetEP_button = QPushButton('Reset', self)
        self.resetEP_button.setFixedWidth(100), self.resetEP_button.setFont(QFont(font_button, fs_font))

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
        swiarea.setFont(QFont(font_button, fs_font)), swiarea.setMinimumHeight(120)
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
        self.figEP, self.axEP = plt.subplots()
        self.canvasEP = FigureCanvasQTAgg(self.figEP)
        self.axEP.set_xlabel('EP / mV', fontsize=fs_), self.axEP.set_ylabel('Depth / µm', fontsize=fs_)
        self.axEP.invert_yaxis()
        self.figEP.subplots_adjust(bottom=0.2, right=0.95, top=0.9, left=0.15)
        sns.despine()

        ep_group = QGroupBox("EP depth profile")
        ep_group.setMinimumHeight(420)
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

    def continue_EP(self):
        # update instruction
        self.setSubTitle("The measurement data are plotted below.  If you want to adjust the profiles, press the "
                         "Adjustment button.  If the drift correction shall be applied in the next step, press the "
                         "respective checkbox. \n")

        # load relevant global parameters
        global dunit, results, dcol_label, grp_label, scaleEP
        # store the unit (mV) in dunit
        dunit['EP'] = 'mV'

        # set status for process control and load data
        self.status_EP += 1
        [checked, results, grp_label, self.ls_core, self.dEP_core,
         self.ls_colname] = fep.load_EPdata(data=self.field("Data"), results=results, dcol_label=dcol_label,
                                            grp_label=grp_label)

        if checked is True:
            # adjust all the core plots to the same x-scale
            dfEP_scale = pd.concat([pd.DataFrame([(self.dEP_core[c][n]['EP_mV'].min(),
                                                   self.dEP_core[c][n]['EP_mV'].max())
                                                  for n in self.dEP_core[c].keys()]) for c in self.dEP_core.keys()])
            self.scale0 = dfEP_scale[0].min(), dfEP_scale[1].max()
            # use self.scale0 for the initial plot but make it possible to update self.scale
            self.scale = scaleEP[min(self.ls_core)] if min(self.ls_core) in scaleEP.keys() else self.scale0
            # plot the pH profile for the first core
            ls = '-.' if self.status_EP < 2 else '-'
            _ = fep.plot_initalProfile(data=self.dEP_core, para='EP', unit='mV', core=min(self.ls_core), ls=ls,
                                       ls_core=self.ls_core, col_name='EP_mV', dobj_hidEP=dobj_hidEP, ax=self.axEP,
                                       fig=self.figEP, grp_label=grp_label, scaleEP=scaleEP, fs_=fs_)

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
            global grp_label, scaleEP
            # allow only discrete values according to existing cores
            core_select = min(self.ls_core, key=lambda x: abs(x - self.sliderEP.value()))

            # update slider position and label
            self.sliderEP.setValue(int(core_select))
            self.sldEP_label.setText('{}: {}'.format(self.ls_colname[0], core_select))

            # update plot according to selected data set and core
            ls = '-.' if self.status_EP < 2 else '-'
            _ = fep.plot_initalProfile(data=results['EP adjusted'], para='EP', unit='mV', col_name='EP_mV', ls=ls,
                                       core=core_select, ls_core=self.ls_core, dobj_hidEP=dobj_hidEP, fig=self.figEP,
                                       ax=self.axEP, grp_label=grp_label, scaleEP=scaleEP, fs_=fs_)
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
                results['EP raw data'][core_select][s].index = ynew

        # add to results dictionary
        results['EP adjusted'] = data

        # plot the pH profile for the first core
        global grp_label, scaleEP
        ls = '-.' if self.status_EP < 2 else '-'
        _ = fep.plot_initalProfile(data=data, para='EP', unit='mV', core=core_select, ls_core=self.ls_core, ls=ls,
                                   col_name='EP_mV', dobj_hidEP=dobj_hidEP, fig=self.figEP, ax=self.axEP,
                                   grp_label=grp_label, scaleEP=scaleEP, fs_=fs_)

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
        self.continueEP_button.setEnabled(False), self.updateEP_button.setEnabled(False)

    def drift_correctionEP(self):
        # import meta-data info from excel file
        dsheets_add = fep.load_additionalInfo(data=self.field("Data"))

        if dsheets_add:
            # additional window for packaged drift correction
            self.driftCorr_EP(df_meta=dsheets_add['meta data'])
        else:
            msgBox = QMessageBox()
            msgBox.setIcon(QMessageBox.Information)
            msgBox.setText("No metadata sheet found.  Continue without EP drift correction.")
            msgBox.setFont(QFont(font_button, fs_font))
            msgBox.setWindowTitle("Warning")
            msgBox.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)

            returnValue = msgBox.exec()
            if returnValue == QMessageBox.Ok:
                pass

    def continue_EPIIb(self):
        global grp_label, scaleEP
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
        _ = fep.plot_initalProfile(data=self.data, para='EP', unit='mV', col_name='EP_mV', core=core_select, ls='-',
                                   ls_core=self.ls_core, dobj_hidEP=dobj_hidEP, fig=self.figEP, ax=self.axEP,
                                   grp_label=grp_label, scaleEP=scaleEP, fs_=fs_)
        self.figEP.canvas.draw()

        # slider initialized to first core
        self.sliderEP.setValue(int(core_select)), self.sldEP_label.setText('{}: {}'.format(self.ls_colname[0],
                                                                                           int(core_select)))

        # when slider value change (on click), return new value and update figure plot
        self.sliderEP.valueChanged.connect(self.sliderEP_update)

        # end of EP preparation
        self.continueEP_button.setEnabled(False), self.updateEP_button.setEnabled(False)

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

    def save_EP(self):
        global dout, results, ls_allData, dobj_hidEP, scaleEP, grp_label
        # preparation to save data
        dout = fep.prepDataEPoutput(dout=dout, results=results)

        # actual saving of data and figures
        fep.save_EPdata(path_save=self.field("Storage path"), save_params=self.field('saving parameters'), dout=dout,
                        data=self.field("Data"), ls_allData=ls_allData)
        fep.save_EPfigure(save_para=self.field('saving parameters'), ls_core=self.ls_core, grp_label=grp_label,
                          path_save=self.field("Storage path"), results=results, dobj_hidEP=dobj_hidEP, scaleEP=scaleEP)

        # Information that saving was successful
        msgBox = QMessageBox()
        msgBox.setIcon(QMessageBox.Information)
        msgBox.setText("Selected data are saved successfully.")
        msgBox.setFont(QFont(font_button, fs_font))
        msgBox.setWindowTitle("Successful")
        msgBox.setStandardButtons(QMessageBox.Ok)

        returnValue = msgBox.exec()
        if returnValue == QMessageBox.Ok:
            pass

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
        self.adjustEP_button.setEnabled(False), self.swi_edit.setEnabled(False), self.updateEP_button.setEnabled(False)

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
        global grp_label
        self.figEP, self.axEP, self.ddata, self.scale0, self.colEP = figEP, axEP, ddata, scale, col
        self.ls_core, self.status_EP = ls_core, status
        self.swiEP_edit = swiEP_edit
        self.ls = '-.' if self.status_EP <= 1.5 else '-'

        # return current core - and get the samples to plot (via slider selection)
        self.Core = min(self.ls_core, key=lambda x: abs(x - sliderValue))

        # plot all samples from current core
        ep_nr = min(self.ddata[self.Core].keys())

        # get pH data and in case apply depth correction in case it was done for H2S / total sulfide
        _ = fep.plot_adjustEP(core=self.Core, sample=ep_nr, col=self.colEP, dfCore=self.ddata[self.Core],
                              fig=self.figEPs, ax=self.axEPs, grp_label=grp_label)
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
        self.msg.setWordWrap(True), self.msg.setFont(QFont(font_button, fs_font))

        # Slider for different cores and label on the right
        self.slider1EP = QSlider(Qt.Horizontal)
        self.slider1EP.setMinimumWidth(350), self.slider1EP.setFixedHeight(20)
        self.sldEP1_label = QLabel()
        self.sldEP1_label.setFixedWidth(70), self.sldEP1_label.setText('sample: --')

        # plot individual sample
        self.figEPs, self.axEPs = plt.subplots(figsize=(3, 2), linewidth=0)
        self.figEPs.set_facecolor("none")
        self.canvasEPs = FigureCanvasQTAgg(self.figEPs)
        self.naviEPs = NavigationToolbar2QT(self.canvasEPs, self, coordinates=False)
        self.axEPs.set_xlabel('EP / mV'), self.axEPs.set_ylabel('Depth / µm')
        self.axEPs.invert_yaxis()
        self.figEPs.subplots_adjust(bottom=0.2, right=0.95, top=0.85, left=0.25)
        sns.despine()

        # define pH range
        EPtrim_label = QLabel(self)
        EPtrim_label.setText('EP range: '), EPtrim_label.setFont(QFont(font_button, fs_font))
        self.EPtrim_edit = QLineEdit(self)
        self.EPtrim_edit.setValidator(QRegExpValidator()), self.EPtrim_edit.setAlignment(Qt.AlignRight)
        self.EPtrim_edit.setMaximumHeight(int(fs_font*1.5))

        # define validator
        validator = QDoubleValidator(-9990, 9990, 4)
        validator.setLocale(QtCore.QLocale("en_US"))
        validator.setNotation(QDoubleValidator.StandardNotation)

        # swi correction for individual sample
        swiSample_label = QLabel(self)
        swiSample_label.setText('SWI correction sample: '), swiSample_label.setFont(QFont(font_button, fs_font))
        self.swiSample_edit = QLineEdit(self)
        self.swiSample_edit.setValidator(validator), self.swiSample_edit.setAlignment(Qt.AlignRight)
        self.swiSample_edit.setMaximumHeight(int(fs_font*1.5)), self.swiSample_edit.setText('--')

        # close the window again
        self.close_button = QPushButton('OK', self)
        self.close_button.setFixedWidth(100), self.close_button.setFont(QFont(font_button, fs_font))
        self.adjust_button = QPushButton('Adjust', self)
        self.adjust_button.setFixedWidth(100), self.adjust_button.setFont(QFont(font_button, fs_font))
        self.reset_button = QPushButton('Reset', self)
        self.reset_button.setFixedWidth(100), self.reset_button.setFont(QFont(font_button, fs_font))

        # create grid and groups
        mlayout2 = QVBoxLayout()
        vbox2_top, vbox2_bottom, vbox2_middle = QHBoxLayout(), QHBoxLayout(), QVBoxLayout()
        mlayout2.addLayout(vbox2_top), mlayout2.addLayout(vbox2_middle), mlayout2.addLayout(vbox2_bottom)

        # add items to the layout grid
        # top part
        MsgGp = QGroupBox()
        MsgGp.setFont(QFont(font_button, fs_font))
        gridMsg = QGridLayout()
        vbox2_top.addWidget(MsgGp)
        MsgGp.setLayout(gridMsg)

        # add GroupBox to layout and load buttons in GroupBox
        gridMsg.addWidget(self.msg, 1, 0)

        # in-between for sample plot
        plotGp = QGroupBox()
        plotGp.setFont(QFont(font_button, fs_font))
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
        naviGp.setFont(QFont(font_button, fs_font))
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
        global grp_label
        # clear lists for another trial
        self.ls_out, self.ls_cropy, ep_trim = list(), list(), self.EPtrim_edit.text()

        if len(ep_trim.split('-')) > 1:
            # assume that negative numbers occur
            ls = re.findall(r"[-+]?(?:\d*\.\d+|\d+)", ep_trim)
            self.scale = (float(ls[0]), float(ls[1]))
        else:
            self.scale = (float(ep_trim.split('-')[0]), float(ep_trim.split('-')[1].strip()))

        # allow only discrete values according to existing cores
        self.sample = min(self.ddata[self.Core].keys(), key=lambda x: abs(x - self.slider1EP.value()))

        # update slider position and label
        self.slider1EP.setValue(self.sample)
        self.sldEP1_label.setText('sample: {}'.format(self.sample))

        _ = fep.plot_adjustEP(core=self.Core, sample=self.sample, dfCore=self.ddata[self.Core], col=self.colEP,
                              fig=self.figEPs, ax=self.axEPs, grp_label=grp_label)
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

    def adjustEP(self):
        # check if the pH range (scale) changed
        self.updateEPscale()
        self.status_EP = 1

        # current sample
        self.sample = int(self.sldEP1_label.text().split(' ')[-1])

        # crop dataframe to selected range
        dcore_crop = fep.cropDF_EP(s=self.sample, ls_cropy=self.ls_cropy, ddata=self.ddata, Core=self.Core)
        # pop outliers from depth profile
        df_pop = fep.popData_EP(dcore_crop=dcore_crop, ls_out=self.ls_out) if self.ls_out else dcore_crop

        # check individual swi for sample
        try:
            int(self.swiSample_edit.text())
            # correction of manually selected baseline and store adjusted pH
            if self.swiSample_edit.text() != '':
                ynew = df_pop.index - float(self.swiSample_edit.text())
            else:
                ynew = df_pop.index
            df_pop = pd.DataFrame(df_pop.to_numpy(), index=ynew, columns=df_pop.columns)
            self.swiSample_edit.setText('--')
        except:
            try:
                float(self.swiSample_edit.text())
                # correction of manually selected baseline and store adjusted pH
                if self.swiSample_edit.text() != '':
                    ynew = df_pop.index - float(self.swiSample_edit.text())
                else:
                    ynew = df_pop.index
                df_pop = pd.DataFrame(df_pop.to_numpy(), index=ynew, columns=df_pop.columns)
                self.swiSample_edit.setText('--')
            except:
                pass

        # update the general dictionary
        global grp_label, scaleEP
        self.ddata[self.Core][self.sample] = df_pop
        _ = fep.plot_EPUpdate(core=self.Core, nr=self.sample, df=df_pop, ddcore=self.ddata[self.Core], col=self.colEP,
                              scale=self.scale, ax=self.axEPs, fig=self.figEPs, grp_label=grp_label)
        self.figEPs.canvas.draw()

        #  update range for pH plot and plot in main window
        self.EPtrim_edit.setText(str(round(self.scale[0], 2)) + ' - ' + str(round(self.scale[1], 2)))
        _ = fep.plot_initalProfile(data=self.ddata, para='EP', unit='mV', col_name='EP_mV', core=self.Core, ls=self.ls,
                                   ls_core=self.ddata.keys(), dobj_hidEP=dobj_hidEP, fig=self.figEP, ax=self.axEP,
                                   trimexact=True, grp_label=grp_label, scaleEP=scaleEP, fs_=fs_)
        self.figEP.canvas.draw()
        self.status_EP += 1

    def updateEPscale(self):
        ep_trim = self.EPtrim_edit.text()

        # get pH range form LineEdit
        if '-' in ep_trim:
            if len(ep_trim.split('-')) > 1:
                # assume that negative numbers occur
                ls = re.findall(r"[-+]?(?:\d*\.\d+|\d+)", ep_trim)
                scale = (float(ls[0]), float(ls[1]))
            else:
                scale = (float(ep_trim.split('-')[0]), float(ep_trim.split('-')[1].strip()))
        elif ',' in ep_trim:
            scale = (float(ep_trim.split(',')[0]), float(ep_trim.split(',')[1].strip()))
        else:
            scale = (float(ep_trim.split(' ')[0]), float(ep_trim.split(' ')[1].strip()))

        # if pH range was updated by the user -> update self.scale (prevent further down)
        if scale != self.scale:
            self.scale = scale

        # update global variable
        global scaleEP
        scaleEP[self.Core] = (round(self.scale[0], 2), round(self.scale[1], 2))

    def resetPlotEP(self):
        global grp_label, scaleEP, results
        _ = fep.plot_EPUpdate(core=self.Core, nr=self.sample, df=results['EP raw data'][self.Core][self.sample],
                              ddcore=self.ddata[self.Core], col=self.colEP, scale=self.scale, ax=self.axEPs,
                              fig=self.figEPs, grp_label=grp_label)
        self.figEPs.canvas.draw()

        #  update range for pH plot and plot in main window
        self.EPtrim_edit.setText(str(round(self.scale[0], 2)) + ' - ' + str(round(self.scale[1], 2)))
        _ = fep.plot_initalProfile(data=results['EP raw data'], para='EP', unit='mV', col_name='EP_mV', core=self.Core,
                                   ls=self.ls, ls_core=self.ddata.keys(), dobj_hidEP=dobj_hidEP, fig=self.figEP,
                                   ax=self.axEP, trimexact=True, grp_label=grp_label, scaleEP=scaleEP, fs_=fs_)
        self.figEP.canvas.draw()
        scaleEP = dict()

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
        self.dataDP[self.nP] = dbs._getProfileStack(nP=self.nP, dataEP=self.ddata, dorder=self.dorder)
        fig, self.axTD = fep.plot_profileTime(nP=self.nP, df_pack=self.dataDP[self.nP][1], resultsEP=self.ddata,
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
        self.figTD, self.axTD = plt.subplots(figsize=(7, 4), linewidth=0)
        self.figTD.set_facecolor("none")
        self.canvasTD = FigureCanvasQTAgg(self.figTD)
        self.axTD.set_xlabel('measurement points'), self.axTD.set_ylabel('EP / mV')
        self.figTD.subplots_adjust(bottom=0.2, right=0.95, top=0.85, left=0.15)
        sns.despine()

        # plot curve fit
        self.figCF, self.axCF = plt.subplots(figsize=(3, 2), linewidth=0) # width, height
        self.figCF.set_facecolor("none")
        self.canvasCF = FigureCanvasQTAgg(self.figCF)
        self.axCF.set_xlabel('profile number'), self.axCF.set_ylabel('average EP / mV')
        sns.despine()

        # drop-down menu for curve fit selection
        self.FitSelect_box = QComboBox(self)
        ls_Fit = ['2nd order polynomial fit', 'linear regression']
        self.FitSelect_box.addItems(ls_Fit), self.FitSelect_box.setEditable(False)

        # report section
        self.msg = QLabel("Details about the curve fit: \n\n\n\n")
        self.msg.setWordWrap(True), self.msg.setFont(QFont(font_button, fs_font))

        # close the window again
        self.closeDC_button = QPushButton('OK', self)
        self.closeDC_button.setFixedWidth(100), self.closeDC_button.setFont(QFont(font_button, fs_font))
        self.fit_button = QPushButton('Fit', self)
        self.fit_button.setFixedWidth(100), self.fit_button.setFont(QFont(font_button, fs_font))

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
        fig, self.axTD = fep.plot_profileTime(nP=self.nP, df_pack=self.dataDP[self.nP][1], resultsEP=self.ddata,
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
        fig, self.axTD = fep.plot_profileTime(nP=self.nP, df_pack=self.dataDP[self.nP][1], resultsEP=self.ddata,
                                              dorder=self.dorder, fig=self.figTD, ax=self.axTD)

        # drift correction
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
        self.figTD.canvas.draw()

        # plot fit results
        _ = fep.plot_Fit(df_reg=df_reg, ydata=ydata, figR=self.figCF, axR=self.axCF, show=True)
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
        global grp_label, scaleEP
        results['EP adjusted'] = self.dataDC
        results['EP profile drift'] = self.dataDP
        results['EP drift correction'] = self.dFit
        results['EP order'] = self.dorder

        for c in self.dataDC.keys():
            min_ = round(np.nanmin([self.dataDC[c][s]['EP_mV'].min() for s in self.dataDC[c].keys()]), 2)
            max_ = round(np.nanmax([self.dataDC[c][s]['EP_mV'].max() for s in self.dataDC[c].keys()]), 2)
            scaleEP[c] = (min_, max_)
        _ = fep.plot_initalProfile(data=self.dataDC, para='EP', unit='mV', core=self.Core, ls='-', col_name='EP_mV',
                                   ls_core=self.ls_core, dobj_hidEP=dobj_hidEP, ax=self.axEP, fig=self.figEP, fs_=fs_,
                                   trimexact=False, grp_label=grp_label, scaleEP=scaleEP)

        # update options what to do later on
        self.hide()


# ---------------------------------------------------------------------------------------------------------------------
class charPage(QWizardPage):
    def __init__(self, parent=None):
        super(charPage, self).__init__(parent)
        self.setTitle("Further sediment characterization")
        self.setSubTitle("On the next slide, you will first select which profiles shall be used for averaging for an "
                         "individual group,  e.g.  core. Then,  you can choose to plot different parameters together"
                         " in a joint plot. \n")

        # when all conditions are met, enable NEXT button
        self.ls_next = QLineEdit()

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
        self.update_btn.setFixedWidth(100), self.update_btn.setFont(QFont(font_button, fs_font))
        self.average_btn = QPushButton('Averaging', self)
        self.average_btn.setFixedWidth(100), self.average_btn.setFont(QFont(font_button, fs_font))
        self.clear_btn = QPushButton('Clear', self)
        self.clear_btn.setFixedWidth(100), self.clear_btn.setFont(QFont(font_button, fs_font))
        self.save_btn = QPushButton('Save', self)
        self.save_btn.setFixedWidth(100), self.save_btn.setFont(QFont(font_button, fs_font))

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

    def _fill_tabula(self, dcore, tabula_par):
        # get number of rows in table
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
        global results
        # actually fill current table with information
        if self.tabs_1.currentIndex() == 0:
            dcore = fj._getProfileLabels(para='O2', results=results)
            self.dcore['O2'] = dcore
            if dcore:
                self._fill_tabula(dcore=dcore, tabula_par=self.tabula_O2)
                self.tabula_O2.resizeColumnsToContents(), self.tabula_O2.resizeRowsToContents()
        elif self.tabs_1.currentIndex() == 1:
            dcore = fj._getProfileLabels(para='pH', results=results)
            self.dcore['pH'] = dcore
            if dcore:
                self._fill_tabula(dcore=dcore, tabula_par=self.tabula_pH)
                self.tabula_pH.resizeColumnsToContents(), self.tabula_pH.resizeRowsToContents()
        elif self.tabs_1.currentIndex() == 2:
            dcore = fj._getProfileLabels(para='H2S', results=results)
            self.dcore['H2S'] = dcore
            if dcore:
                self._fill_tabula(dcore=dcore, tabula_par=self.tabula_H2S)
                self.tabula_H2S.resizeColumnsToContents(), self.tabula_H2S.resizeRowsToContents()
        else:
            dcore = fj._getProfileLabels(para='EP', results=results)
            self.dcore['EP'] = dcore
            if dcore:
                self._fill_tabula(dcore=dcore, tabula_par=self.tabula_EP)
                self.tabula_EP.resizeColumnsToContents(), self.tabula_EP.resizeRowsToContents()

    def average_profiles(self):
        global dav, dunit, ls_para_global, results
        if self.tabs_1.currentIndex() == 0:
            # raw data -  'O2 raw data' | adjusted data - 'O2 profile'
            dav_o2 = fj.exeAverageProfileTab(tab=self.tabula_O2, results=results, searchK1='O2 profile',
                                             searchK2='O2 raw data')
            dav['O2'] = dav_o2
        if self.tabs_1.currentIndex() == 1:
            # raw data -  'pH profile raw data' | adjusted data - 'pH adjusted'
            dav_pH = fj.exeAverageProfileTab(tab=self.tabula_O2, results=results, searchK1='pH adjusted',
                                             searchK2='pH profile raw data')
            dav['pH'] = dav_pH
        if self.tabs_1.currentIndex() == 2:
            # raw data -  'H2S profile raw data' | adjusted data - 'H2S adjusted'
            dav_h2s = fj.exeAverageProfileTab(tab=self.tabula_O2, results=results, searchK1='H2S adjusted',
                                              searchK2='H2S profile raw data')
            dav['H2S'] = dav_h2s
        if self.tabs_1.currentIndex() == 3:
            # raw data -  'EP raw data' | adjusted data - 'EP adjusted'
            dav_ep = fj.exeAverageProfileTab(tab=self.tabula_O2, results=results, searchK1='EP adjusted',
                                             searchK2='EP raw data')
            dav['EP'] = dav_ep
        else:
            pass

        # return message to continue
        if ls_para_global[self.tabs_1.currentIndex()] in dunit.keys():
            msgBox = QMessageBox()
            msgBox.setIcon(QMessageBox.Information)
            msgBox.setText("Averaging successful!  Please continue to the tab or the next sheet and select the parameters "
                           "that shall be plotted together.")
            msgBox.setFont(QFont(font_button, fs_font))
            msgBox.setWindowTitle("Great job!")
            msgBox.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
            msgBox.exec()

    def save_avProfiles(self):
        global dav, dunit
        fj.save_avProfiles(save_path=self.field("Storage path"), data=self.field("Data"), dav=dav, dunit=dunit)

        # Information that saving was successful
        msgBox = QMessageBox()
        msgBox.setIcon(QMessageBox.Information)
        msgBox.setText("Selected data are saved successfully.")
        msgBox.setFont(QFont(font_button, fs_font))
        msgBox.setWindowTitle("Successful")
        msgBox.setStandardButtons(QMessageBox.Ok)

        returnValue = msgBox.exec()
        if returnValue == QMessageBox.Ok:
            pass

    def reset_tabula(self):
        global dav
        dav = dict()
        self.dcore = dict()
        if self.tabs_1.currentIndex() == 0:
            self.tabula_O2.setRowCount(1), self.tabula_O2.clearContents()
        elif self.tabs_1.currentIndex() == 1:
            self.tabula_pH.setRowCount(1), self.tabula_pH.clearContents()
        elif self.tabs_1.currentIndex() == 2:
            self.tabula_H2S.setRowCount(1), self.tabula_H2S.clearContents()
        else:
            self.tabula_EP.setRowCount(1), self.tabula_EP.clearContents()

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
        self.save_btn.clicked.connect(self.save_jointProfiles)

    def initUI(self):
        # checkbox for which parameters shall be plotted together
        self.o2_bx = QCheckBox('oxygen O2', self)
        self.ph_bx = QCheckBox('pH', self)
        self.h2s_bx = QCheckBox('total sulfide ΣS2- / H2S', self)
        self.ep_bx = QCheckBox('EP', self)
        self.h2s_bx.setMinimumWidth(170)
        self.o2_bx.setFont(QFont(font_button, fs_font)), self.ph_bx.setFont(QFont(font_button, fs_font)),
        self.h2s_bx.setFont(QFont(font_button, fs_font)), self.ep_bx.setFont(QFont(font_button, fs_font))

        # open additional window to classify which cores shall be plotted together
        self.spec_btn = QPushButton('Specify joint groups', self)
        self.spec_btn.setFixedWidth(150), self.spec_btn.setMinimumHeight(20)
        self.spec_btn.setFont(QFont(font_button, fs_font))
        self.plot_btn = QPushButton('Plot', self)
        self.plot_btn.setFixedWidth(100), self.plot_btn.setMinimumHeight(20)
        self.plot_btn.setFont(QFont(font_button, fs_font))
        self.adj_btn = QPushButton('Adjust', self)
        self.adj_btn.setFixedWidth(150), self.adj_btn.setMinimumHeight(20)
        self.adj_btn.setFont(QFont(font_button, fs_font))
        self.clear_btn = QPushButton('Clear', self)
        self.clear_btn.setFixedWidth(100), self.clear_btn.setMinimumHeight(20)
        self.clear_btn.setFont(QFont(font_button, fs_font))
        self.save_btn = QPushButton('Save', self)
        self.save_btn.setFixedWidth(100), self.save_btn.setMinimumHeight(20)
        self.save_btn.setFont(QFont(font_button, fs_font))

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
        btn_grp.setFont(QFont(font_button, fs_font)), btn_grp.setFixedHeight(75)
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
        self.figJ, self.axJ = plt.subplots(figsize=(3, 4), linewidth=0)
        self.axJ1 = self.axJ.twiny()
        self.canvasJ = FigureCanvasQTAgg(self.figJ)
        self.axJ.set_ylabel('Depth / µm', fontsize=fs_), self.axJ.set_xlabel('analyte', fontsize=fs_)
        self.axJ1.set_xlabel('analyte 2', fontsize=fs_)
        self.axJ.invert_yaxis()
        self.figJ.subplots_adjust(bottom=0.2, right=0.95, top=0.85, left=0.15)

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

    def specifyGroups(self):
        global dunit, dav
        # get the group labels of each selected parameter (maximum four parameters)
        [lsGrp1, lsGrp2, lsGrp3, lsGrp4, dunit,
         dav] = fj._getParaGroups(para_select=self.field('parameter selected'), ls_jPlot=self.ls_jPlot, dunit=dunit,
                                  data=self.field('Data'), dav=dav)

        # open new window and have a click collection for each profile of the first parameter
        global wSpecGp
        wSpecGp = specGroup(lsGrp1, lsGrp2, lsGrp3, lsGrp4, self.ls_jPlot)
        if wSpecGp.isVisible():
            pass
        else:
            wSpecGp.show()

    def adjust_profile(self):
        global wAdj_jP
        wAdj_jP = AdjustjPWindow(self.slider.value()-1, self.figJ, self.axJ, self.axJ1, self.ls_jPlot)
        if wAdj_jP.isVisible():
            pass
        else:
            wAdj_jP.show()

    def slider_update(self):
        global tabcorr, dcolor, dunit, fs_
        # allow only discrete values according to existing cores
        grp_select = min(np.arange(0, len(tabcorr.index)+1), key=lambda x: abs(x - self.slider.value()))

        # update slider position and label
        self.slider.setValue(int(grp_select))
        self.sld_label.setText('group: {}'.format(grp_select-1))

        # plot relevant core
        self._plot_joProfile1Core(sval=grp_select-1, run=2)
        if len(self.figJ.axes) == 4:
            dbs.layout4Axes(fs_=fs_, dcolor=dcolor, dunit=dunit, axJ2=self.figJ.axes[-2], axJ3=self.figJ.axes[-1],
                            para2=self.ls_jPlot[1], para3=self.ls_jPlot[0])
        elif len(self.figJ.axes) == 3:
            if self.ls_jPlot == ['EP', 'H2S', 'O2']:
                dbs.layout4Axes(fs_=fs_, dcolor=dcolor, dunit=dunit, axJ2=self.figJ.axes[-1], para2=self.ls_jPlot[1])
            else:
                dbs.layout4Axes(fs_=fs_, dcolor=dcolor, dunit=dunit, axJ2=self.figJ.axes[-1], para2=self.ls_jPlot[0])

        # adjust the framing
        dbs.adjust_axes(ls_jPlot=self.ls_jPlot, figProf=self.figJ)
        self.figJ.canvas.draw()

    def plot_joProfile(self):
        global tabcorr
        if isinstance(tabcorr, type(None)) is False:
            # slider initialized to first core
            self.slider.setMinimum(1), self.slider.setMaximum(int(len(tabcorr.index)))
            self.slider.setValue(1)
            self.sld_label.setText('group: {}'.format(1))

            # plot initial joint plot for group 0
            self._plot_joProfile1Core(sval=self.slider.value()-1, run=1)

            # when slider value change (on click), return new value and update figure plot
            self.slider.valueChanged.connect(self.slider_update)

            # in case the fit window is open -> update figFit according to selected sliderValue
            dbs.adjust_axes(ls_jPlot=self.ls_jPlot, figProf=self.figJ)
        else:
            msgBox = QMessageBox()
            msgBox.setIcon(QMessageBox.Information)
            msgBox.setText("No profile data specified.  Please,  select which core profiles shall be plotted together")
            msgBox.setFont(QFont(font_button, fs_font))
            msgBox.setWindowTitle("Warning")
            msgBox.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
            msgBox.exec()

    def _plot_joProfile1Core(self, sval, run):
        # clear all previous plots in figure
        [ax.cla() for ax in self.figJ.axes]
        self.axJ.invert_yaxis()

        # get the profiles and correlation matrix for the different parameters
        global tabcorr, dunit, dcolor
        # sorted parameters: EP, H2S, O2, pH
        self.ls_jPlot = sorted(list(dict.fromkeys(self.ls_jPlot)))

        # create a template of the figure including required additional axes
        dbs.templateFigure(figJ=self.figJ, axJ=self.axJ, axJ1=self.axJ1, run=run, fs_=fs_, dunit=dunit, dcolor=dcolor,
                           tabcorr=tabcorr)
        ls_axes = self.figJ.axes

        # fill the axes with averaged profiles
        for en, para in enumerate(self.ls_jPlot):
            # find correct position of parameter on coordinate system (separate function)
            pos = fj.find_para_position(en=en, para=para, ls_jPlot=self.ls_jPlot)

            self.sld_label.setText('group: {}'.format(sval+1))
            pkeys = tabcorr[para].to_numpy()
            colK = dbs._findCoreLabel(option1=pkeys[sval], option2='core {}'.format(pkeys[sval]),
                                      ls=list(dav[para].keys()))
            data = dav[para][colK]

            # exclude parameter from the index upon first adjustment
            if para in data.index:
                data = data.loc[:data.index[list(data.index).index(para) - 1]]
            ls_axes[pos].plot(data['mean'].values, data.index, lw=1.5, color=dcolor[para])
            ls_axes[pos].xaxis.label.set_color(dcolor[para]), ls_axes[pos].tick_params(axis='x', colors=dcolor[para])
            ls_axes[pos].axhline(0, color='k', lw=0.5)

            # make it a pretty layout
            if pos == 2:
                dbs.layout4Axes(fs_=fs_, dcolor=dcolor, dunit=dunit, axJ2=ls_axes[pos], para2=para)
            elif pos == 3:
                dbs.layout4Axes(fs_=fs_, dcolor=dcolor, dunit=dunit, axJ3=ls_axes[pos], para3=para)
        # make it a pretty plot
        self.axJ.invert_yaxis(), self.figJ.tight_layout()
        self.figJ.canvas.draw()

    def save_jointProfiles(self):
        # make a project folder for the specific analyte if it doesn't exist
        save_path = self.field("Storage path") + '/Graphs/additional/'
        if not os.path.exists(save_path):
            os.makedirs(save_path)

        # generate images of all all samples (don't plot them) and respective save_name
        global tabcorr, dav, dcolor, dunit
        ls_jPlot = list(dict.fromkeys(self.ls_jPlot))
        dfig = dict()
        for c in tabcorr.index:
            save_name = save_path + datetime.now().strftime("%Y%m%d-%H%M%S") + '_jointPlot_grp-' + str(c)
            dfig[save_name] = fj._plot_joProfile4save(sval=c, ls_jPlot=ls_jPlot, tabcorr=tabcorr, dav=dav, fs_=fs_,
                                                      dcolor=dcolor, dunit=dunit, show=False)

        # save figures
        for k in dfig.keys():
            [dfig[k].savefig(k + '.' + t, transparent=True, dpi=300) for t in ls_figtype]

        # Return information that saving was successful
        msgBox = QMessageBox()
        msgBox.setIcon(QMessageBox.Information)
        msgBox.setText("Saving completed successfully.")
        msgBox.setFont(QFont(font_button, fs_font))
        msgBox.setWindowTitle("Successful")
        msgBox.setStandardButtons(QMessageBox.Ok)

        returnValue = msgBox.exec()
        if returnValue == QMessageBox.Ok:
            pass

    def clear_profile(self):
        global tabcorr
        tabcorr = None

        # delete surplus subplots so that we actually have 2 again
        if len(self.figJ.axes) > 2:
            [self.figJ.delaxes(ax) for ax in self.figJ.axes[2:]]

        # clear all axes
        [ax.cla() for ax in self.figJ.axes]
        for ax in self.figJ.axes:
            [t.set_color('k') for t in ax.xaxis.get_ticklines()]
            [t.set_color('k') for t in ax.xaxis.get_ticklabels()]
            ax.tick_params(axis='x', colors='k')

        self.axJ.set_ylabel('Depth / µm')
        self.axJ.set_xlabel('analyte', color='k'), self.axJ1.set_xlabel('analyte 2', color='k')
        self.figJ.subplots_adjust(bottom=0.2, right=0.95, top=0.8, left=0.15)
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
        MsgGp.setFont(QFont(font_button, fs_font))
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
        NavGp.setFont(QFont(font_button, fs_font))
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

        # adjust table to its content
        tabula.resizeRowsToContents(), tabula.adjustSize()
        # adjust table header to its content
        header = tabula.horizontalHeader()
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)
        header.setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)
        header.setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QtWidgets.QHeaderView.Stretch)
        return tabula

    def clear(self):
        # clear the table
        self.tabCorr.clearContents()

    def close(self):
        # fill the dataframe
        tab_corr = pd.DataFrame(columns=['O2', 'pH', 'H2S', 'EP'], index=range(self.tabCorr.rowCount()))
        for i in range(self.tabCorr.rowCount()):
            for en, j in enumerate(tab_corr.columns):
                if self.tabCorr.cellWidget(i, en) is not None:
                    choice = self.tabCorr.cellWidget(i, en).currentText()
                else:
                    choice = '--'
                tab_corr.loc[i, j] = choice if choice == '--' else int(choice)
        # store dataframe in global variable
        global tabcorr
        tabcorr = tab_corr

        # close the window
        self.hide()


class AdjustjPWindow(QDialog):
    def __init__(self, group, figTab, axTab, axTab1, ls_jPlot):
        super().__init__()
        self.group, self.ls_cropy, self.data, self.para = group, list(), dict(), None
        self.figTab, self.axTab, self.axTab1, self.ls_jPlot = figTab, axTab, axTab1, ls_jPlot
        self.initUI()

        # connect checkbox and load file button with a function
        self.close_button.clicked.connect(self.close)
        self.show_button.clicked.connect(self.showPlots)
        self.adjust_button.clicked.connect(self.applyTrimming)

    def initUI(self):
        self.setWindowTitle("Adjust individual profiles")
        self.setGeometry(650, 50, 600, 650) # x-position, y-position, width, height

        # add description about how to use this window (slider, outlier detection, cropping area)
        self.msg = QLabel("Use the tab to switch between analytes belonging to the selected group. \nYou can trim the "
                          "data range: press CONTROL/COMMAND + select min/max or you can adjust the general depth shown"
                          "in the plot. \nAt the end,  update the plot by pressing the button UPDATE")
        self.msg.setWordWrap(True)

        self.close_button = QPushButton('Close', self)
        self.close_button.setFixedWidth(100)
        self.show_button = QPushButton('Show Data', self)
        self.show_button.setFixedWidth(100)
        self.adjust_button = QPushButton('Adjust Data', self)
        self.adjust_button.setFixedWidth(100)

        self.yrange_label, self.yrange_unit_label = QLabel(self), QLabel(self)
        self.yrange_label.setText('Depth range'), self.yrange_unit_label.setText('µm')
        self.yrange_edit = QLineEdit(self)
        validator = QRegExpValidator(QRegExp("[\-]?[0-9\.]{0,5}[\s?\-\,]{0,3}[0-9\.]{0,5}"))
        self.yrange_edit.setValidator(validator), self.yrange_edit.setAlignment(Qt.AlignRight)
        self.yrange_edit.setMaximumWidth(100), self.yrange_edit.setText('--')

        self.range_label, self.range_unit_label = QLabel(self), QLabel(self)
        self.range_label.setText('Analyte range'), self.range_unit_label.setText('µmol/L')
        self.range_edit = QLineEdit(self)
        validator = QRegExpValidator(QRegExp("[\-]?[0-9\.]{0,3}[\s?\-\,]{0,3}[0-9\.]{0,3}"))
        self.range_edit.setValidator(validator), self.range_edit.setAlignment(Qt.AlignRight)
        self.range_edit.setMaximumWidth(100), self.range_edit.setText('--')

        self.figT_O2, self.figT_pH = self.Figula(analyte='O2'), self.Figula(analyte='pH')
        self.figT_H2S, self.figT_EP = self.Figula(analyte='H2S'), self.Figula(analyte='EP')

        # creating window layout
        w = QWidget()
        mlayout2 = QVBoxLayout(w)
        vbox_top, vboxR, vbox, vbox_bottom = QHBoxLayout(), QVBoxLayout(), QVBoxLayout(), QHBoxLayout()
        mlayout2.addLayout(vbox_top), mlayout2.addLayout(vbox), mlayout2.addLayout(vboxR), mlayout2.addLayout(vbox_bottom)

        # table of core / available sample profiles and a column to select the profiles to be averaged
        self.tabs_1 = QTabWidget()
        self.tab1_1, self.tab2_1, self.tab3_1, self.tab4_1 = QWidget(), QWidget(), QWidget(), QWidget()

        # Add tabs
        self.tabs_1.addTab(self.tab1_1, "O2")
        self.tabs_1.addTab(self.tab2_1, "pH")
        self.tabs_1.addTab(self.tab3_1, "H2S/total sulfide ΣS2")
        self.tabs_1.addTab(self.tab4_1, "EP")

        # Add tabs to widget
        vbox_top.addWidget(self.tabs_1)
        # add tables to respective tab
        self.O2vbox = QVBoxLayout(self.tab1_1)
        self.O2vbox.addWidget(self.figT_O2[2])
        self.O2vbox.addWidget(self.figT_O2[3])
        self.pHvbox = QVBoxLayout(self.tab2_1)
        self.pHvbox.addWidget(self.figT_pH[2])
        self.pHvbox.addWidget(self.figT_pH[3])
        self.H2Svbox = QVBoxLayout(self.tab3_1)
        self.H2Svbox.addWidget(self.figT_H2S[2])
        self.H2Svbox.addWidget(self.figT_H2S[3])
        self.EPvbox = QVBoxLayout(self.tab4_1)
        self.EPvbox.addWidget(self.figT_EP[2])
        self.EPvbox.addWidget(self.figT_EP[3])

        # draw additional "line" to separate parameters from plots and to separate navigation from rest
        vline = QFrame()
        vline.setFrameShape(QFrame.HLine | QFrame.Raised)
        vline.setLineWidth(2)
        vbox.addWidget(vline)

        # add update button to the layout
        AdjGp, gridAdj = QGroupBox(), QGridLayout()
        vboxR.addWidget(AdjGp)
        AdjGp.setLayout(gridAdj)

        gridAdj.addWidget(self.range_label, 0, 0)
        gridAdj.addWidget(self.range_edit, 0, 1)
        gridAdj.addWidget(self.range_unit_label, 0, 2)
        gridAdj.addWidget(self.yrange_label, 1, 0)
        gridAdj.addWidget(self.yrange_edit, 1, 1)
        gridAdj.addWidget(self.yrange_unit_label, 1, 2)
        gridAdj.addWidget(self.show_button, 1, 3)
        gridAdj.addWidget(self.adjust_button, 1, 4)
        gridAdj.addWidget(self.close_button, 1, 5)

        self.setLayout(mlayout2)

    def Figula(self, analyte):
        if analyte in ['O2', 'H2S']:
            unit = 'µmol/L'
        elif analyte == 'pH':
            unit = ''
        else:
            unit = 'mV'

        fig, ax = plt.subplots(figsize=(3, 4), linewidth=0)
        canT = FigureCanvasQTAgg(fig)
        naviT = NavigationToolbar2QT(canT, self, coordinates=False)

        if analyte == 'pH':
            ax.set_ylabel('Depth / µm'), ax.set_xlabel('pH value')
        else:
            ax.set_ylabel('Depth / µm'), ax.set_xlabel('{} / {}'.format(analyte, unit))
        ax.invert_yaxis()
        sns.despine(), fig.subplots_adjust(bottom=0.2, right=0.95, top=0.95, left=0.15)
        return fig, ax, canT, naviT

    def update_xrange(self):
        # which parameter, which axes, which range
        if self.range_edit.text():
            sp = ', ' if ', ' in self.range_edit.text() else '- '
            ls_xrange = [float(x.strip()) for x in self.range_edit.text().split(sp)]

            # find the position of the parameter in the main plot (which axis?)
            ls_axes = self.figTab.axes
            dpos = dict()
            for p in enumerate(ls_axes):
                ls_keys = p[1].get_xlabel().split('/')[0].split(' ')
                for k in ls_keys:
                    if k in ['$O_2$', 'O2', 'pH', 'EP', 'H2S']:
                        k = 'O2' if k == '$O_2$' else k
                        dpos[k] = p[0]

            # adjust axes in main plot
            ls_axes[dpos[self.para]].set_xlim(ls_xrange[0], ls_xrange[1])
            self.figTab.canvas.draw()

            # update single parameter plot
            if self.tabs_1.currentIndex() == 0:
                self.figT_O2[1].set_xlim(ls_xrange[0], ls_xrange[1])
                self.figT_O2[0].canvas.draw()
            elif self.tabs_1.currentIndex() == 1:
                self.figT_pH[1].set_xlim(ls_xrange[0], ls_xrange[1])
                self.figT_pH[0].canvas.draw()
            elif self.tabs_1.currentIndex() == 2:
                self.figT_H2S[1].set_xlim(ls_xrange[0], ls_xrange[1])
                self.figT_H2S[0].canvas.draw()
            elif self.tabs_1.currentIndex() == 3:
                self.figT_EP[1].set_xlim(ls_xrange[0], ls_xrange[1])
                self.figT_EP[0].canvas.draw()

    def update_yrange(self):
        # which parameter, which axes, which range
        ls_yrange = None
        if self.yrange_edit.text():
            sp = ', ' if ', ' in self.yrange_edit.text() else '- '
            ls_yrange = sorted([float(x.strip()) for x in self.yrange_edit.text().split(sp)], reverse=True)

            # adjust axes in main plot
            self.axTab.set_ylim(ls_yrange[0], ls_yrange[1])
            self.figTab.canvas.draw()

            # update single parameter plot
            if self.tabs_1.currentIndex() == 0:
                self.figT_O2[1].set_ylim(ls_yrange[0], ls_yrange[1])
                self.figT_O2[0].canvas.draw()
            elif self.tabs_1.currentIndex() == 1:
                self.figT_pH[1].set_ylim(ls_yrange[0], ls_yrange[1])
                self.figT_pH[0].canvas.draw()
            elif self.tabs_1.currentIndex() == 2:
                self.figT_H2S[1].set_ylim(ls_yrange[0], ls_yrange[1])
                self.figT_H2S[0].canvas.draw()
            elif self.tabs_1.currentIndex() == 3:
                self.figT_EP[1].set_ylim(ls_yrange[0], ls_yrange[1])
                self.figT_EP[0].canvas.draw()

        return ls_yrange

    def showPlots(self):
        global tabcorr, dunit
        self.data, self.data_crp = dict(), dict()
        self.range_edit.clear(), self.yrange_edit.clear()

        id = self.group
        if self.tabs_1.currentIndex() == 0:
            if 'O2' in dunit.keys():
                # update analyte unit
                self.range_unit_label.setText(dunit['O2'])

                # plot respective curve for the given analyte in the actual group/core
                if '--' != tabcorr.loc[id, 'O2']:
                    data = dbs.findDataColumn(para='O2', df2check=dav['O2'][tabcorr.loc[id, 'O2']])
                    self.figT_O2[1].plot(data[data.columns[0]].values, data.index, lw=1.5, marker='o', fillstyle='none',
                                         ms=4, color=dcolor['O2'])
                self.figT_O2[1].axhline(0, color='k', lw=0.5)
                self.figT_O2[0].canvas.mpl_connect('button_press_event', self.onclick_trimming)
                self.figT_O2[0].canvas.draw()
        elif self.tabs_1.currentIndex() == 1:
            if 'pH' in dunit.keys():
                # update analyte unit
                self.range_unit_label.setText(dunit['pH'])

                # plot respective curve for the given analyte in the actual group/core
                if '--' != tabcorr.loc[id, 'pH']:
                    data = dbs.findDataColumn(para='pH', df2check=dav['pH'][tabcorr.loc[id, 'pH']])
                    self.figT_pH[1].plot(data[data.columns[0]].values, data.index, lw=1.5, marker='o', fillstyle='none',
                                         ms=4, color=dcolor['pH'])
                self.figT_pH[1].axhline(0, color='k', lw=0.5)
                self.figT_pH[0].canvas.mpl_connect('button_press_event', self.onclick_trimming)
                self.figT_pH[0].canvas.draw()
        elif self.tabs_1.currentIndex() == 2:
            if 'H2S' in dunit.keys() or 'total sulfide' in dunit.keys():
                # update analyte unit
                if 'total sulfide' in dunit.keys():
                    self.range_unit_label.setText(dunit['total sulfide'])
                else:
                    self.range_unit_label.setText(dunit['H2S'])

                # plot respective curve for the given analyte in the actual group/core
                if '--' != tabcorr.loc[id, 'H2S']:
                    data = dbs.findDataColumn(para='H2S', df2check=dav['H2S'], searchK=tabcorr.loc[id, 'H2S'])
                    self.figT_H2S[1].plot(data.values, data.index, lw=1.5, marker='o', fillstyle='none', ms=4,
                                          color=dcolor['H2S'])
                self.figT_H2S[1].axhline(0, color='k', lw=0.5)
                self.figT_H2S[0].canvas.mpl_connect('button_press_event', self.onclick_trimming)
                self.figT_H2S[0].canvas.draw()
        elif self.tabs_1.currentIndex() == 3:
            if 'EP' in dunit.keys():
                # update analyte unit
                self.range_unit_label.setText(dunit['EP'])

                # plot respective curve for the given analyte in the actual group/core
                if '--' != tabcorr.loc[id, 'EP']:
                    data = dbs.findDataColumn(para='EP', df2check=dav['EP'][tabcorr.loc[id, 'EP']])
                    self.figT_EP[1].plot(data[data.columns[0]].values, data.index, lw=1.5, marker='o', fillstyle='none',
                                         ms=4, color=dcolor['EP'])
                self.figT_EP[1].axhline(0, color='k', lw=0.5)
                self.figT_EP[0].canvas.mpl_connect('button_press_event', self.onclick_trimming)
                self.figT_EP[0].canvas.draw()

    def onclick_trimming(self, event):
        modifiers = QtWidgets.QApplication.keyboardModifiers()
        if modifiers == Qt.ControlModifier:
            # change selected range when control is pressed on keyboard
            # in case there are more than 2 points selected -> clear list and start over again
            if len(self.ls_cropy) >= 2:
                self.ls_cropy.clear()
            self.ls_cropy.append(event.ydata)

            # live trimming of actual data
            self.para = self.selectPara()
            data_, self.figProf, self.axProf, self.color = self.liveTrimming()
            self.data[self.para] = pd.DataFrame(data_)

            # mark the selected depth range in the single plot
            self._markHLine(df=self.data[self.para], figProf=self.figProf, axProf=self.axProf)

    def selectPara(self):
        if self.tabs_1.currentIndex() == 0:
            para = 'O2'
        elif self.tabs_1.currentIndex() == 1:
            para = 'pH'
        elif self.tabs_1.currentIndex() == 2:
            para = 'H2S'
        elif self.tabs_1.currentIndex() == 3:
            para = 'EP'
        else:
            para = None
        return para

    def liveTrimming(self):
        id = int(self.group)
        para = self.selectPara()
        # current group, current analyte
        if self.tabs_1.currentIndex() == 0:
            data = dbs.findDataColumn(para=para, df2check=dav['O2'][tabcorr.loc[id, 'O2']])
            figProf, axProf, color = self.figT_O2[0], self.figT_O2[1], ls_col[0]
        elif self.tabs_1.currentIndex() == 1:
            data = dbs.findDataColumn(para=para, df2check=dav['pH'][tabcorr.loc[id, 'pH']])
            figProf, axProf, color = self.figT_pH[0], self.figT_pH[1], ls_col[1]
        elif self.tabs_1.currentIndex() == 2:
            data = dbs.findDataColumn(para=para, df2check=dav['H2S'], searchK=tabcorr.loc[id, 'H2S'])
            figProf, axProf, color = self.figT_H2S[0], self.figT_H2S[1], ls_col[3]
        elif self.tabs_1.currentIndex() == 3:
            data = dbs.findDataColumn(para=para, df2check=dav['EP'][tabcorr.loc[id, 'EP']])
            figProf, axProf, color = self.figT_EP[0], self.figT_EP[1], ls_col[6]
        else:
            data, figProf, axProf, color = None, None, None, 'k'
        return data, figProf, axProf, color

    def applyTrimming(self):
        global dav, tabcorr, dunit
        # get the actual parameter to look at
        self.para = self.selectPara()
        if self.ls_cropy:
            # first option - select the depth range
            data_crop = self.cropDF(para=self.para, df=self.data[self.para])
            # update dictionary of raw data
            dav[self.para][tabcorr.loc[self.group, self.para]] = data_crop

            # second option - adjust the concentration range in the QLineEdit
            if isinstance(data_crop, type(None)) is False:
                # re-plot in the additional and the main window
                dbs.plot_ProfileUpdate(data=data_crop, color=dcolor[self.para], para=self.para, figProf=self.figProf,
                                       axProf=self.axProf, dunit=dunit)

                # re-plot main window
                dbs.plot_mainProfUpdate(sval=self.group, ls_jPlot=self.ls_jPlot, figProf=self.figTab, axJ=self.axTab,
                                        axJ1=self.figTab.axes[1], dav=dav, fs_=fs_, dcolor=dcolor, tabcorr=tabcorr,
                                        dunit=dunit)

                # after trimming / the adjust button has been pressed, reset the crop-y list
                self.ls_cropy.clear()

        # adjust the x_range for the individual parameter as well
        self.update_xrange()
        self.yrange = self.update_yrange()

    def _markHLine(self, df, figProf, axProf):
        # in case too many boundaries are selected, use the minimal/maximal values
        if len(self.ls_cropy) > 2:
            ls_crop = [min(self.ls_cropy), max(self.ls_cropy)]
        else:
            ls_crop = sorted(self.ls_cropy)

        ls_df = list()
        [ls_df.append(f) for f in df.index if isinstance(f, int) or isinstance(f, float)]

        # span grey area to mark outside range
        if len(ls_crop) == 1:
            sub = (ls_df[0] - ls_crop[0], ls_df[-1] - ls_crop[0])
            if np.abs(sub[0]) < np.abs(sub[1]):
                axProf.axhspan(ls_df[0], ls_crop[-1], color='gray', alpha=0.3)  # left outer side
            else:
                axProf.axhspan(ls_crop[-1], ls_df[-1], color='gray', alpha=0.3)  # right outer side
        else:
            if ls_crop[-1] < ls_crop[0]:
                axProf.axhspan(ls_df[0], ls_crop[-1], color='gray', alpha=0.3)  # left outer side
            else:
                axProf.axhspan(ls_crop[-1], ls_df[-1], color='gray', alpha=0.3)  # left outer side

        # draw vertical line to mark boundaries
        [axProf.axhline(x, color='k', ls='--', lw=0.5) for x in ls_crop]
        figProf.canvas.draw()

    def cropDF(self, para, df):
        if self.ls_cropy:
            # in case there was only 1 point selected -> extend the list to the other end
            if len(self.ls_cropy) == 1:
                sub = (df.index[0] - self.ls_cropy[0], df.index[-2] - self.ls_cropy[0])
                if np.abs(sub[0]) < np.abs(sub[1]):
                    self.ls_cropy = [self.ls_cropy[0], df.index[-2]]
                else:
                    self.ls_cropy = [df.index[0], self.ls_cropy[0]]
            # actually crop the depth profile to the area selected.
            # In case more than 2 points have been selected, choose the outer ones
            try:
                df_crop = df.loc[min(self.ls_cropy): max(self.ls_cropy)]
                self.data_crp[para] = df_crop
            except:
                df_crop = None
        else:
            df_crop = df
            self.data_crp[para] = df_crop[df_crop.columns[0]]
        return df_crop

    def close(self):
        global dyrange, dunit
        # adjust the y-range in the main window
        dbs.layoutMainFigure(fig=self.figTab, dyrange=dyrange, dunit=dunit)
        self.update_xrange()
        _ = self.update_yrange()

        dbs.adjust_axes(ls_jPlot=self.ls_jPlot, figProf=self.figTab)
        self.figTab.canvas.draw()

        # close the window
        self.hide()


# ---------------------------------------------------------------------------------------------------------------------
class FinalPage(QWizardPage):
    def __init__(self, parent=None):
        super(FinalPage, self).__init__(parent)
        self.setTitle("Final page")
        self.setSubTitle("Thanks for visiting  ·  Tak for besøget\n\nIf you have any questions regarding the "
                         "software or have encountered a bug,  please do not hesitate to contact me at "
                         "info@envipatable.com.\n\n")


# ---------------------------------------------------------------------------------------------------------------------
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
        self.msg.setWordWrap(True), self.msg.setFont(QFont(font_button, fs_font))

        # define validator
        validator = QDoubleValidator(-9990, 9990, 4)
        validator.setLocale(QtCore.QLocale("en_US"))
        validator.setNotation(QDoubleValidator.StandardNotation)
        validator_pos = QDoubleValidator(0., 9990, 4)
        validator_pos.setLocale(QtCore.QLocale("en_US"))
        validator_pos.setNotation(QDoubleValidator.StandardNotation)

        # input
        cnd_label, cnd_unit_label = QLabel(self), QLabel(self)
        cnd_label.setText('Conductivity: '), cnd_unit_label.setText('S/m')
        self.cnd_edit = QLineEdit(self)
        self.cnd_edit.setValidator(validator_pos), self.cnd_edit.setAlignment(Qt.AlignRight)
        self.cnd_edit.setMaximumWidth(100), self.cnd_edit.setText('')

        atm_label, atm_unit_label = QLabel(self), QLabel(self)
        atm_label.setText('Actual pressure: '), atm_unit_label.setText('bar')
        self.atm_edit = QLineEdit(self)
        self.atm_edit.setValidator(validator_pos), self.atm_edit.setAlignment(Qt.AlignRight)
        self.atm_edit.setMaximumWidth(100), self.atm_edit.setText('')

        temp_label, temp_unit_label = QLabel(self), QLabel(self)
        temp_label.setText('Temperature: '), temp_unit_label.setText('degC')
        self.temp_edit = QLineEdit(self)
        self.temp_edit.setValidator(validator), self.temp_edit.setAlignment(Qt.AlignRight)
        self.temp_edit.setMaximumWidth(100), self.temp_edit.setText(str(self.temp_degC.text()))

        sal_label, sal_unit_label = QLabel(self), QLabel(self)
        sal_label.setText('Salinity: '), sal_unit_label.setText('PSU')
        self.sal_edit = QLineEdit(self)
        self.sal_edit.setValidator(validator_pos), self.sal_edit.setAlignment(Qt.AlignRight)
        self.sal_edit.setMaximumWidth(100), self.sal_edit.setText('--'), self.sal_edit.setEnabled(False)

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
        MsgGp.setFont(QFont(font_button, fs_font))
        gridMsg = QGridLayout()
        vbox2_top.addWidget(MsgGp)
        MsgGp.setLayout(gridMsg)

        # add GroupBox to layout and load buttons in GroupBox
        gridMsg.addWidget(self.msg, 1, 0)

        # in-between for input parameter
        plotGp = QGroupBox("User input")
        plotGp.setFont(QFont(font_button, fs_font))
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
        naviGp.setFont(QFont(font_button, fs_font))
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
            salinity = sal.SalCon_Converter(temp_degC=float(self.temp_edit.text().strip()), M=0,
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


# ---------------------------------------------------------------------------------------------------------------------
if __name__ == '__main__':
    import sys

    app = QtWidgets.QApplication(sys.argv)
    path = os.path.join('/Users/au652733/Python/Project_CEMwizard/ready2buildApp/', 'Rootics.png')
    app.setWindowIcon(QIcon(path))
    app.setStyle('QtCurve') # options: 'Breeze', 'Oxygen', 'QtCurve', 'Windows', 'Fusion'
    app.setStyleSheet("QLineEdit { qproperty-frame: false }")

    Wizard = MagicWizard()
    # screen Size adjustment
    screen = app.primaryScreen()
    rect = screen.availableGeometry()
    Wizard.setMaximumHeight(int(rect.height() * 0.9))
    #Wizard.move(int(rect.width()*0.1), int(rect.height()*0.1))

    # show wizard
    Wizard.show()
    sys.exit(app.exec_())

#%