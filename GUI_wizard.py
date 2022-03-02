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
import qtawesome as qta
from PyQt5.QtWidgets import (QCheckBox, QComboBox, QFileDialog, QFrame, QGridLayout, QGroupBox, QHBoxLayout, QLabel,
                             QLineEdit, QDialog, QMessageBox, QPushButton, QSlider, QVBoxLayout, QWidget, QWizard,
                             QWizardPage, QInputDialog)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import *
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT, FigureCanvasQTAgg
import numpy as np
import seaborn as sns
import pandas as pd
from lmfit import Model
import os
import re

import functions_dbs as dbs
import function_salinity as sal

# global parameter
lim, lim_min, steps = 150, -1, 0.5
convC2K = 273.15                    # temperature conversion from degC into Kelvin
gof_accept = 10.                    # acceptable goodness of fit to result to reasonable depth profiles (SWI correction)
gof_top = 3.                        # excellent goodness of fit to result to reasonable depth profiles (SWI correction)
ls_allData = ['meta data', 'raw data', 'fit_mV', 'SWIcorrected mV', 'O2 profile', 'penetration depth']

# color list for samples: grey, orange, petrol, green, yellow, light grey, blue
ls_col = list(['#4c5558', '#eb9032', '#21a0a8', '#9ec759', '#f9d220', '#96a6ab', '#1B08AA'])
ls_figtype = ['png']
dpi = 300
fs_font = 10

# plot style / layout
sns.set_context('paper'), sns.set_style('ticks')

# global variables
dobj_hid, dpen_glob, dO2_core, results, dout = dict(), dict(), dict(), dict(), dict()
scalepH, scaleh2s, scaleEP = list(), list(), list()

# wizard architecture - how are the pages arranged?
wizard_page_index = {"IntroPage": 0, "o2Page": 1, "phPage": 2, "h2sPage": 3, "epPage": 4, "charPage": 5}


# !!! TODO: clean hidden code and unnecessary functions
# !!! TODO: make smaller functions and store them in library py file - checked: intro, o2
# !!! TODO: clean warnings marked by pycharm
# !!! TODO: write the guideline - update the subtitle accordingly and avoid the "black box" image
# !!! TODO: all plot with maximal lim
# !!! TODO: make the layout / fontsize of text, buttons,... all the same
# !!! TODO: combine similar functions / plots of different projects

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
        # set start page
        self.setStartId(wizard_page_index["IntroPage"])

        # GUI layout
        self.setWindowTitle("Guide through the forest")
        self.setGeometry(50, 50, 500, 300)

        # define Wizard style and certain options
        self.setWizardStyle(QWizard.MacStyle)
        self.setOptions(QtWidgets.QWizard.NoCancelButtonOnLastPage | QtWidgets.QWizard.HaveFinishButtonOnEarlyPages)
        # !!!TODO: enable logo in Subtitle
        # logo_image = QImage('Figure4icon.png')
        # self.setPixmap(QWizard.LogoPixmap, QPixmap.fromImage(logo_image))

        # add a background image
        path = os.path.join('/Users/au652733/Python/Project_CEMwizard/Pictures', 'leaves3.png')
        pixmap = QtGui.QPixmap(path)
        pixmap = pixmap.scaled(500, 500, QtCore.Qt.KeepAspectRatio)
        self.setPixmap(QWizard.BackgroundPixmap, pixmap)


class IntroPage(QWizardPage):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle("InfoPage")
        self.setSubTitle("Please provide the path to your measurement file and select which of the parameters should "
                         "be analyzed.\nWe will then guide you through the analysis.\n")

        # create layout
        self.initUI()

        # connect checkbox and load file button with a function
        self.load_button.clicked.connect(self.load_data)
        self.OutPut_box.stateChanged.connect(self.softwareFile)
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
        self.h2s_box = QCheckBox('total sulfide / H2S', self)
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
        self.OutPut_box = QCheckBox('output file', self)

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
        self.ls_saveOp.setText(','.join(['meta data', 'raw data', 'fit_mV', 'SWIcorrected mV', 'O2 profile',
                                         'penetration depth']))

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
        grid_file.addWidget(self.OutPut_box, 0, 2)
        grid_file.addWidget(self.save_button, 1, 0)
        grid_file.addWidget(self.inputSaveLineEdit, 1, 1)
        grid_file.addWidget(self.set_button, 2, 0)
        self.setLayout(mlayout)

    def load_data(self):
        fname, filter = QFileDialog.getOpenFileName(self, "Select specific excel file for measurement analysis",
                                                    "Text files (*.xls *.csv *xlsx)")
        self.fname.setText(fname)
        if fname:
            self.inputFileLineEdit.setText(fname)
            self.fname.setText(fname)

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

    def softwareFile(self):
        self.OutPut.setText(str(self.OutPut_box.isChecked()))

    def total_sulfide(self):
        if self.h2s_box.isChecked() is True:
            self.ph_box.setChecked(True)

    def pH_check(self):
        if self.h2s_box.isChecked() is True and self.ph_box.isChecked() is False:
            msgBox = QMessageBox()
            msgBox.setIcon(QMessageBox.Information)
            msgBox.setText("Total sulfide can only be calculated, when the pH is provided as well. Otherwise you will "
                           "only get the H2S concentration.")
            msgBox.setFont(QFont('Helvetica Neue', 11))
            msgBox.setWindowTitle("Warning")
            msgBox.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)

            returnValue = msgBox.exec()
            if returnValue == QMessageBox.Ok:
                pass

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
        self.ls_saveOp = ls_saveOp
        self.initUI()

        # when checkbox selected, save information in registered field
        self.meta_box.stateChanged.connect(self.saveoption_selected)
        self.rdata_box.stateChanged.connect(self.saveoption_selected)
        self.fit_box.stateChanged.connect(self.saveoption_selected)
        self.swi_box.stateChanged.connect(self.saveoption_selected)
        self.profile_box.stateChanged.connect(self.saveoption_selected)
        self.pen_box.stateChanged.connect(self.saveoption_selected)
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
        self.meta_box = QCheckBox('meta data', self)
        self.meta_box.setChecked(True)
        self.rdata_box = QCheckBox('raw data', self)
        self.rdata_box.setChecked(True)
        self.fit_box = QCheckBox('fit data', self)
        self.fit_box.setChecked(True)
        self.swi_box = QCheckBox('SWI corrected data', self)
        self.swi_box.setChecked(True)
        self.profile_box = QCheckBox('O2 profile corrected', self)
        self.profile_box.setChecked(True)
        self.pen_box = QCheckBox('Penetration depth', self)
        self.pen_box.setChecked(True)

        self.swiF_box = QCheckBox('SWI corrected plot', self)
        self.swiF_box.setChecked(False)
        self.fitF_box = QCheckBox('Fit plot', self)
        self.fitF_box.setChecked(False)
        self.penF_box = QCheckBox('Penetration depth figure', self)
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
        grid_data.addWidget(self.swi_box, 3, 0)
        grid_data.addWidget(self.profile_box, 4, 0)
        grid_data.addWidget(self.pen_box, 5, 0)

        fig_settings = QGroupBox("Figures")
        grid_fig = QGridLayout()
        fig_settings.setFont(QFont('Helvetica Neue', 12))
        vbox2_middle.addWidget(fig_settings)
        fig_settings.setLayout(grid_fig)

        # include widgets in the layout
        grid_fig.addWidget(self.swiF_box, 0, 0)
        grid_fig.addWidget(self.fitF_box, 1, 0)
        grid_fig.addWidget(self.penF_box, 2, 0)

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
        if self.swi_box.isChecked() is True:
            ls_setSave.append('SWIcorrected mV')
        if self.profile_box.isChecked() is True:
            ls_setSave.append('O2 profile')
        if self.pen_box.isChecked() is True:
            ls_setSave.append('penetration depth')
        # figures
        if self.swiF_box.isChecked() is True:
            ls_setSave.append('fig swi')
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
                         " \nTo start the analysis, press CONTINUE.")

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
        self.temperature_edit.setText('13.2')

        salinity_label, salinity_unit_label = QLabel(self), QLabel(self)
        salinity_label.setText('Salinity'), salinity_unit_label.setText('PSU')
        self.salinity_edit = QLineEdit(self)
        self.salinity_edit.setValidator(QDoubleValidator()), self.salinity_edit.setAlignment(Qt.AlignRight)
        self.salinity_edit.setText('0.')

        pene2_label, pene2_unit_label = QLabel(self), QLabel(self)
        pene2_label.setText('Sensor LoD'), pene2_unit_label.setText('µmol/l')
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
        self.sld_label.setFixedWidth(50)
        self.sld_label.setText('core: --')

        # creating window layout
        w1 = QWidget()
        mlayout1 = QVBoxLayout(w1)
        vbox1_left, vbox1_middle, vbox1_right = QHBoxLayout(), QHBoxLayout(), QHBoxLayout()
        mlayout1.addLayout(vbox1_left), mlayout1.addLayout(vbox1_middle), mlayout1.addLayout(vbox1_right)

        para_settings = QGroupBox("Input for O2 analysis")
        grid_load = QGridLayout()
        para_settings.setFont(QFont('Helvetica Neue', 12))
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
        O2_group.setMinimumWidth(300), O2_group.setMinimumHeight(400)
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
            self.sld_label.setText('core: {}'.format(value))

    def reset_o2page(self):

        if self.count != 0:
            self.setSubTitle("Start all over again. New attempt, new chances. \nLoad calibration, update parameters if "
                             "required, and press CONTINUE.")

            # reset count and reset slider and continue button / status
            self.count = 0
            self.slider.setValue(int(min(self.ls_core)))
            self.sld_label.setText('core: --')
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

    def conductivity_converterO2(self):
        # open dialog window for conductivity -> salinity conversion
        global wConv
        wConv = SalConvWindowO2(float(self.temperature_edit.text()), self.salinity_edit)
        if wConv.isVisible():
            pass
        else:
            wConv.show()

    def pre_check_calibration(self):
        # minimal dissolved O2 is assumed to be 0%air
        self.o2_dis = dbs.dissolvedO2_calc(T=float(self.temperature_edit.text()),
                                           salinity=float(self.salinity_edit.text()))

    def User4Calibration(self, ):
        userCal = QMessageBox.question(self, 'Calibration', 'Shall we use the calibration from the measurement file?'
                                                            '\nIf not,  the sensor will be recalibrated based on the '
                                                            'given temperature & salinity.',
                                       QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)

        if userCal == QMessageBox.Yes:
            # define for output metadata
            self.typeCalib = 'internal calibration from measurement file'

            # calibration from excel file
            dO2_core.update(dbs.O2rearrange(df=self.ddata_shift[self.ls_colname[1]], unit='µmol/l'))
            results['O2 profile'] = dO2_core

            # continue with the process - first execute without any click
            self.continue_processII()
            # update process that shall be executed when button is clicked
            self.continue_button.disconnect()
            self.continue_button.clicked.connect(self.continue_processII)

        elif userCal == QMessageBox.No:
            msgBox1 = QMessageBox()
            msgBox1.setIcon(QMessageBox.Question)
            msgBox1.setFont(QFont('Helvetica Neue', 11))
            msgBox1.setWindowTitle('Recalibration')
            msgBox1.setText('Shall we do the calibration core by core or should we apply one calibration to all '
                            'samples?')
            msgBox1.addButton('core by core', msgBox1.ActionRole)
            msgBox1.addButton('apply to all', msgBox1.ActionRole)

            ret = msgBox1.exec()

            global lim, lim_min
            if ret == 0:
                # define for output metadata
                self.typeCalib = 'recalibration core by core'

                # calibration core by core
                dO2_core.update(dbs.O2converter4conc(data_shift=self.ddata_shift[self.ls_colname[-1]], lim_min=lim_min,
                                                     lim=lim, o2_dis=self.o2_dis, unit='µmol/l'))
                results['O2 profile'] = dO2_core

                # continue with the process - first execute without any click
                self.continue_processII()
                # update process that shall be executed when button is clicked
                self.continue_button.disconnect()
                self.continue_button.clicked.connect(self.continue_processII)
            else:
                # calibration of one core applied to all others -> select core
                text, ok = QInputDialog.getText(self, 'Core selection',
                                                'Select core that shall be used for recalibration:')
                if ok is True:
                    try:
                        if int(text) in self.ls_core:
                            # possible responses include either "core" or only the number -> find pattern with re
                            dO2_core.update(dbs.O2calc4conc_one4all(core_sel=int(text), lim_min=lim_min, lim=lim,
                                                                    o2_dis=self.o2_dis, unit='µmol/l',
                                                                    data_shift=self.ddata_shift[self.ls_colname[-1]]))
                            results['O2 profile'] = dO2_core
                        else:
                            # calibration of one core applied to all others -> select core
                            text, ok = QInputDialog.getText(self, 'Core selection', 'Select EXISTING core that shall'
                                                                                    ' be used for recalibration:')
                            if ok is True:
                                # possible responses include either "core" or only the number -> find pattern with re
                                dO2_core.update(dbs.O2calc4conc_one4all(core_sel=int(text), lim_min=lim_min, lim=lim,
                                                                        o2_dis=self.o2_dis, unit='µmol/l',
                                                                        data_shift=self.ddata_shift[self.ls_colname[-1]]))
                                results['O2 profile'] = dO2_core

                        # define for output metadata
                        self.typeCalib = 'recalibration one core ' + text + ' to all'

                        # continue with the process - first execute without any click
                        self.continue_processII()
                        self.continue_button.disconnect()
                        self.continue_button.clicked.connect(self.continue_processII)
                    except:
                        # calibration of one core applied to all others -> select core
                        QInputDialog.getText(self, 'Core selection', 'Select EXISTING core that shall be used for '
                                                                     'recalibration:')

    def load_O2data(self):
        # load excel sheet with all measurements
        if self.field("SoftwareFile") == 'True':
            # raw measurement file pre-processed and saved per default as rawData file
            dsheets = dbs._loadFile4GUI(file=self.field("Data"))
        else:
            # old version with pre-processed files:
            dsheets = pd.read_excel(self.field("Data"), sheet_name=None)

        # pre-check whether O2_all in sheet names
        sheet_select = dbs.sheetname_check(dsheets, para='O2')

        # !!! TODO: field("SoftwareFile") might be depreciated in the future
        #  prepare file depending on the type
        if self.field("SoftwareFile") == 'True':
            ddata = dsheets[sheet_select]
        else:
            ddata = dsheets[sheet_select].set_index('Nr')

        return ddata, sheet_select

    def sigmoidalFit(self, ddata, sheet_select):
        # pre-set of parameters
        gmod = Model(dbs._gompertz_curve)

        # ----------------------------------------------------------------------------------
        # list all available cores for O2 sheet
        ls_core = list(dict.fromkeys(ddata['Core'].to_numpy()))

        # import all measurements for given parameter
        [dic_dcore, ls_nr,
         ls_colname] = dbs.load_measurements(dsheets=ddata, ls_core=ls_core, para=sheet_select)
        results['O2 raw data'] = dic_dcore

        # curve fit and baseline finder
        dfit, dic_deriv = dbs.fit_baseline(ls_core=ls_core, ls_nr=ls_nr, dic_dcore=dic_dcore, steps=steps, gmod=gmod)
        results['O2 fit'], results['O2 derivative'] = dfit, dic_deriv

        return ls_core, ls_colname, gmod, dic_dcore, dic_deriv, dfit

    def baselineShift(self):
        self.ddata_shift = dict()
        for c in self.ls_colname[1:]:
            data_shift = dbs.baseline_shift(dic_dcore=self.dic_dcore, dic_deriv=self.dic_deriv, column=c)
            self.ddata_shift[c] = data_shift
        results['O2 SWI corrected'] = self.ddata_shift

        # plot baseline corrected depth profiles
        fig0 = dbs.GUI_baslineShift(data_shift=self.ddata_shift[self.ls_colname[-1]], core=min(self.ls_core),
                                    ls_core=self.ls_core, fig=self.figO2, ax=self.axO2)

        # slider initialized to first core
        self.slider.setMinimum(int(min(self.ls_core))), self.slider.setMaximum(int(max(self.ls_core)))
        self.slider.setValue(int(min(self.ls_core)))
        self.sld_label.setText('core: {}'.format(int(min(self.ls_core))))

        # when slider value change (on click), return new value and update figure plot
        self.slider.valueChanged.connect(self.slider_update)

        # in case the FitWindow is open -> update figFit according to selected sliderValue
        self.slider.sliderReleased.connect(self.wFit_update)
        self.figO2.canvas.draw()

    def continue_process(self):
        # store relevant information
        results['temperature degC'] = float(self.temperature_edit.text())
        results['salinity PSU'] = float(self.salinity_edit.text())

        if self.count == 0:
            # determine min/max dissolved O2 according to set temperature and salinity
            self.pre_check_calibration()

            # update subtitle for progress report
            self.setSubTitle("Analysis starts with the correction of the surface-water interface (SWI).  If the "
                             "correction looks good,  press CONTINUE.  Otherwise,  press CHECK FIT for adjustments.")
            # load data from excel sheet depending on the type (measurement file or prepared file)
            ddata, sheet_select = self.load_O2data()

            # sigmoidal fit
            [self.ls_core, self.ls_colname, self.gmod, self.dic_dcore,
             self.dic_deriv, self.dfit] = self.sigmoidalFit(ddata=ddata, sheet_select=sheet_select)

            # baseline shift
            self.baselineShift()

            # enable button to click and investigate the derivative / fit
            self.checkFit_button.setEnabled(True)
            self.checkFit_button.clicked.connect(self.checkFitWindow)

            # enable next step in O2 analysis
            self.count += 1

        elif self.count == 1:
            # update subtitle for progress report
            self.setSubTitle("Depth correction (SWE) done.  Continue with calibration.")

            # get user input on calibration - convert O2 potential into concentration
            self.User4Calibration()

    def continue_processII(self):
        if self.count == 1:
            # determine penetration depth according to given O2 concentration
            self.O2_penetration = float(self.pene2_edit.text())
            [self.dcore_pen,
             dcore_fig] = GUI_calcO2penetration(unit='µmol/l', steps=steps, gmod=self.gmod,
                                                O2_pen=float(self.pene2_edit.text()))
            results['O2 penetration depth'] = self.dcore_pen

            # update subtitle for progress report
            self.setSubTitle(" For each core,  select all samples to be considered for calculation of the average "
                             "penetration depth. Then press CONTINUE.\n")

            # slider initialized to first core
            self.slider.setValue(int(min(self.ls_core)))
            self.sld_label.setText('core: {}'.format(int(min(self.ls_core))))

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
             dcore_fig] = GUI_calcO2penetration(unit='µmol/l', steps=steps, O2_pen=float(self.pene2_edit.text()),
                                                gmod=self.gmod)

        # slider initialized to first core
        self.slider.setValue(int(min(self.ls_core)))
        self.sld_label.setText('core: {}'.format(int(min(self.ls_core))))

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
                wFit = FitWindow(core_select, self.count, self.ls_core, self.dic_dcore, self.dfit, self.dic_deriv,
                                 self.ddata_shift[self.ls_colname[-1]], self.figO2, self.axO2)
            except:
                pass

    def slider_update(self):
        if self.ls_core:
            # allow only discrete values according to existing cores
            core_select = min(self.ls_core, key=lambda x: abs(x - self.slider.value()))

            # update slider position and label
            self.slider.setValue(int(core_select))
            self.sld_label.setText('core: {}'.format(core_select))

            # update plot according to selected core
            fig0 = dbs.GUI_baslineShift(data_shift=self.ddata_shift[self.ls_colname[-1]], core=core_select,
                                        ls_core=self.ls_core, fig=self.figO2, ax=self.axO2)
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
            self.sld_label.setText('core: {}'.format(core_select))

            # update plot according to selected core
            fig1 = GUI_O2depth(core=core_select, ls_core=self.ls_core, dcore_pen=self.dcore_pen, dobj_hid=dobj_hid,
                               ax=self.axO2, fig=self.figO2)
            self.figO2.canvas.draw()

    def slider_update2(self):
        # allow only discrete values according to existing cores
        core_select = min(self.ls_core, key=lambda x: abs(x - self.slider.value()))

        # update slider position and label
        self.slider.setValue(int(core_select))
        self.sld_label.setText('core: {}'.format(core_select))

        # update plot according to selected core
        fig2, mean_ = GUI_penetration_av(core=core_select, ls_core=self.ls_core, dcore_pen=self.dcore_pen,
                                         fig=self.figO2, ax=self.axO2)
        self.figO2.canvas.draw()

    def checkFitWindow(self):
        global wFit
        wFit = FitWindow(self.slider.value(), self.count, self.ls_core, self.dic_dcore, self.dfit, self.dic_deriv,
                         self.ddata_shift[self.ls_colname[-1]], self.figO2, self.axO2)
        if wFit.isVisible():
            pass
        else:
            wFit.show()

    def save_data(self):
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
            dbs.save_rawExcel(dout=dout, file=self.field("Data"), savePath=self.field("Storage path"))

    def save_figdepth(self, save_path, dfigBase):
        if not os.path.exists(save_path + 'DepthProfile/'):
            os.makedirs(save_path + 'DepthProfile/')
        for f in dfigBase.keys():
            for t in ls_figtype:
                name = save_path + 'DepthProfile/' + 'Depthprofile_core-{}_SWI_corrected.'.format(f) + t
                dfigBase[f].savefig(name, bbox_inches='tight', pad_inches=0.1, dpi=dpi)

    def save_figFit(self, save_path, dfigFit):
        if not os.path.exists(save_path + 'Fit/'):
            os.makedirs(save_path + 'Fit/')

        for f in dfigFit.keys():
            for ff in dfigFit[f].keys():
                for t in ls_figtype:
                    name = save_path + 'Fit/' + 'Fit_core-{}_sample-{}.'.format(f, ff) + t
                    dfigFit[f][ff].savefig(name, bbox_inches='tight', pad_inches=0.1, dpi=dpi)

    def save_figPen(self, save_path, dfigPen):
        if not os.path.exists(save_path + 'PenetrationDepth/'):
            os.makedirs(save_path + 'PenetrationDepth/')
        for f in dfigPen.keys():
            for t in ls_figtype:
                name = save_path + 'PenetrationDepth/' + 'PenetrationDepth_core-{}.'.format(f) + t
                dfigPen[f].savefig(name, bbox_inches='tight', pad_inches=0.1, dpi=dpi)

    def save_figure(self):
        ls_saveFig = list()
        [ls_saveFig.append(i) for i in self.field('saving parameters').split(',') if 'fig' in i]

        if len(ls_saveFig) > 0:
            save_path = self.field("Storage path") + '/Graphs/'

            # make folder "Graphs" if it doesn't exist
            if not os.path.exists(save_path):
                os.makedirs(save_path)

            # generate images of all all samples (don't plot them)
            [dfigBase, dfigFit,
             dfigPen] = figures4saving(ls_core=self.ls_core, ddcore=self.dic_dcore, deriv=self.dic_deriv,
                                       ddata_shift=self.ddata_shift[self.ls_colname[-1]], dfit=self.dfit,
                                       dcore_pen=self.dcore_pen)

            # Depth profiles
            if 'fig swi' in ls_saveFig:
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
        global dout
        # preparation - make own function out at the end
        dout = dbs.prep4saveRes(dout=dout, results=results, typeCalib=self.typeCalib, o2_dis=self.o2_dis,
                                temperature=float(self.temperature_edit.text()), pene2=float(self.pene2_edit.text()),
                                salinity=float(self.salinity_edit.text()))

        # extract saving options for data / figures - according to user input
        self.save_data()
        self.save_figure()

        # Information that saving was successful
        msgBox = QMessageBox()
        msgBox.setIcon(QMessageBox.Information)
        msgBox.setText("Required information are saved successfully.")
        msgBox.setFont(QFont('Helvetica Neue', 11))
        msgBox.setWindowTitle("Successful")
        msgBox.setStandardButtons(QMessageBox.Ok)

        returnValue = msgBox.exec()
        if returnValue == QMessageBox.Ok:
            pass

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

        # return current core - and get the samples to plot (via slider selection)
        self.Core = min(ls_core, key=lambda x: abs(x - sliderValue))

        # get the transmitted data
        self.dShift, self.figO2, self.axO2 = data_shift, figO2, axO2
        self.dfCore, self.FitCore, self.DerivCore = dfCore[self.Core], dfFit[self.Core], dfDeriv[self.Core]

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
        self.save1_button.clicked.connect(self.save_fit)
        self.close_button.clicked.connect(self.close_window)

    def initUI(self):
        self.setWindowTitle("Check fit for depth correction")
        self.setGeometry(650, 180, 600, 400)

        # add description about how to use this window (slider, outlier detection, cropping area)
        self.msg = QLabel("Use the slider to switch between samples belonging to the selected core. \nYou have the "
                          "following options to improve the fit: \n- Trim fit range: press CONTROL/COMMAND + select "
                          "min/max \n- Remove outliers: press SHIFT + select individual points \n\nAt the end, update"
                          " the fit by pressing the button UPDATE FIT")

        self.msg.setWordWrap(True)

        self.close_button = QPushButton('Fit OK', self)
        self.close_button.setFixedWidth(100)
        self.update_button = QPushButton('update fit', self)
        self.update_button.setFixedWidth(100)
        self.save1_button = QPushButton('Save', self)
        self.save1_button.setFixedWidth(100)

        # Slider for different cores and label on the right
        self.slider1 = QSlider(Qt.Horizontal)
        self.slider1.setMinimumWidth(350), self.slider1.setFixedHeight(20)
        self.sld1_label = QLabel()
        self.sld1_label.setFixedWidth(70)
        self.sld1_label.setText('sample: --')

        self.chi2_bx = QLabel(self)
        self.chi2_bx.setFixedWidth(100)
        self.chi2 = QLabel()
        self.chi2.setText('Goodness of fit (reduced χ2): --')
        self.chi2.setAlignment(Qt.AlignLeft)
        self.pixmapP = QPixmap(qta.icon('fa5.laugh').pixmap(QtCore.QSize(16, 16)))
        self.pixmapG = QPixmap(qta.icon('fa5.meh-blank').pixmap(QtCore.QSize(16, 16)))
        self.pixmapB = QPixmap(qta.icon('fa5.frown').pixmap(QtCore.QSize(16, 16)))
        self.chi2_bx.setPixmap(self.pixmapG)
        self.chi2_bx.setAlignment(Qt.AlignRight)

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
        self.axFit.set_xlabel('Depth / µm'), self.axFit.set_ylabel('O2 / mV')
        self.ax1Fit.set_ylabel('1st derivative', color='#0077b6')

        self.axFit.invert_yaxis()
        self.figFit.subplots_adjust(bottom=0.2, right=0.95, top=0.9, left=0.15)
        sns.despine()

        # add items to the layout grid
        # top part
        MsgGp = QGroupBox()
        MsgGp.setFont(QFont('Helvetica Neue', 12))
        MsgGp.setMinimumWidth(300)
        gridMsg = QGridLayout()
        vbox2_top.addWidget(MsgGp)
        MsgGp.setLayout(gridMsg)

        # add GroupBox to layout and load buttons in GroupBox
        gridMsg.addWidget(self.msg, 1, 0)

        # in-between for chi-2
        ChiGp = QGroupBox()
        ChiGp.setFont(QFont('Helvetica Neue', 12))
        ChiGp.setMinimumWidth(300)
        gridChi = QGridLayout()
        vbox2_middle.addWidget(ChiGp)
        ChiGp.setLayout(gridChi)

        # add GroupBox to layout and load buttons in GroupBox
        gridChi.addWidget(self.chi2_bx, 1, 0)
        gridChi.addWidget(self.chi2, 1, 1)

        # middle part
        FitGp = QGroupBox("Sigmoidal fit and 1st derivative")
        FitGp.setFont(QFont('Helvetica Neue', 12))
        FitGp.setMinimumWidth(300), FitGp.setMinimumHeight(400)
        gridFit = QGridLayout()
        vbox2_middle1.addWidget(FitGp)
        FitGp.setLayout(gridFit)

        # add GroupBox to layout and load buttons in GroupBox
        gridFit.addWidget(self.slider1, 1, 0)
        gridFit.addWidget(self.sld1_label, 1, 1)
        gridFit.addWidget(self.canvasFit, 2, 0)

        # bottom part
        BtnGp = QGroupBox()
        BtnGp.setMinimumWidth(300), BtnGp.setFixedHeight(45)
        gridBtn = QGridLayout()
        vbox2_bottom.addWidget(BtnGp)
        vbox2_bottom.setAlignment(self, Qt.AlignLeft | Qt.AlignTop)
        BtnGp.setLayout(gridBtn)
        gridBtn.addWidget(self.close_button, 1, 0)
        gridBtn.addWidget(self.update_button, 1, 1)
        gridBtn.addWidget(self.save1_button, 1, 2)

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

    def cropDF(self, s):
        if self.ls_cropx:
            # in case there was only 1 point selected -> extend the list to the other end
            if len(self.ls_cropx) == 1:
                sub = (self.dfCore[s].index[0] - self.ls_cropx[0], self.dfCore[s].index[-1] - self.ls_cropx[0])
                if np.abs(sub[0]) < np.abs(sub[1]):
                    self.ls_cropx = [self.ls_cropx[0], self.dfCore[s].index[-1]]
                else:
                    self.ls_cropx = [self.dfCore[s].index[0], self.ls_cropx[0]]

            # actually crop the depth profile to the area selected.
            # In case more than 2 points have been selected, choose the outer ones
            dcore_crop = self.dfCore[s].loc[min(self.ls_cropx): max(self.ls_cropx)]
        else:
            dcore_crop = self.dfCore[s]
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
        gmod = Model(dbs._gompertz_curve)
        res, df_fit_crop, df_fitder = dbs.baseline_finder_DF(dic_dcore=dcore_crop, steps=steps, model=gmod)

        # update red.chi2
        if round(res.redchi, 3) > gof_accept:
            self.chi2_bx.setPixmap(self.pixmapB)
        elif gof_top < round(res.redchi, 3) < gof_accept:
            self.chi2_bx.setPixmap(self.pixmapG)
        else:
            self.chi2_bx.setPixmap(self.pixmapP)
        self.chi2.setText('Goodness of fit (reduced χ2): ' + str(round(res.redchi, 3)))
        return df_fit_crop, df_fitder

    def updateFit(self):
        # current core, current sample
        c, s = self.Core, int(self.sld1_label.text().split(' ')[-1])

        # crop dataframe to selected range
        dcore_crop = self.cropDF(s=s)

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
        self.dShift[c][s] = pd.DataFrame(dcore_crop['O2_mV'].values, dcore_crop.index - df_fitder.idxmin().values[0])

        # plot baseline corrected depth profiles
        fig0 = dbs.GUI_baslineShiftCore(data_shift=self.dShift[c], core_select=self.Core, fig=self.figO2, ax=self.axO2)
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
        if round(self.FitCore[int(sample_select)][0].redchi, 3) > gof_accept:
            self.chi2_bx.setPixmap(self.pixmapB)
        elif gof_top < round(self.FitCore[int(sample_select)][0].redchi, 3) < gof_accept:
            self.chi2_bx.setPixmap(self.pixmapG)
        else:
            self.chi2_bx.setPixmap(self.pixmapP)
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


def figures4saving(ls_core, ddata_shift=None, ddcore=None, dfit=None, deriv=None, dcore_pen=None):
    dfigBase, dfigFit, dfigPen = dict(), dict(), dict()
    for c in ls_core:
        # SWI corrected
        if ddata_shift:
            dfigBase[c] = dbs.GUI_baslineShift(show=False, data_shift=ddata_shift, core=c, ls_core=ls_core)

        # Fit plots
        dfigFitS = dict()
        if ddcore:
            for s in ddcore[c].keys():
                dfigFitS[s] = GUI_FitDepth(core=c, nr=s, dfCore=ddcore[c], dfFit=dfit[c], dfDeriv=deriv[c], show=False)
            dfigFit[c] = dfigFitS

        # indicated penetration depth
        if dcore_pen:
            dfigPen[c] = GUI_penetration_av(core=c, ls_core=ls_core, dcore_pen=dcore_pen, show=False)[0]
    return dfigBase, dfigFit, dfigPen


def plot_Fitselect(core, sample, dfCore, dfFit, dfDeriv, fig, ax, ax1):
    # initialize first plot with first core and sample
    fig3 = GUI_FitDepth(core=core, nr=sample, dfCore=dfCore, dfFit=dfFit, dfDeriv=dfDeriv, fig=fig, ax=ax, ax1=ax1)
    fig3.canvas.draw()
    return fig3


def plot_FitUpdate(core, nr, dic_dcore, dfit, dic_deriv, fig, ax, ax1):
    # clear coordinate system but keep the labels
    ax.cla(), ax1.cla()
    ax.title.set_text('Fit characteristics for core {} - sample {}'.format(core, nr))
    ax.set_xlabel('Depth / µm'), ax.set_ylabel('O2 / mV'), ax1.set_ylabel('1st derivative', color='#0077b6')

    # plotting part
    ax.plot(dic_dcore.index, dic_dcore['O2_mV'], lw=0, marker='o', ms=4, color='k')
    ax.plot(dfit[dfit.columns[0]], lw=0.75, ls=':', color='k')

    ax1.plot(dic_deriv, lw=1., color='#0077b6')
    ax1.axvline(dic_deriv.idxmin().values[0], ls='-.', color='darkorange', lw=1.5)

    # text annotation to indicate depth correction
    text = 'surface level \nat {:.1f}µm'
    ax.text(dic_dcore['O2_mV'].index[0] * 0.95, dic_dcore['O2_mV'].max() * 0.15,
            text.format(dic_deriv.idxmin().values[0]), ha="left", va="center", color='k', size=9.5,
            bbox=dict(fc='lightgrey', alpha=0.25))

    # general layout
    sns.despine()
    ax.spines['right'].set_visible(True)
    plt.tight_layout()
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
        ax.title.set_text('Fit characteristics for core {} - sample {}'.format(core, nr))
        ax.set_xlabel('Depth / µm'), ax.set_ylabel('O2 / mV'), ax1.set_ylabel('1st derivative', color='#0077b6')

    # plotting part
    ax.plot(dfCore[nr].index, dfCore[nr]['O2_mV'], lw=0, marker='o', ms=4, color='k')
    ax.plot(dfFit[nr][1], lw=0.75, ls=':', color='k')
    ax1.plot(dfDeriv[nr], lw=1., color='#0077b6')
    ax1.axvline(dfDeriv[nr].idxmin().values[0], ls='-.', color='darkorange', lw=1.5)

    # text annotation for sediment water interface depth correction
    text = 'surface level \nat {:.1f}µm'
    ax.text(dfCore[nr]['O2_mV'].index[0] * 0.95, dfCore[nr]['O2_mV'].max() * 0.15,
            text.format(dfDeriv[nr].idxmin().values[0]), ha="left", va="center", color='k', size=9.5,
            bbox=dict(fc='lightgrey', alpha=0.25))

    # general layout
    ax.set_xlim(dfCore[nr].index[0]*1.05, dfCore[nr].index[-1]*1.05)
    sns.despine()
    ax.spines['right'].set_visible(True), plt.tight_layout()

    if show is False:
        plt.close(fig)
    else:
        fig.canvas.draw()
    return fig


def GUI_O2depth(core, ls_core, dcore_pen, dobj_hid, fig, ax):
    ax.cla()
    lines = list()
    # identify closest value in list
    core_select = closest_core(ls_core=ls_core, core=core)

    # initialize figure plot
    if ax is None:
        fig, ax = plt.subplots(figsize=(3, 4))
    if core_select != 0:
        ax.title.set_text('Fit depth profile for core {}'.format(core_select))
    ax.set_xlabel('O2 concentration / µmol/l'), ax.set_ylabel('Depth / µm')
    ax.invert_yaxis()

    if core_select != 0:
        ax.axhline(0, lw=.5, color='k')
    if core_select != 0:
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
        leg = ax.legend(frameon=True, fancybox=True)

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


def closest_core(ls_core, core):
    if core == 0 or not ls_core:
        core_select = 0
    else:
        core_select = min(ls_core, key=lambda x: abs(x - core))
    return core_select


def GUI_calcO2penetration(O2_pen, unit, steps, gmod):
    dcore_pen, dcore_fig = dict(), dict()
    for core in dO2_core.keys():
        dic_pen, dfig_pen = dict(), dict()
        for s in dO2_core[core].keys():
            df_fit = dbs.penetration_depth(df=dO2_core[core][s[0]].dropna(), O2_pen=O2_pen, unit=unit, steps=steps,
                                           model=gmod)
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
        dfpen_core.loc['mean'], dfpen_core.loc['std'] = dfpen_core.mean(), dfpen_core.std()
        dpenetration[core] = dfpen_core

    dpen_glob.update(pd.concat(dpenetration, axis=0))

    return dcore_pen, dcore_fig


def av_penetrationDepth(core_select, ls_remain):
    mean_ = (dpen_glob['Depth / µm'].loc[core_select].loc[ls_remain].mean(),
             dpen_glob['O2_µmol/l'].loc[core_select].loc[ls_remain].mean())
    std_ = (dpen_glob['Depth / µm'].loc[core_select].loc[ls_remain].std(),
            dpen_glob['O2_µmol/l'].loc[core_select].loc[ls_remain].std())

    # update dpen_glob
    dpen_glob['Depth / µm'].loc[core_select].loc['mean'] = mean_[0]
    dpen_glob['O2_µmol/l'].loc[core_select].loc['mean'] = mean_[1]
    dpen_glob['Depth / µm'].loc[core_select].loc['std'] = std_[0]
    dpen_glob['O2_µmol/l'].loc[core_select].loc['std'] = std_[1]
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
    core_select = closest_core(ls_core=ls_core, core=core)

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
        ax.legend(frameon=True, fancybox=True)

        # indicate penetration depth mean + std according to visible curves
        mean_, std_ = av_penetrationDepth(core_select=core_select, ls_remain=ls_remain)
        ax.axhline(mean_[0], ls=':', color='crimson')
        ax.fill_betweenx([mean_[0] - std_[0], mean_[0] + std_[0]], -50, 500, lw=0, alpha=0.5, color='grey')
        ax.axvline(mean_[1], ls=':', color='crimson')
        ax.fill_between([mean_[1] - std_[1], mean_[1] + std_[1]], -5000, 5000, lw=0, alpha=0.5, color='grey')

        # layout
        ax.set_xlim(-10, df.max().max() * 1.05), ax.set_ylim(df.idxmin().max() * 1.05, df.idxmax().min() * 1.05)
        ax.set_ylabel('Depth / µm'), ax.set_xlabel('O2 concentration ' + 'µmol/l')

        # include mean depth in title
        if core_select == 0 or not dcore_pen:
            pass
        else:
            ax.title.set_text('Average penetration depth for core {}: {:.0f} ± {:.0f}µm'.format(core_select, mean_[0],
                                                                                                std_[0]))
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
                         "\nIt can be adjusted later.  Press PLOT to start.")
        self.initUI()

        # connect checkbox and load file button with a function
        self.continuepH_button.clicked.connect(self.continue_pH)
        self.adjustpH_button.clicked.connect(self.adjust_pH)
        self.savepH_button.clicked.connect(self.save_pH)
        self.resetpH_button.clicked.connect(self.reset_pHpage)
        self.swipH_box.stateChanged.connect(self.enablePlot_swiBox)

    def initUI(self):
        # manual baseline correction
        swi_label, swi_unit_label = QLabel(self), QLabel(self)
        swi_label.setText('Actual correction: '), swi_unit_label.setText('µm')
        self.swi_edit = QLineEdit(self)
        self.swi_edit.setValidator(QDoubleValidator()), self.swi_edit.setAlignment(Qt.AlignRight)
        self.swi_edit.setMaximumWidth(100), self.swi_edit.setText('--'), self.swi_edit.setEnabled(False)

        # option to select the SWI (baseline) from the O2 calculations in case O2 was selected
        self.swipH_box = QCheckBox('SWI from O2 analysis', self)
        self.swipH_box.setFont(QFont('Helvetica Neue', fs_font))
        self.swipH_box.setVisible(True), self.swipH_box.setEnabled(False)

        # Action button
        self.savepH_button = QPushButton('Save', self)
        self.savepH_button.setFixedWidth(100), self.savepH_button.setFont(QFont('Helvetica Neue', fs_font))
        self.continuepH_button = QPushButton('Plot', self)
        self.continuepH_button.setFixedWidth(100), self.continuepH_button.setFont(QFont('Helvetica Neue', fs_font))
        self.adjustpH_button = QPushButton('Adjustments', self)
        self.adjustpH_button.setFixedWidth(100), self.adjustpH_button.setEnabled(False)
        self.adjustpH_button.setFont(QFont('Helvetica Neue', fs_font))
        self.resetpH_button = QPushButton('Reset', self)
        self.resetpH_button.setFixedWidth(100), self.resetpH_button.setFont(QFont('Helvetica Neue', fs_font))

        # Slider for different cores and label on the right
        self.sliderpH = QSlider(Qt.Horizontal)
        self.sliderpH.setMinimumWidth(350), self.sliderpH.setFixedHeight(20)
        self.sldpH_label = QLabel()
        self.sldpH_label.setFixedWidth(50)
        self.sldpH_label.setText('core: --')

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
        grid_swi.addWidget(self.swipH_box, 0, 3)
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
        self.figpH, self.axpH = plt.subplots(figsize=(5, 3))
        self.canvaspH = FigureCanvasQTAgg(self.figpH)
        self.axpH.set_xlabel('pH value'), self.axpH.set_ylabel('Depth / µm')
        self.axpH.invert_yaxis()
        self.figpH.tight_layout(pad=1.5)
        sns.despine()

        pH_group = QGroupBox("pH depth profile")
        pH_group.setMinimumWidth(350), pH_group.setMinimumHeight(400)
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
        if self.field("SoftwareFile") == 'True':
            dsheets = dbs._loadFile4GUI(file=self.field("Data"))
        else:
            # old version with pre-processed files:
            dsheets = pd.read_excel(self.field("Data"), sheet_name=None)

        # pre-check whether pH_all in sheet names
        sheet_select = dbs.sheetname_check(dsheets, para='pH')

        # !!! TODO: field("SoftwareFile") might be depreciated in the future
        #  prepare file depending on the type
        if self.field("SoftwareFile") == 'True':
            ddata = dsheets[sheet_select]
        else:
            ddata = dsheets[sheet_select].set_index('Nr')

        # list all available cores for pH sheet
        self.ls_core = list(dict.fromkeys(ddata['Core'].to_numpy()))

        # import all measurements for given parameter
        [self.dpH_core, ls_nr,
         self.ls_colname] = dbs.load_measurements(dsheets=ddata, ls_core=self.ls_core, para=sheet_select)
        results['pH raw data'] = self.dpH_core

    def continue_pH(self):
        # set status for process control
        self.status_pH = 0

        # update layout
        self.swipH_box.setEnabled(True) if self.field("SWI pH as o2") == 'True' else self.swipH_box.setEnabled(False)
        self.swi_edit.setEnabled(True)

        # load data
        self.load_pHdata()

        # ----------------------------------------------------------------------------------
        # adjust all the core plots to the same x-scale
        dfpH_scale = pd.concat([pd.DataFrame([(self.dpH_core[c][n]['pH'].min(), self.dpH_core[c][n]['pH'].max())
                                              for n in self.dpH_core[c].keys()]) for c in self.dpH_core.keys()])
        self.scale0 = dfpH_scale[0].min(), dfpH_scale[1].max()
        # use self.scale0 for the initial plot but make it possible to update self.scale
        self.scale = self.scale0

        # plot the pH profile for the first core
        figpH0 = plot_pHProfile(data_pH=self.dpH_core, core=min(self.ls_core), ls_core=self.ls_core, scale=self.scale0,
                                fig=self.figpH, ax=self.axpH)

        # slider initialized to first core
        self.sliderpH.setMinimum(int(min(self.ls_core))), self.sliderpH.setMaximum(int(max(self.ls_core)))
        self.sliderpH.setValue(int(min(self.ls_core)))
        self.sldpH_label.setText('core: {}'.format(int(min(self.ls_core))))

        # when slider value change (on click), return new value and update figure plot
        self.sliderpH.valueChanged.connect(self.sliderpH_update)

        # update continue button to "update" in case the swi shall be updated
        self.adjustpH_button.setEnabled(True)
        self.continuepH_button.disconnect()
        self.continuepH_button.clicked.connect(self.continue_pHII)

        # set options for swi correction
        if 'O2 penetration depth' not in results.keys():
            self.swipH_box.setEnabled(False)

    def continue_pHII(self):
        # update status for process control
        self.status_pH += 1

        # identify closest value in list
        core_select = closest_core(ls_core=self.ls_core, core=self.sliderpH.value())

        # check whether a (manual) swi correction is required. SWI correction only for current core
        self.swi_correctionpH()

        # plot the pH profile for the first core
        scale_plot = self.scale0 if len(scalepH) == 0 else scalepH
        figpH0 = plot_pHProfile(data_pH=self.dpH_core, core=core_select, ls_core=self.ls_core, scale=scale_plot,
                                ls='-', fig=self.figpH, ax=self.axpH)
        self.figpH.canvas.draw()

        # slider initialized to first core
        self.sliderpH.setValue(int(core_select)), self.sldpH_label.setText('core: {}'.format(int(core_select)))

        # when slider value change (on click), return new value and update figure plot
        self.sliderpH.valueChanged.connect(self.sliderpH_update)

        # store adjusted pH
        results['pH swi adjusted'] = self.dpH_core

    def swi_correctionpH(self):
        # identify closest value in list
        core_select = min(self.ls_core, key=lambda x: abs(x - self.sliderpH.value()))

        if self.swipH_box.checkState() == 0:
            self.continuepH_button.setEnabled(True)

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
                for s in self.dpH_core[core_select].keys():
                    ynew = self.dpH_core[core_select][s].index - float(self.swi_edit.text())
                    self.dpH_core[core_select][s].index = ynew
        else:
            dpen_av = dict()
            for c in results['O2 penetration depth'].keys():
                ls = list()
                [ls.append(i.split('-')[0]) for i in list(results['O2 penetration depth'][c].keys())
                 if "penetration" in i]
                l = pd.DataFrame([results['O2 penetration depth'][c][s]
                                  for s in results['O2 penetration depth'][c].keys()
                     if 'penetration' in s], columns=['Depth (µm)', 'O2 (%air)'], index=ls)
                dpen_av[c] = l.mean()

            # update information about actual correction of pH profile
            if 'pH swi depth' in results.keys():
                for c in self.dpH_core.keys():
                    if c in results['pH swi depth'].keys():
                        results['pH swi depth'][c] += dpen_av[c]['Depth (µm)']
                    else:
                        results['pH swi depth'][c] = dpen_av[c]['Depth (µm)']
            else:
                results['pH swi depth'] = dpen_av

            # SWI correction as for O2 project
            for c in self.dpH_core.keys():
                for s in self.dpH_core[c].keys():
                    xnew = [i - dpen_av[c]['Depth (µm)'] for i in self.dpH_core[c][s].index]
                    self.dpH_core[c][s].index = xnew

            # SWI correction applied only once
            self.continuepH_button.setEnabled(False)
        results['pH swi corrected'] = self.dpH_core

    def sliderpH_update(self):
        if self.ls_core:
            # allow only discrete values according to existing cores
            core_select = min(self.ls_core, key=lambda x: abs(x - self.sliderpH.value()))

            # update slider position and label
            self.sliderpH.setValue(int(core_select))
            self.sldpH_label.setText('core: {}'.format(core_select))

            # update plot according to selected core
            scale_plot = self.scale0 if len(scalepH) == 0 or self.status_pH == 0 else scalepH
            ls = '-.' if self.status_pH == 0 else '-'
            figpH0 = plot_pHProfile(data_pH=self.dpH_core, core=core_select, ls_core=self.ls_core, scale=scale_plot,
                                    ls=ls, fig=self.figpH, ax=self.axpH)
            self.figpH.canvas.draw()

    def adjust_pH(self):
        # open dialog window to adjust data presentation
        self.status_pH = 1.5
        global wAdjust
        wAdjust = AdjustpHWindow(self.sliderpH.value(), self.ls_core, self.dpH_core, self.scale, self.figpH, self.axpH)
        if wAdjust.isVisible():
            pass
        else:
            wAdjust.show()

    def save_pH(self):
        print('TODO: implement pH saving')

    def reset_pHpage(self):
        # update status for process control
        self.status_pH = 0
        self.scale, scalepH = None, list()
        dfpH_scale = pd.concat([pd.DataFrame([(self.dpH_core[c][n]['pH'].min(), self.dpH_core[c][n]['pH'].max())
                                              for n in self.dpH_core[c].keys()]) for c in self.dpH_core.keys()])
        self.scale0 = dfpH_scale[0].min(), dfpH_scale[1].max()

        # connect plot button to first part
        self.continuepH_button.disconnect()
        self.continuepH_button.clicked.connect(self.continue_pH)
        self.continuepH_button.setEnabled(True)
        self.adjustpH_button.setEnabled(False)
        self.swi_edit.setEnabled(False)

        # reset slider
        self.count = 0
        self.sliderpH.setValue(int(min(self.ls_core)))
        self.sldpH_label.setText('core: --')
        self.sliderpH.disconnect()
        self.sliderpH.valueChanged.connect(self.sliderpH_update)

        # clear pH range (scale), SWI correction
        self.swi_edit.setText('--')
        self.swipH_box.setVisible(True), self.swipH_box.setEnabled(False)
        self.swipH_box.setCheckState(False)

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
    def __init__(self, sliderValue, ls_core, dic_pH, scale, figpH, axpH):
        super().__init__()
        self.initUI()

        # return current core - and get the samples to plot (via slider selection)
        self.Core = min(ls_core, key=lambda x: abs(x - sliderValue))

        # get the transmitted data
        self.figpH, self.axpH, self.dic_pH, self.scaleS0 = figpH, axpH, dic_pH, scale

        # plot all samples from current core
        fig = plot_adjustpH(core=self.Core, sample=min(self.dic_pH[self.Core].keys()), dfCore=self.dic_pH[self.Core],
                            scale=self.scaleS0, fig=self.figpHs, ax=self.axpHs)
        # set the range for pH
        self.pHtrim_edit.setText(str(round(self.scaleS0[0], 2)) + ' - ' + str(round(self.scaleS0[1], 2)))

        # connect onclick event with function
        self.ls_out, self.ls_cropy = list(), list()
        self.figpHs.canvas.mpl_connect('button_press_event', self.onclick_updatepH)

        # update slider range to number of samples and set to first sample
        self.slider1pH.setMinimum(int(min(self.dic_pH[self.Core].keys())))
        self.slider1pH.setMaximum(int(max(self.dic_pH[self.Core].keys())))
        self.slider1pH.setValue(int(min(self.dic_pH[self.Core].keys())))
        self.sldpH1_label.setText('sample: ' + str(int(min(self.dic_pH[self.Core].keys()))))

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
        self.setGeometry(650, 180, 600, 300)

        # add description about how to use this window (slider, outlier detection, trim range)
        self.msg = QLabel("Use the slider to switch between samples belonging to the selected core. \nYou have the "
                          "following options to improve the fit: \n- Trim pH range (y-axis): press CONTROL/COMMAND + "
                          "select min/max \n- Remove outliers: press SHIFT + select individual points \n\nAt the end, "
                          "update the plot by pressing the button ADJUST.")
        self.msg.setWordWrap(True), self.msg.setFont(QFont('Helvetica Neue', int(fs_font*1.15)))

        # Slider for different cores and label on the right
        self.slider1pH = QSlider(Qt.Horizontal)
        self.slider1pH.setMinimumWidth(350), self.slider1pH.setFixedHeight(20)
        self.sldpH1_label = QLabel()
        self.sldpH1_label.setFixedWidth(70), self.sldpH1_label.setText('sample: --')

        # plot individual sample
        self.figpHs, self.axpHs = plt.subplots(figsize=(5, 3))
        self.figpHs.set_facecolor("none")
        self.canvaspHs = FigureCanvasQTAgg(self.figpHs)
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
        MsgGp.setMinimumWidth(300)
        gridMsg = QGridLayout()
        vbox2_top.addWidget(MsgGp)
        MsgGp.setLayout(gridMsg)

        # add GroupBox to layout and load buttons in GroupBox
        gridMsg.addWidget(self.msg, 1, 0)

        # in-between for sample plot
        plotGp = QGroupBox()
        plotGp.setFont(QFont('Helvetica Neue', 12))
        plotGp.setMinimumWidth(300), plotGp.setMinimumHeight(400)
        gridFig = QGridLayout()
        vbox2_middle.addWidget(plotGp)
        plotGp.setLayout(gridFig)

        # add GroupBox to layout and load buttons in GroupBox
        gridFig.addWidget(self.slider1pH, 1, 1)
        gridFig.addWidget(self.sldpH1_label, 1, 0)
        gridFig.addWidget(self.canvaspHs, 2, 1)
        gridFig.addWidget(pHtrim_label, 3, 0)
        gridFig.addWidget(self.pHtrim_edit, 3, 1)

        # bottom group for navigation panel
        naviGp = QGroupBox("Navigation panel")
        naviGp.setFont(QFont('Helvetica Neue', 12))
        naviGp.setMinimumWidth(300), naviGp.setFixedHeight(75)
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
        sample_select = min(self.dic_pH[self.Core].keys(), key=lambda x: abs(x - self.slider1pH.value()))

        # update slider position and label
        self.slider1pH.setValue(sample_select)
        self.sldpH1_label.setText('sample: {}'.format(sample_select))

        # update plot according to selected core
        fig = plot_adjustpH(core=self.Core, sample=sample_select, dfCore=self.dic_pH[self.Core], scale=self.scale,
                            fig=self.figpHs, ax=self.axpHs)
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
            sub = (self.dic_pH[self.Core][s].index[0] - ls_crop[-1], self.dic_pH[self.Core][s].index[-1] - ls_crop[-1])
            if np.abs(sub[0]) < np.abs(sub[1]):
                # left outer side
                self.axpHs.axhspan(self.dic_pH[self.Core][s].index[0], ls_crop[-1], color='gray', alpha=0.3)
            else:
                # right outer side
                self.axpHs.axhspan(ls_crop[-1], self.dic_pH[self.Core][s].index[-1], color='gray', alpha=0.3)
        else:
            if ls_crop[-1] < ls_crop[0]:
                # left outer side
                self.axpHs.axhspan(self.dic_pH[self.Core][s].index[0], ls_crop[-1], color='gray', alpha=0.3)
            else:
                # left outer side
                self.axpHs.axhspan(ls_crop[-1], self.dic_pH[self.Core][s].index[-1], color='gray', alpha=0.3)

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
        scalepH = (round(self.scale[0], 2), round(self.scale[1], 2))

    def cropDF_pH(self, s):
        if self.ls_cropy:
            # in case there was only 1 point selected -> extend the list to the other end
            if len(self.ls_cropy) == 1:
                sub = (self.dic_pH[self.Core][s].index[0] - self.ls_cropy[0],
                       self.dic_pH[self.Core][s].index[-1] - self.ls_cropy[0])
                if np.abs(sub[0]) < np.abs(sub[1]):
                    self.ls_cropy = [self.ls_cropy[0], self.dic_pH[self.Core][s].index[-1]]
                else:
                    self.ls_cropy = [self.dic_pH[self.Core][s].index[0], self.ls_cropy[0]]

            # actually crop the depth profile to the area selected.
            # In case more than 2 points have been selected, choose the outer ones -> trim y-axis
            dcore_crop = self.dic_pH[self.Core][s].loc[min(self.ls_cropy): max(self.ls_cropy)]
        else:
            dcore_crop = self.dic_pH[self.Core][s]
        return dcore_crop

    def popData_pH(self, dcore_crop):
        ls_pop = [min(dcore_crop.index.to_numpy(), key=lambda x: abs(x - self.ls_out[p]))
                  for p in range(len(self.ls_out))]
        # drop in case value is still there
        [dcore_crop.drop(p, inplace=True) for p in ls_pop if p in dcore_crop.index]
        return dcore_crop

    def adjustpH(self):
        # check if the pH range (scale) changed
        self.updatepHscale()

        # current core, current sample
        c, s = self.Core, int(self.sldpH1_label.text().split(' ')[-1])

        # crop dataframe to selected range
        dcore_crop = self.cropDF_pH(s=s)
        # pop outliers from depth profile
        if self.ls_out:
            dcore_crop = self.popData_pH(dcore_crop=dcore_crop)

        # update the general dictionary
        self.dic_pH[self.Core][s] = dcore_crop
        # store adjusted pH
        results['pH adjusted'] = self.dic_pH

        # re-draw pH profile plot
        fig = plot_pHUpdate(core=self.Core, nr=s, df_pHs=dcore_crop, ddcore=self.dic_pH[self.Core], scale=self.scale,
                            ax=self.axpHs, fig=self.figpHs)
        self.figpHs.canvas.draw()

        #  update range for pH plot and plot in main window
        self.pHtrim_edit.setText(str(round(self.scale[0], 2)) + ' - ' + str(round(self.scale[1], 2)))
        fig0 = plot_pHProfile(data_pH=self.dic_pH, core=self.Core, ls_core=self.dic_pH.keys(), scale=self.scale,
                              fig=self.figpH, ax=self.axpH)
        self.figpH.canvas.draw()

    def resetPlot(self):
        print('start all over again and use the raw data')

    def close_window(self):
        self.hide()


def plot_pHProfile(data_pH, core, ls_core, scale, ls='-.', fig=None, ax=None, show=True):
    plt.ioff()
    # identify closest value in list
    core_select = closest_core(ls_core=ls_core, core=core)

    # initialize figure
    if ax is None:
        fig, ax = plt.subplots(figsize=(3, 4))
    else:
        ax.cla()
    ax.set_xlabel('pH value'), ax.set_ylabel('Depth / µm')
    ax.invert_yaxis()

    if core_select != 0:
        ax.title.set_text('pH depth profile for core {}'.format(core_select))
        ax.axhline(0, lw=.5, color='k')
        for en, nr in enumerate(data_pH[core_select].keys()):
            lw = 0.75 if ls == '-.' else 1.
            mark = '.' if ls == '-.' else None
            ax.plot(data_pH[core_select][nr]['pH'], data_pH[core_select][nr].index, lw=lw, ls=ls, marker=mark,
                    color=ls_col[en], alpha=0.75, label='sample ' + str(nr))
        ax.legend(frameon=True, fontsize=10)

    # update layout
    scale_min = -1 * scale[1]/10 if scale[0] == 0 else scale[0]*0.95
    ax.set_xlim(scale_min, scale[1]*1.015)
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
    ax.title.set_text('pH profile for core {} - sample {}'.format(core, nr))
    ax.set_xlabel('pH value'), ax.set_ylabel('Depth / µm')

    # plotting part
    ax.axhline(0, lw=.5, color='k')
    for en in enumerate(ddcore.keys()):
        if en[1] == nr:
            pos = en[0]
    ax.plot(df_pHs['pH'], df_pHs.index, lw=0.75, ls='-.', marker='.', ms=4, color=ls_col[pos], alpha=0.75)

    # general layout
    scale_min = -1 * scale[1]/10 if scale[0] == 0 else scale[0]*0.95
    ax.invert_yaxis(), ax.set_xlim(scale_min, scale[1]*1.015)
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
        ax.title.set_text('pH profile for core {} - sample {}'.format(core, nr))
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
    sns.despine(), plt.tight_layout()

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
        self.setTitle("H2S / total sulfide depth profile")
        self.setSubTitle("The depth profile will first be plotted without any depth correction.  In case the pH depth"
                         " profile is available,  the total sulfide concentration is calculated.")
        self.initUI()

        # connect checkbox and load file button with a function
        self.salcon_button.clicked.connect(self.conductivity_converter)
        self.continueh2s_button.clicked.connect(self.continue_H2S)
        self.adjusth2s_button.clicked.connect(self.adjust_H2S)
        self.saveh2s_button.clicked.connect(self.save_H2S)
        self.reseth2s_button.clicked.connect(self.reset_H2Spage)
        self.swih2s_box.stateChanged.connect(self.enablePlot_swiBoxH2S)

    def initUI(self):
        # plot window, side panel for user input, and continue button
        tempC_label, tempC_unit_label = QLabel(self), QLabel(self)
        tempC_label.setText('Temperature'), tempC_unit_label.setText('degC')
        self.tempC_edit = QLineEdit(self)
        self.tempC_edit.setValidator(QDoubleValidator()), self.tempC_edit.setAlignment(Qt.AlignRight)
        self.tempC_edit.setMaximumWidth(100), self.tempC_edit.setText('13.2')

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

        # option to select the SWI (baseline) from the O2 calculations in case O2 was selected
        self.swih2s_box = QCheckBox('SWI from O2 analysis', self)
        self.swih2s_box.setFont(QFont('Helvetica Neue', fs_font))
        self.swih2s_box.setVisible(True), self.swih2s_box.setEnabled(False)

        # Action button
        self.salcon_button = QPushButton('Converter', self)
        self.salcon_button.setFixedWidth(100), self.salcon_button.setFont(QFont('Helvetica Neue', fs_font))
        self.saveh2s_button = QPushButton('Save', self)
        self.saveh2s_button.setFixedWidth(100), self.saveh2s_button.setFont(QFont('Helvetica Neue', fs_font))
        self.continueh2s_button = QPushButton('Plot', self)
        self.continueh2s_button.setFixedWidth(100), self.continueh2s_button.setFont(QFont('Helvetica Neue', fs_font))
        self.adjusth2s_button = QPushButton('Adjustments', self)
        self.adjusth2s_button.setFixedWidth(100), self.adjusth2s_button.setEnabled(False)
        self.adjusth2s_button.setFont(QFont('Helvetica Neue', fs_font))
        self.reseth2s_button = QPushButton('Reset', self)
        self.reseth2s_button.setFixedWidth(100), self.reseth2s_button.setFont(QFont('Helvetica Neue', fs_font))

        # Slider for different cores and label on the right
        self.sliderh2s = QSlider(Qt.Horizontal)
        self.sliderh2s.setMinimumWidth(350), self.sliderh2s.setFixedHeight(20)
        self.sldh2s_label = QLabel()
        self.sldh2s_label.setFixedWidth(50)
        self.sldh2s_label.setText('core: --')

        # creating window layout
        w2 = QWidget(self)
        mlayout2 = QVBoxLayout(w2)
        vbox1_top, vbox1_middle, vbox1_bottom = QHBoxLayout(), QHBoxLayout(), QVBoxLayout()
        mlayout2.addLayout(vbox1_top), mlayout2.addLayout(vbox1_middle), mlayout2.addLayout(vbox1_bottom)

        para_settings = QGroupBox("Input for H2S analysis")
        grid_load = QGridLayout()
        para_settings.setFont(QFont('Helvetica Neue', 12))
        vbox1_top.addWidget(para_settings)
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
        grid_load.addWidget(self.swih2s_box, 2, 3)
        grid_load.addWidget(self.continueh2s_button, 3, 0)
        grid_load.addWidget(self.adjusth2s_button, 3, 1)
        grid_load.addWidget(self.reseth2s_button, 3, 2)
        grid_load.addWidget(self.saveh2s_button, 3, 3)

        # draw additional "line" to separate parameters from plots and to separate navigation from rest
        vline = QFrame()
        vline.setFrameShape(QFrame.HLine | QFrame.Raised)
        vline.setLineWidth(2)
        vbox1_middle.addWidget(vline)

        # plotting area
        self.figh2s, self.axh2s = plt.subplots(figsize=(3, 4))
        self.canvash2s = FigureCanvasQTAgg(self.figh2s)
        self.axh2s.set_xlabel('H2S / µmol/l'), self.axh2s.set_ylabel('Depth / µm')
        self.axh2s.invert_yaxis()
        self.figh2s.subplots_adjust(bottom=0.2, right=0.95, top=0.9, left=0.15)
        sns.despine()

        H2S_group = QGroupBox("H2S depth profile")
        H2S_group.setMinimumWidth(350), H2S_group.setMinimumHeight(400)
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
            if self.swih2s_box.checkState() == 0:
                self.continueh2s_button.setEnabled(True), self.swih2s_edit.setEnabled(True)
            else:
                self.continueh2s_button.setEnabled(False)#, self.swih2s_edit.setEnabled(False)

    def load_H2Sdata(self):
        if self.field("SoftwareFile") == 'True':
            dsheets = dbs._loadFile4GUI(file=self.field("Data"))
        else:
            # old version with pre-processed files:
            dsheets = pd.read_excel(self.field("Data"), sheet_name=None)

        # pre-check whether pH_all in sheet names
        sheet_select = dbs.sheetname_check(dsheets, para='H2S')

        # !!! TODO: field("SoftwareFile") might be depreciated in the future
        #  prepare file depending on the type
        if self.field("SoftwareFile") == 'True':
            ddata = dsheets[sheet_select]
        else:
            ddata = dsheets[sheet_select].set_index('Nr')

        # list all available cores for pH sheet
        self.ls_core = list(dict.fromkeys(ddata['Core'].to_numpy()))

        # import all measurements for given parameter
        [self.dH2S_core, ls_nr,
         self.ls_colname] = dbs.load_measurements(dsheets=ddata, ls_core=self.ls_core, para=sheet_select)
        results['H2S raw data'] = self.dH2S_core

    def conductivity_converter(self):
        # open dialog window for conductivity -> salinity conversion
        global wConv
        wConv = SalConvWindowO2(float(self.tempC_edit.text()), self.sal_edit)
        if wConv.isVisible():
            pass
        else:
            wConv.show()

    def continue_H2S(self):
        # set status for process control
        self.status_h2s = 0

        # update subtitle in case the pH profile was present as well
        if 'pH raw data' in results.keys():
            self.setSubTitle("The total sulfide is calculated based on H2S as well as the temperature and salinity.  "
                             "Please make sure both parameters are correct.")

        # load data
        self.load_H2Sdata()

        # ----------------------------------------------------------------------------------
        # adjust all the core plots to the same x-scale (uncalibrated)
        c = list(self.dH2S_core.keys())[0]
        nr = list(self.dH2S_core[c].keys())[0]

        # columns: Core, H2S_uM
        self.colH2S = self.dH2S_core[c][nr].columns[1]
        dfH2S_scale = pd.concat([pd.DataFrame([(self.dH2S_core[c][n][self.colH2S].min(),
                                                self.dH2S_core[c][n][self.colH2S].max())
                                               for n in self.dH2S_core[c].keys()]) for c in self.dH2S_core.keys()])
        self.scale0 = dfH2S_scale[0].min(), dfH2S_scale[1].max()
        self.scale = self.scale0

        # plot the pH profile for the first core
        figH2S0 = plot_H2SProfile(data_H2S=self.dH2S_core, core=min(self.ls_core), ls_core=self.ls_core,
                                  scale=self.scale0, fig=self.figh2s, ax=self.axh2s, col=self.colH2S)

        # slider initialized to first core
        self.sliderh2s.setMinimum(int(min(self.ls_core))), self.sliderh2s.setMaximum(int(max(self.ls_core)))
        self.sliderh2s.setValue(int(min(self.ls_core)))
        self.sldh2s_label.setText('core: {}'.format(int(min(self.ls_core))))

        # when slider value change (on click), return new value and update figure plot
        self.sliderh2s.valueChanged.connect(self.sliderh2s_update)

        # update continue button to "update" in case the swi shall be updated
        self.adjusth2s_button.setEnabled(True)
        self.continueh2s_button.disconnect()

        if 'pH raw data' in results.keys():
            # get information about correlation pH to H2S + pre-check if the excel file contains a correlation sheet
            ddata_all = pd.read_excel(self.field("Data"), sheet_name=None)
            df_correl = self.precheck_totalSulfide(ddata_all)
            results['pH - H2S correlation'] = df_correl

            # calculation of total sulfide possible
            self.continueh2s_button.clicked.connect(self.continue_H2SII)

        else:
            # skip total sulfide but allow swi correction
            self.continueh2s_button.clicked.connect(self.continue_H2SIII)
        print(2490, results.keys())

    def getOriginal_pH(self, corepH, sample):
        if 'pH swi depth' in results.keys():
            if corepH in results['pH swi depth'].keys():
                if isinstance(results['pH swi depth'][corepH], float):
                    corr = results['pH swi depth'][corepH]
                else:
                    corr = results['pH swi depth'][corepH]['Depth (µm)']
            else:
                corr = 0.
            xold = results['pH raw data'][corepH][sample].index + corr
            pH_coreS = pd.DataFrame(results['pH raw data'][corepH][sample]['pH'])
            pH_coreS.index = xold
        else:
            pH_coreS = results['pH raw data'][corepH][sample]['pH']
        return pH_coreS

    def _calcTotalSulfide(self, tempK, sal_pmill, coreh2s, sampleS, pH_coreS):
        # pK1 equation
        pK1 = -98.08 + (5765.4/tempK) + 15.04555*np.log(tempK) + -0.157*(sal_pmill**0.5) + 0.0135*sal_pmill
        K1 = 10**(-pK1)

        # generate total sulfide DF
        df = pd.concat([self.dH2S_core[coreh2s][sampleS], pH_coreS], axis=1)
        df['total sulfide µmol/l'] = df[self.colH2S] * (1 + (K1 / 10**(-df['pH'])))

        # zero correction -> everything that is negative is set to 0
        df_ = df['total sulfide µmol/l'].copy()
        df_[df_ < 0] = 0
        df['total sulfide zero corr'] = df_

        return df

    def precheck_totalSulfide(self, ddata_all):
        try:
            if 'correlation' in ddata_all.keys():
                df_correl = ddata_all['correlation']
            else:
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

        # get all cores of H2S
        ls_coreH2S = list()
        [ls_coreH2S.append(l) for l in df_corr['H2S core'].to_numpy() if l not in ls_coreH2S]

        # calculate total sulfide
        dsulfide, n = dict(), 0
        for em, coreh2s in enumerate(ls_coreH2S):
            # get all samples of specific core
            samplesh2S = df_corr[df_corr['H2S core'] == coreh2s]['H2S Nr'].to_numpy()
            dsulfideS = dict()
            for en, s in enumerate(samplesh2S):
                # get the original pH profile
                pH_coreS = self.getOriginal_pH(corepH=df_corr.loc[n]['pH core'], sample=df_corr.loc[n]['pH Nr'])

                # calculate total sulfide for specific core and sample according to associated pH profile
                df = self._calcTotalSulfide(coreh2s=coreh2s, sampleS=s, tempK=tempK, sal_pmill=sal_pmill,
                                            pH_coreS=pH_coreS)
                dsulfideS[s] = df
                n += 1
            dsulfide[coreh2s] = dsulfideS
        return dsulfide

    def continue_H2SII(self):
        # update status for process control
        self.status_h2s = 0

        # update layout
        self.swih2s_box.setEnabled(True) if self.field("SWI pH as o2") == 'True' else self.swih2s_box.setEnabled(False)
        self.swih2s_edit.setEnabled(True)

        # identify closest value in list
        core_select = closest_core(ls_core=self.ls_core, core=self.sliderh2s.value())

        # convert H2S into total sulfide in case pH was measured
        dsulfide = self.calc_total_sulfide()
        results['H2S total sulfide'] = dsulfide

        # update pH profile plot for the first core
        if 'H2S total sulfide' in results.keys():
            para = 'total sulfide zero corr'
            dscale = dict()
            for c in results['H2S total sulfide'].keys():
                l = [(results['H2S total sulfide'][c][nr][para].min(), results['H2S total sulfide'][c][nr][para].max())
                     for nr in results['H2S total sulfide'][c].keys()]
                dscale[c] = pd.DataFrame((np.min(l), np.max(l)))
            scale = (pd.concat(dscale, axis=1).T[0].min(), pd.concat(dscale, axis=1).T[1].max())
        else:
            scale = self.scale0
        self.scaleS0 = scale

        # update column name that shall be plotted
        self.col2 = 'total sulfide zero corr'
        figH2S0 = plot_H2SProfile(data_H2S=dsulfide, core=core_select, ls_core=self.ls_core, scale=scale,
                                  fig=self.figh2s, ax=self.axh2s, col=self.col2, ls='-')

        # slider initialized to first core
        self.sliderh2s.setMinimum(int(min(self.ls_core))), self.sliderh2s.setMaximum(int(max(self.ls_core)))
        self.sliderh2s.setValue(int(min(self.ls_core)))
        self.sldh2s_label.setText('core: {}'.format(int(min(self.ls_core))))

        # when slider value change (on click), return new value and update figure plot
        self.sliderh2s.valueChanged.connect(self.sliderh2s_updateII)

        # ----------------------------------------------------------------------------------------------------------
        # update continue button as well as adjustment button in case the swi shall be updated
        self.adjusth2s_button.disconnect()
        self.adjusth2s_button.clicked.connect(self.adjust_H2SII)
        self.continueh2s_button.disconnect()
        self.continueh2s_button.clicked.connect(self.continue_H2SIII)

    def continue_H2SIII(self):
        # update status for process control
        self.status_h2s = 2

        # update layout
        self.swih2s_box.setEnabled(True) if self.field("SWI pH as o2") == 'True' else self.swih2s_box.setEnabled(False)
        self.swih2s_edit.setEnabled(True)

        # update subtitle for swi correction
        self.setSubTitle("You reached the sediment-water interface correction.  Either choose the correction based on "
                         "the surface found in the O2 project or manually adjust the surface.")

        # identify closest value in list
        core_select = closest_core(ls_core=self.ls_core, core=self.sliderh2s.value())
        # identify data, that shall be plotted
        self.data = results['H2S total sulfide'] if 'H2S total sulfide' in results.keys() else self.dH2S_core

        # check whether a (manual) swi correction is required. SWI correction only for current core
        self.swi_correctionH2S()

        # plot the pH profile for the first core
        if 'H2S total sulfide' in results.keys():
            para = 'total sulfide zero corr'
            dscale = dict()
            for c in results['H2S total sulfide'].keys():
                l = [(results['H2S total sulfide'][c][nr][para].min(), results['H2S total sulfide'][c][nr][para].max())
                     for nr in results['H2S total sulfide'][c].keys()]
                dscale[c] = pd.DataFrame((np.min(l), np.max(l)))
            scale = (pd.concat(dscale, axis=1).T[0].min(), pd.concat(dscale, axis=1).T[1].max())
        else:
            scale = self.scale0
        self.scaleS0 = scale
        figH2S = plot_H2SProfile(data_H2S=self.data, core=core_select, ls_core=self.ls_core, scale=self.scaleS0,
                                 fig=self.figh2s, ax=self.axh2s, col=self.colH2S, ls='-')
        self.figh2s.canvas.draw()

    def swi_correctionH2S(self):
        # identify closest value in list
        core_select = min(self.ls_core, key=lambda x: abs(x - self.sliderh2s.value()))
        if self.swih2s_box.checkState() == 0:
            self.status_h2s = 0
            self.continueh2s_button.setEnabled(True)

            if '--' in self.swih2s_edit.text() or len(self.swih2s_edit.text()) == 0:
                pass
            else:
                # correction of manually selected baseline
                for s in self.data[core_select].keys():
                    # H2S correction
                    ynew = self.data[core_select][s].index - float(self.swih2s_edit.text())
                    self.data[core_select][s].index = ynew
                    # pH correction
                    ynew = self.data[core_select][s].index - float(self.swih2s_edit.text())
        else:
            dpenH2S_av = dict()
            for c in results['O2 penetration depth'].keys():
                ls = list()
                [ls.append(i.split('-')[0]) for i in list(results['O2 penetration depth'][c].keys())
                 if "penetration" in i]
                l = pd.DataFrame([results['O2 penetration depth'][c][s]
                                  for s in results['O2 penetration depth'][c].keys()
                                  if 'penetration' in s], columns=['Depth (µm)', 'O2 (%air)'], index=ls)
                dpenH2S_av[c] = l.mean()

            # SWI correction as for O2 project
            for c in self.data.keys():
                for s in self.data[c].keys():
                    xnew = [i - dpenH2S_av[c]['Depth (µm)'] for i in self.data[c][s].index]
                    self.data[c][s].index = xnew

            # SWI correction applied only once
            self.continueh2s_button.setEnabled(False)

        # add to results dictionary
        if 'H2S total sulfide' in results.keys():
            results['H2S total sulfide swi corrected'] = self.data
        else:
            results['H2S swi corrected'] = self.data

    def sliderh2s_update(self):
        if self.ls_core:
            # allow only discrete values according to existing cores
            core_select = min(self.ls_core, key=lambda x: abs(x - self.sliderh2s.value()))

            # update slider position and label
            self.sliderh2s.setValue(int(core_select))
            self.sldh2s_label.setText('core: {}'.format(core_select))

            # update plot according to selected core
            if len(scaleh2s) == 0 or self.status_h2s == 0:
                scale_plot = self.scale0
            else:
                scale_plot = scaleh2s
            figH2S = plot_H2SProfile(data_H2S=self.dH2S_core, core=core_select, ls_core=self.ls_core, scale=scale_plot,
                                     fig=self.figh2s, ax=self.axh2s, col=self.colH2S,  ls='-.')
            self.figh2s.canvas.draw()

    def sliderh2s_updateII(self):
        if self.ls_core:
            # allow only discrete values according to existing cores
            core_select = min(self.ls_core, key=lambda x: abs(x - self.sliderh2s.value()))

            # update slider position and label
            self.sliderh2s.setValue(int(core_select))
            self.sldh2s_label.setText('core: {}'.format(core_select))

            # update plot according to selected core
            if 'H2S total sulfide' in results.keys():
                para, dd, dscale = 'total sulfide zero corr', results['H2S total sulfide'], dict()
                for c in dd.keys():
                    l = [(dd[c][nr][para].min(), dd[c][nr][para].max()) for nr in dd[c].keys()]
                    dscale[c] = pd.DataFrame((np.min(l), np.max(l)))
                scale_plot = (pd.concat(dscale, axis=1).T[0].min(), pd.concat(dscale, axis=1).T[1].max())
            else:
                scale_plot = self.scale0 if len(scaleh2s) == 0 or self.status_h2s == 0 else scaleh2s
            figH2S = plot_H2SProfile(data_H2S=results['H2S total sulfide'], core=core_select, ls_core=self.ls_core,
                                     scale=scale_plot, fig=self.figh2s, ax=self.axh2s, col=self.col2, ls='-')
            self.figh2s.canvas.draw()

    def adjust_H2S(self):
        # open dialog window to adjust data presentation
        self.status_h2s = 1.5

        global wAdjustS
        res_pH = results['pH - H2S correlation'] if 'pH - H2S correlation' in results.keys() else None
        wAdjustS = AdjustpHWindowS(self.sliderh2s.value(), self.ls_core, self.dH2S_core, self.scale, self.colH2S,
                                   self.figh2s, self.axh2s, res_pH, self.swih2s_box, self.swih2s_edit, 0)
        if wAdjustS.isVisible():
            pass
        else:
            wAdjustS.show()

    def adjust_H2SII(self):
        # open dialog window to adjust data presentation
        self.status_h2s = 2.5
        res_pH = results['pH - H2S correlation'] if 'pH - H2S correlation' in results.keys() else None

        global wAdjustS
        wAdjustS = AdjustpHWindowS(self.sliderh2s.value(), self.ls_core, results['H2S total sulfide'], self.scaleS0,
                                   self.col2, self.figh2s, self.axh2s, res_pH, self.swih2s_box, self.swih2s_edit, 1)
        if wAdjustS.isVisible():
            pass
        else:
            wAdjustS.show()

    def save_H2S(self):
        print('TODO: implement H2S saving')

    def reset_H2Spage(self):
        # update status for process control
        self.status_h2s = 0
        self.scale, scaleh2s = None, list()
        dfH2S_scale = pd.concat([pd.DataFrame([(self.dH2S_core[c][n][self.colH2S].min(),
                                                self.dH2S_core[c][n][self.colH2S].max())
                                               for n in self.dH2S_core[c].keys()]) for c in self.dH2S_core.keys()])
        self.scale0 = dfH2S_scale[0].min(), dfH2S_scale[1].max()
        self.tempC_edit.setText('13.2')
        self.sal_edit.setText('0.')

        # connect plot button to first part
        self.continueh2s_button.disconnect()
        self.continueh2s_button.clicked.connect(self.continue_H2S)
        self.continueh2s_button.setEnabled(True)
        self.adjusth2s_button.setEnabled(False)
        self.swih2s_edit.setEnabled(False)

        # reset slider
        self.count = 0
        self.sliderh2s.setValue(int(min(self.ls_core)))
        self.sldh2s_label.setText('core: --')
        self.sliderh2s.disconnect()
        self.sliderh2s.valueChanged.connect(self.sliderh2s_update)

        # clear pH range (scale), SWI correction
        self.swih2s_edit.setText('--')
        self.sldh2s_label.setText('core: --')
        self.swih2s_box.setVisible(True), self.swih2s_box.setEnabled(False)
        self.swih2s_box.setCheckState(False)

        # empty figure
        self.axh2s.cla()
        self.axh2s.set_xlabel('H2S / µmol/l'), self.axh2s.set_ylabel('Depth / µm')
        self.axh2s.invert_yaxis()
        self.figh2s.subplots_adjust(bottom=0.2, right=0.95, top=0.9, left=0.15)
        sns.despine()
        self.figh2s.canvas.draw()

        # reset the subtext
        self.setSubTitle("The depth profile will be plotted without any depth correction.  In case the pH depth profile"
                         " is available,  the total sulfide concentration is calculated.")

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
    def __init__(self, sliderValue, ls_core, dic_H2S, scale, col, figH2S, axH2S, df_correl, swih2s_box, swih2s_edit,
                 status):
        super().__init__()
        self.initUI()

        # get the transmitted data
        self.figH2S, self.axH2S, self.dic_H2S, self.scaleS0, self.colH2S = figH2S, axH2S, dic_H2S, scale, col
        self.df_correl, self.ls_core, self.swih2s_box, self.status_ph = df_correl, ls_core, swih2s_box, status
        self.swih2s_edit = swih2s_edit
        self.ls = '-.' if self.status_ph == 0 else '-'

        # return current core - and get the samples to plot (via slider selection)
        self.Core = min(self.ls_core, key=lambda x: abs(x - sliderValue))

        # plot all samples from current core
        h2s_nr = min(self.dic_H2S[self.Core].keys())
        if self.df_correl is None:
            pH_sample = None
        else:
            pH_sample = self.df_correl[self.df_correl['H2S Nr'] == h2s_nr]['pH Nr'].to_numpy()[0]

        # get pH data and in case apply depth correction in case it was done for H2S / total sulfide
        self.pH_data = results['pH raw data'] if 'pH raw data' in results.keys() else None
        if self.pH_data:
            self.swi_correctionpHII()
        fig, self.ax1 = plot_adjustH2S(core=self.Core, sample=h2s_nr, col=self.colH2S, dfCore=self.dic_H2S[self.Core],
                                       scale=self.scaleS0, fig=self.figH2Ss, ax1=None, ax=self.axH2Ss, pH=self.pH_data,
                                       pH_sample=pH_sample)
        # set the range for pH
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
        self.setGeometry(650, 180, 600, 300)

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
        self.figH2Ss, self.axH2Ss = plt.subplots(figsize=(5, 3))
        self.figH2Ss.set_facecolor("none")
        self.canvasH2Ss = FigureCanvasQTAgg(self.figH2Ss)
        self.axH2Ss.set_xlabel('H2S / µmol/l'), self.axH2Ss.set_ylabel('Depth / µm')
        self.axH2Ss.invert_yaxis()
        self.figH2Ss.subplots_adjust(bottom=0.2, right=0.95, top=0.85, left=0.15)
        sns.despine()

        # define pH range
        H2Strim_label = QLabel(self)
        H2Strim_label.setText('H2S range: '), H2Strim_label.setFont(QFont('Helvetica Neue', 12))
        self.H2Strim_edit = QLineEdit(self)
        self.H2Strim_edit.setValidator(QRegExpValidator()), self.H2Strim_edit.setAlignment(Qt.AlignRight)
        self.H2Strim_edit.setMaximumHeight(int(fs_font*1.5))

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
        MsgGp.setMinimumWidth(300)
        gridMsg = QGridLayout()
        vbox2_top.addWidget(MsgGp)
        MsgGp.setLayout(gridMsg)

        # add GroupBox to layout and load buttons in GroupBox
        gridMsg.addWidget(self.msg, 1, 0)

        # in-between for sample plot
        plotGp = QGroupBox()
        plotGp.setFont(QFont('Helvetica Neue', 12))
        plotGp.setMinimumWidth(300), plotGp.setMinimumHeight(400)
        gridFig = QGridLayout()
        vbox2_middle.addWidget(plotGp)
        plotGp.setLayout(gridFig)

        # add GroupBox to layout and load buttons in GroupBox
        gridFig.addWidget(self.slider1H2S, 1, 1)
        gridFig.addWidget(self.sldH2S1_label, 1, 0)
        gridFig.addWidget(self.canvasH2Ss, 2, 1)
        gridFig.addWidget(H2Strim_label, 3, 0)
        gridFig.addWidget(self.H2Strim_edit, 3, 1)

        # bottom group for navigation panel
        naviGp = QGroupBox("Navigation panel")
        naviGp.setFont(QFont('Helvetica Neue', 12))
        naviGp.setMinimumWidth(300), naviGp.setFixedHeight(75)
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
            pH_sample = None
        else:
            pH_sample = self.df_correl[self.df_correl['H2S Nr'] == sample_select]['pH Nr'].to_numpy()[0]

        pH_data = results['pH raw data'] if 'pH raw data' in results.keys() else None
        fig, self.ax1 = plot_adjustH2S(core=self.Core, sample=sample_select, dfCore=self.dic_H2S[self.Core],
                                       scale=self.scale, fig=self.figH2Ss, ax=self.axH2Ss, col=self.colH2S,
                                       pH=pH_data, pH_sample=pH_sample, ax1=self.ax1)
        self.figH2Ss.canvas.draw()

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
            sub = (self.dic_pH[self.Core][s].index[0] - ls_crop[-1], self.dic_pH[self.Core][s].index[-1] - ls_crop[-1])
            if np.abs(sub[0]) < np.abs(sub[1]):
                # left outer side
                self.axpHs.axhspan(self.dic_pH[self.Core][s].index[0], ls_crop[-1], color='gray', alpha=0.3)
            else:
                # right outer side
                self.axpHs.axhspan(ls_crop[-1], self.dic_pH[self.Core][s].index[-1], color='gray', alpha=0.3)
        else:
            if ls_crop[-1] < ls_crop[0]:
                # left outer side
                self.axpHs.axhspan(self.dic_pH[self.Core][s].index[0], ls_crop[-1], color='gray', alpha=0.3)
            else:
                # left outer side
                self.axpHs.axhspan(ls_crop[-1], self.dic_pH[self.Core][s].index[-1], color='gray', alpha=0.3)

        # draw vertical line to mark boundaries
        [self.axpHs.axhline(x, color='k', ls='--', lw=0.5) for x in ls_crop]
        self.figpHs.canvas.draw()

    def updateH2Sscale(self):
        # get pH range form LineEdit
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

        # if pH range was updated by the user -> update self.scale (prevent further down)
        if scale != self.scale:
            self.scale = scale

        # update global variable
        global scaleh2s
        scaleh2s = (round(self.scale[0], 2), round(self.scale[1], 2))

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

        # update the general dictionary
        self.dic_H2S[self.Core][s] = dcore_crop

        # re-draw pH profile plot
        if self.df_correl is None:
            pH_sample = None
        else:
            pH_sample = self.df_correl[self.df_correl['H2S Nr'] == s]['pH Nr'].to_numpy()[0]
        # pH_sample = self.df_correl[self.df_correl['H2S Nr'] == s]['pH Nr'].to_numpy()[0] if self.df_correl else None
        self.pH_data = results['pH raw data'] if 'pH raw data' in results.keys() else None
        print(3119, results.keys())
        if 'H2S swi corrected pH' in results and self.pH_data:
            self.swi_correctionpHII()
        fig, self.ax1 = plot_H2SUpdate(core=self.Core, nr=s, df_H2Ss=dcore_crop, ddcore=self.dic_H2S[self.Core],
                                       scale=self.scale, ax=self.axH2Ss, fig=self.figH2Ss, col=self.colH2S,
                                       pH=self.pH_data, pHnr=pH_sample, ax1=self.ax1)
        self.figH2Ss.canvas.draw()

        #  update range for pH plot and plot in main window
        self.H2Strim_edit.setText(str(round(self.scale[0], 2)) + ' - ' + str(round(self.scale[1], 2)))
        fig0 = plot_H2SProfile(data_H2S=self.dic_H2S, core=self.Core, ls_core=self.dic_H2S.keys(), scale=self.scale,
                               fig=self.figH2S, ax=self.axH2S, col=self.colH2S, ls=self.ls)
        self.figH2S.canvas.draw()
        self.status_ph += 1

    def swi_correctionpHII(self):
        # identify closest value in list
        core_select = min(self.ls_core, key=lambda x: abs(x - self.slider1H2S.value()))
        if self.swih2s_box.checkState() == 0:
            if '--' in self.swih2s_edit.text() or len(self.swih2s_edit.text()) == 0:
                pass
            else:
                # correction of manually selected baseline
                for s in self.pH_data[core_select].keys():
                    ynew = self.pH_data[core_select][s].index - float(self.swih2s_edit.text())
        else:
            dpenH2S_av = dict()
            for c in results['O2 penetration depth'].keys():
                ls = list()
                [ls.append(i.split('-')[0]) for i in list(results['O2 penetration depth'][c].keys())
                 if "penetration" in i]
                l = pd.DataFrame([results['O2 penetration depth'][c][s]
                                  for s in results['O2 penetration depth'][c].keys()
                                  if 'penetration' in s], columns=['Depth (µm)', 'O2 (%air)'], index=ls)
                dpenH2S_av[c] = l.mean()

            # SWI correction as for O2 project
            for c in self.pH_data.keys():
                for s in self.pH_data[c].keys():
                    xnew = [i - dpenH2S_av[c]['Depth (µm)'] for i in self.pH_data[c][s].index]
                    self.pH_data[c][s].index = xnew

        # add to results dictionary
        if 'H2S total sulfide' in results.keys():
            results['H2S total sulfide swi corrected pH'] = self.pH_data
        else:
            results['H2S swi corrected pH'] = self.pH_data

    def resetPlotH2S(self):
        print('start all over again and use the raw data')

    def close_windowH2S(self):
        self.hide()


def plot_H2SProfile(data_H2S, core, ls_core, scale, col, ls='-.', fig=None, ax=None, show=True):
    plt.ioff()
    # identify closest value in list and the plotted analyte
    core_select = closest_core(ls_core=ls_core, core=core)

    s0 = list(data_H2S[core_select].keys())[0]
    para = 'total sulfide zero corr' if 'total sulfide zero corr' in data_H2S[core_select][s0].columns else col

    # initialize figure
    if ax is None:
        fig, ax = plt.subplots(figsize=(3, 4))
    else:
        ax.cla()
    ax.set_xlabel('{} / µmol/l'.format(para.split('zero')[0].split('_')[0])), ax.set_ylabel('Depth / µm')
    ax.invert_yaxis()

    if core_select != 0:
        ax.title.set_text('{} depth profile for core {}'.format(para.split('zero')[0].split('_')[0], core_select))
        ax.axhline(0, lw=.5, color='k')
        for en, nr in enumerate(data_H2S[core_select].keys()):
            df = data_H2S[core_select][nr][para].dropna()
            mark ='.' if ls == '-.' else None
            lw = 1.0 if ls == '-.' else 0.75
            ax.plot(df, df.index, lw=0.75, ls=ls, marker=mark, color=ls_col[en], alpha=0.75, label='sample ' + str(nr))
        ax.legend(frameon=True, fontsize=10)

    # update layout
    scale_min = -1 * scale[1]/10 if scale[0] == 0 else scale[0]*0.95
    ax.set_xlim(scale_min, scale[1]*1.05)
    fig.subplots_adjust(bottom=0.2, right=0.95, top=0.85, left=0.15)

    if show is False:
        plt.close(fig)
    else:
        fig.canvas.draw()
    return fig


def plot_adjustH2S(core, sample, dfCore, col, scale, pH, pH_sample, fig, ax, ax1):
    # initialize first plot with first core and sample
    fig, ax1 = GUI_adjustDepthH2S(core=core, nr=sample, dfCore=dfCore, col=col, scale=scale, fig=fig, ax=ax, ax1=ax1,
                                  pH=pH, pHnr=pH_sample)
    fig.canvas.draw()
    return fig, ax1


def plot_H2SUpdate(core, nr, df_H2Ss, ddcore, scale, col, pH, pHnr, fig, ax, ax1=None):
    # clear coordinate system but keep the labels
    ax.cla()
    if pH:
        ax1.cla()
        ax1.set_xlabel('pH value')
    else:
        ax1 = None
    ax.title.set_text('H2S profile for core {} - sample {}'.format(core, nr))
    ax.set_xlabel('H2S / µmol/l'), ax.set_ylabel('Depth / µm')

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
        ax1.plot(results['pH raw data'][core][pHnr]['pH'], results['pH raw data'][core][pHnr].index+corr, lw=0.75,
                 ls='--', color='#971EB3', alpha=0.75)

    # general layout
    scale_min = -1 * scale[1]/10 if scale[0] == 0 else scale[0]*0.95
    ax.invert_yaxis(), ax.set_xlim(scale_min, scale[1]*1.015)
    sns.despine()
    if pH:
        ax.spines['top'].set_visible(True)
    plt.subplots_adjust(bottom=0.2, right=0.95, top=0.8, left=0.15)
    fig.canvas.draw()
    return fig, ax1


def GUI_adjustDepthH2S(core, nr, dfCore, scale, col, pH=None, pHnr=None, fig=None, ax=None, ax1=None, show=True):
    plt.ioff()
    # initialize figure plot
    if ax is None:
        fig, ax = plt.subplots(figsize=(5, 3))
    else:
        ax.cla()
    if pH:
        if ax1 is None:
            ax1 = ax.twiny()
            ax1.set_xlabel('pH value')
        else:
            ax1.clear()
            ax1.set_xlabel('pH value')
    else:
        ax1 = None

    if core != 0:
        ax.title.set_text('H2S profile for core {} - sample {}'.format(core, nr))
        ax.set_ylabel('Depth / µm'), ax.set_xlabel('H2S / µmol/l')

    # plotting part
    ax.axhline(0, lw=.5, color='k')

    # position in sample list to get teh right color
    for en in enumerate(dfCore.keys()):
        if en[1] == nr:
            pos = en[0]

    ax.plot(dfCore[nr][col], dfCore[nr].index, lw=0.75, ls='-.', marker='.', ms=4, color=ls_col[pos], alpha=0.75)

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
        print(3310, 'pH raw data' in results.keys(), 'corr', corr)
        print(core, pHnr, results['pH raw data'].keys())
        ax1.plot(results['pH raw data'][core][pHnr]['pH'], results['pH raw data'][core][pHnr].index+corr, lw=0.75,
                 ls='--', color='#971EB3', alpha=0.75)

    # general layout
    scale_min = -1 * scale[1]/10 if scale[0] == 0 else scale[0]*0.95
    ax.invert_yaxis(), ax.set_xlim(scale_min, scale[1]*1.015)
    sns.despine()
    ax.spines['top'].set_visible(True) if pH else ax.spines['top'].set_visible(False)
    if pH:
        fig.subplots_adjust(bottom=0.2, right=0.95, top=0.8, left=0.15)
    else:
        fig.subplots_adjust(bottom=0.2, right=0.95, top=0.8, left=0.15)

    if show is False:
        plt.close(fig)
    else:
        fig.canvas.draw()
    return fig, ax1


# -----------------------------------------------
class epPage(QWizardPage):
    def __init__(self, parent=None):
        super(epPage, self).__init__(parent)
        self.setTitle("EP depth profile")
        self.setSubTitle("Press PLOT to start and display the initial EP profiles.  If a drift correction shall be "
                         "included, make sure to check the checkbox.  At any case,  the profile can be adjusted by "
                         "trimming the depth range and removing outliers.")

        self.status_EP = 0
        self.initUI()

        # connect checkbox and load file button with a function
        self.continueEP_button.clicked.connect(self.continue_EP)
        self.adjustEP_button.clicked.connect(self.adjust_EP)
        self.saveEP_button.clicked.connect(self.save_EP)
        self.resetEP_button.clicked.connect(self.reset_EPpage)
        self.swiEP_box.stateChanged.connect(self.enablePlot_swiBox)

    def initUI(self):
        # manual baseline correction
        swi_label, swi_unit_label = QLabel(self), QLabel(self)
        swi_label.setText('Actual correction: '), swi_unit_label.setText('µm')
        self.swi_edit = QLineEdit(self)
        self.swi_edit.setValidator(QDoubleValidator()), self.swi_edit.setAlignment(Qt.AlignRight)
        self.swi_edit.setMaximumWidth(100), self.swi_edit.setText('--'), self.swi_edit.setEnabled(False)

        # option to select the SWI (baseline) from the O2 calculations in case O2 was selected
        self.swiEP_box = QCheckBox('SWI from O2 analysis', self)
        self.swiEP_box.setFont(QFont('Helvetica Neue', fs_font))
        self.swiEP_box.setVisible(True), self.swiEP_box.setEnabled(False)

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
        self.sldEP_label.setFixedWidth(50), self.sldEP_label.setText('core: --')

        # creating window layout
        w2 = QWidget(self)
        mlayout2 = QVBoxLayout(w2)
        vbox1_top, vbox1_middle, vbox1_bottom = QHBoxLayout(), QHBoxLayout(), QVBoxLayout()
        mlayout2.addLayout(vbox1_top), mlayout2.addLayout(vbox1_middle), mlayout2.addLayout(vbox1_bottom)

        swiarea = QGroupBox("Navigation panel")
        swiarea.setMinimumHeight(125)
        grid_swi = QGridLayout()
        swiarea.setFont(QFont('Helvetica Neue', fs_font))
        vbox1_top.addWidget(swiarea)
        swiarea.setLayout(grid_swi)

        # include widgets in the layout
        grid_swi.addWidget(drift_label, 0, 0)
        grid_swi.addWidget(self.driftEP_box, 0, 1)
        grid_swi.addWidget(swi_label, 1, 0)
        grid_swi.addWidget(self.swi_edit, 1, 1)
        grid_swi.addWidget(swi_unit_label, 1, 2)
        grid_swi.addWidget(self.swiEP_box, 1, 3)
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
        self.figEP, self.axEP = plt.subplots(figsize=(5, 3))
        self.canvasEP = FigureCanvasQTAgg(self.figEP)
        self.axEP.set_xlabel('EP / mV'), self.axEP.set_ylabel('Depth / µm')
        self.axEP.invert_yaxis()
        self.figEP.tight_layout(pad=1.5)
        sns.despine()

        ep_group = QGroupBox("EP depth profile")
        ep_group.setMinimumWidth(350), ep_group.setMinimumHeight(400)
        grid_ep = QGridLayout()

        # add GroupBox to layout and load buttons in GroupBox
        vbox1_bottom.addWidget(ep_group)
        ep_group.setLayout(grid_ep)
        grid_ep.addWidget(self.sliderEP, 1, 0)
        grid_ep.addWidget(self.sldEP_label, 1, 1)
        grid_ep.addWidget(self.canvasEP, 2, 0)
        self.setLayout(mlayout2)

    def enablePlot_swiBox(self):
        if self.status_EP >= 1:
            if self.swiEP_box.checkState() == 0:
                self.continueEP_button.setEnabled(True), self.swi_edit.setEnabled(True)
            else:
                self.continueEP_button.setEnabled(False)

    def load_EPdata(self):
        if self.field("SoftwareFile") == 'True':
            dsheets = dbs._loadFile4GUI(file=self.field("Data"))
        else:
            # old version with pre-processed files:
            dsheets = pd.read_excel(self.field("Data"), sheet_name=None)

        # pre-check whether pH_all in sheet names
        sheet_select = dbs.sheetname_check(dsheets, para='EP')

        # !!! TODO: field("SoftwareFile") might be depreciated in the future
        #  prepare file depending on the type
        if self.field("SoftwareFile") == 'True':
            ddata = dsheets[sheet_select]
        else:
            ddata = dsheets[sheet_select].set_index('Nr')

        # list all available cores for pH sheet (in timely order, e.g., not ordered in ascending/ descending order)
        self.ls_core = list(dict.fromkeys(ddata['Core'].to_numpy()))

        # import all measurements for given parameter
        [self.dEP_core, ls_nr,
         self.ls_colname] = dbs.load_measurements(dsheets=ddata, ls_core=self.ls_core, para=sheet_select)

        # order depth index ascending
        self.dEP_core = dict(map(lambda c: (c, dict(map(lambda s: (s, self.dEP_core[c][s].sort_index(ascending=True)),
                                                        self.dEP_core[c].keys()))), self.dEP_core.keys()))
        results['EP raw data'] = self.dEP_core

    def continue_EP(self):
        # set status for process control
        self.status_EP = 0

        # update instruction
        self.setSubTitle("Now,  the surface water interface can now be corrected. In case the O2 project was assessed "
                         "before,  you can either use the depth determined there, or use your own depth. ")

        # load data
        self.load_EPdata()

        # ----------------------------------------------------------------------------------
        # adjust all the core plots to the same x-scale
        dfEP_scale = pd.concat([pd.DataFrame([(self.dEP_core[c][n]['EP_mV'].min(), self.dEP_core[c][n]['EP_mV'].max())
                                              for n in self.dEP_core[c].keys()]) for c in self.dEP_core.keys()])
        self.scale0 = dfEP_scale[0].min(), dfEP_scale[1].max()
        # use self.scale0 for the initial plot but make it possible to update self.scale
        self.scale = self.scale0

        # plot the pH profile for the first core
        figEP0 = plot_initalProfile(data=self.dEP_core, para='EP', unit='mV', core=min(self.ls_core), scale=self.scale0,
                                    ls_core=self.ls_core, col_name='EP_mV', fig=self.figEP, ax=self.axEP)
        # slider initialized to first core
        self.sliderEP.setMinimum(int(min(self.ls_core))), self.sliderEP.setMaximum(int(max(self.ls_core)))
        self.sliderEP.setValue(int(min(self.ls_core)))
        self.sldEP_label.setText('core: {}'.format(int(min(self.ls_core))))

        # when slider value change (on click), return new value and update figure plot
        self.sliderEP.valueChanged.connect(self.sliderEP_update)

        # update continue button to "update" in case the swi shall be updated
        self.adjustEP_button.setEnabled(True)
        self.continueEP_button.disconnect()
        if self.driftEP_box.isChecked():
            self.continueEP_button.clicked.connect(self.continue_EPII)
        else:
            self.continueEP_button.clicked.connect(self.continue_EPIII)
            self.swi_edit.setEnabled(True)

            # set options for swi correction
            if 'O2 penetration depth' not in results.keys():
                self.swiEP_box.setEnabled(False)

    def sliderEP_update(self):
        if self.ls_core:
            # allow only discrete values according to existing cores
            core_select = min(self.ls_core, key=lambda x: abs(x - self.sliderEP.value()))

            # update slider position and label
            self.sliderEP.setValue(int(core_select))
            self.sldEP_label.setText('core: {}'.format(core_select))

            # update plot according to selected data set and core
            data = self.dEP_corr if 'EP drift corrected' in results.keys() else self.dEP_core
            dfEP_scale = pd.concat([pd.DataFrame([(data[c][n]['EP_mV'].min(), data[c][n]['EP_mV'].max())
                                                  for n in data[c].keys()]) for c in data.keys()])
            scale_plot = dfEP_scale[0].min(), dfEP_scale[1].max()
            self.scale = scale_plot

            ls = '-.' if self.status_EP == 0 else '-'
            figEP0 = plot_initalProfile(data=data, para='EP', unit='mV', col_name='EP_mV', core=core_select,
                                        ls_core=self.ls_core, scale=scale_plot, ls=ls, fig=self.figEP, ax=self.axEP)
            self.figEP.canvas.draw()

    def continue_EPII(self):
        # update status for process control
        self.status_EP += 1

        # identify closest value in list
        core_select = closest_core(ls_core=self.ls_core, core=self.sliderEP.value())

        # drift correction in case it was selected
        self.drift_correctionEP()

        # store drift corrected EP
        results['EP drift corrected'] = self.dEP_corr

        # plot the pH profile for the first core
        dfEP_scale = pd.concat([pd.DataFrame([(self.dEP_corr[c][n]['EP_mV'].min(), self.dEP_corr[c][n]['EP_mV'].max())
                                              for n in self.dEP_corr[c].keys()]) for c in self.dEP_corr.keys()])
        scale_plot = dfEP_scale[0].min(), dfEP_scale[1].max()
        self.scale = scale_plot
        # scale_plot = self.scale0 if len(scaleEP) == 0 else scaleEP
        figEP0 = plot_initalProfile(data=self.dEP_corr, para='EP', unit='mV', col_name='EP_mV', core=core_select,
                                    ls_core=self.ls_core, scale=scale_plot, ls='-', fig=self.figEP, ax=self.axEP)
        self.figEP.canvas.draw()

        # !!!TODO: allow de-checking of sample (which is not an EP signal) in figure plot



        # slider initialized to first core
        self.sliderEP.setValue(int(core_select)), self.sldEP_label.setText('core: {}'.format(int(core_select)))

        # when slider value change (on click), return new value and update figure plot
        self.sliderEP.valueChanged.connect(self.sliderEP_update)

        self.continueEP_button.disconnect()
        self.continueEP_button.clicked.connect(self.continue_EPIII)

        # update layout
        self.swiEP_box.setEnabled(True) if self.field("SWI pH as o2") == 'True' else self.swiEP_box.setEnabled(False)
        self.swi_edit.setEnabled(True)

    def drift_correctionEP(self):
        # get first data point (as we are sure this was measured in the water column)
        ddict = dict(map(lambda c: (c, pd.DataFrame([(self.dEP_core[c][s]['EP_mV'].values[0],
                                                      self.dEP_core[c][s]['EP_mV'].index[0])
                                                     for s in self.dEP_core[c].keys()], index=self.dEP_core[c].keys())),
                         self.ls_core))
        df = pd.concat(ddict, axis=0)

        # polynomial fit of 2nd order: ax**2 + bx + c = y
        paraFit = np.polyfit(np.arange(0, len(df.index)), df[0].to_numpy(), deg=2)

        # apply drift correction
        self.dEP_corr = dict()
        i = 0
        for c in self.dEP_core.keys():
            d = dict()
            for s in self.dEP_core[c].keys():
                d_corr = self.dEP_core[c][s]['EP_mV'] + (paraFit[0]*(i**2) + paraFit[1]*i)
                d[s] = pd.DataFrame(d_corr, columns=['EP_mV'])
                i += 1
            self.dEP_corr[c] = d

    def swi_correctionEP(self):
        # identify closest value in list
        core_select = min(self.ls_core, key=lambda x: abs(x - self.sliderEP.value()))
        if self.swiEP_box.checkState() == 0:
            self.continueEP_button.setEnabled(True)

            # update information about actual correction of pH profile
            if '--' in self.swi_edit.text():
                results['EP swi depth'] = dict({core_select: 0.})
            elif 'EP swi depth' in results.keys():
                if core_select in results['EP swi depth'].keys():
                    results['EP swi depth'][core_select] += float(self.swi_edit.text())
                else:
                    dic1 = dict({core_select: float(self.swi_edit.text())})
                    results['EP swi depth'].update(dic1)
            else:
                results['EP swi depth'] = dict({core_select: float(self.swi_edit.text())})

            if '--' in self.swi_edit.text() or len(self.swi_edit.text()) == 0:
                pass
            else:
                # correction of manually selected baseline
                for s in self.data[core_select].keys():
                    ynew = self.data[core_select][s].index - float(self.swi_edit.text())
                    self.data[core_select][s].index = ynew
        else:
            dpen_av = dict()
            for c in results['O2 penetration depth'].keys():
                ls = list()
                [ls.append(i.split('-')[0]) for i in list(results['O2 penetration depth'][c].keys())
                 if "penetration" in i]
                l = pd.DataFrame([results['O2 penetration depth'][c][s]
                                  for s in results['O2 penetration depth'][c].keys()
                                  if 'penetration' in s], columns=['Depth (µm)', 'O2 (%air)'], index=ls)
                dpen_av[c] = l.mean()

            # update information about actual correction of pH profile
            if 'EP swi depth' in results.keys():
                for c in self.data.keys():
                    if c in results['EP swi depth'].keys():
                        results['EP swi depth'][c] += dpen_av[c]['Depth (µm)']
                    else:
                        results['EP swi depth'][c] = dpen_av[c]['Depth (µm)']
            else:
                results['EP swi depth'] = dpen_av

            # SWI correction as for O2 project
            for c in self.data.keys():
                for s in self.data[c].keys():
                    xnew = [i - dpen_av[c]['Depth (µm)'] for i in self.data[c][s].index]
                    self.data[c][s].index = xnew

            # SWI correction applied only once
            self.continueEP_button.setEnabled(False)
            results['EP swi adjusted'] = self.data

    def continue_EPIII(self):
        # update status for process control
        self.status_EP += 1

        # identify closest value in list
        core_select = closest_core(ls_core=self.ls_core, core=self.sliderEP.value())

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
                                    ls_core=self.ls_core, scale=scale_plot, ls='-', fig=self.figEP, ax=self.axEP)
        self.figEP.canvas.draw()

        # !!!TODO: allow de-checking of sample (which is not an EP signal) in figure plot




        # slider initialized to first core
        self.sliderEP.setValue(int(core_select)), self.sldEP_label.setText('core: {}'.format(int(core_select)))

        # when slider value change (on click), return new value and update figure plot
        self.sliderEP.valueChanged.connect(self.sliderEP_update)

    def adjust_EP(self):
        # open dialog window to adjust data presentation
        self.status_EP = 1.5

        global wAdjustEP
        wAdjustEP = AdjustpHWindowEP()
        if wAdjustEP.isVisible():
            pass
        else:
            wAdjustEP.show()

    def save_EP(self):
        print('TODO: implement EP saving')

    def reset_EPpage(self):
        # update status for process control
        self.status_EP = 0

        # connect plot button to first part
        self.continueEP_button.disconnect()
        self.continueEP_button.clicked.connect(self.continue_EP)
        self.continueEP_button.setEnabled(True)
        self.adjustEP_button.setEnabled(False)
        self.swi_edit.setEnabled(False)

        # reset slider
        self.count = 0
        self.sliderEP.setValue(int(min(self.ls_core))), self.sldEP_label.setText('core: --')
        self.sliderEP.disconnect()
        self.sliderEP.valueChanged.connect(self.sliderEP_update)

        # clear SWI correction
        self.swi_edit.setText('--')
        self.swiEP_box.setVisible(True), self.swiEP_box.setEnabled(False)
        self.swiEP_box.setChecked(False)

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


class AdjustpHWindowEP(QDialog):
    def __init__(self, sliderValue, ls_core, ddata, scale, col, figEP, axEP, swiEP_box, swiEP_edit, status):
        super().__init__()
        self.initUI()

        # get the transmitted data
        self.figEP, self.axEP, self.ddata, self.scale0, self.colEP = figEP, axEP, ddata, scale, col
        self.ls_core, self.swiEP_box, self.status_EP = ls_core, swiEP_box, status
        self.swiEP_edit = swiEP_edit
        self.ls = '-.' if self.status_EP == 0 else '-'

        # return current core - and get the samples to plot (via slider selection)
        self.Core = min(self.ls_core, key=lambda x: abs(x - sliderValue))

        # plot all samples from current core
        ep_nr = min(self.ddata[self.Core].keys())

        # get pH data and in case apply depth correction in case it was done for H2S / total sulfide
        fig, self.ax1 = plot_adjustEP(core=self.Core, sample=ep_nr, col=self.colEP, dfCore=self.ddata[self.Core],
                                      scale=self.scale0, fig=self.figEPs, ax=self.axEPs)

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
        self.setGeometry(650, 180, 600, 300)

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
        self.figH2Ss, self.axH2Ss = plt.subplots(figsize=(5, 3))
        self.figH2Ss.set_facecolor("none")
        self.canvasH2Ss = FigureCanvasQTAgg(self.figH2Ss)
        self.axH2Ss.set_xlabel('H2S / µmol/l'), self.axH2Ss.set_ylabel('Depth / µm')
        self.axH2Ss.invert_yaxis()
        self.figH2Ss.subplots_adjust(bottom=0.2, right=0.95, top=0.85, left=0.15)
        sns.despine()

        # define pH range
        H2Strim_label = QLabel(self)
        H2Strim_label.setText('H2S range: '), H2Strim_label.setFont(QFont('Helvetica Neue', 12))
        self.H2Strim_edit = QLineEdit(self)
        self.H2Strim_edit.setValidator(QRegExpValidator()), self.H2Strim_edit.setAlignment(Qt.AlignRight)
        self.H2Strim_edit.setMaximumHeight(int(fs_font*1.5))

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
        MsgGp.setMinimumWidth(300)
        gridMsg = QGridLayout()
        vbox2_top.addWidget(MsgGp)
        MsgGp.setLayout(gridMsg)

        # add GroupBox to layout and load buttons in GroupBox
        gridMsg.addWidget(self.msg, 1, 0)

        # in-between for sample plot
        plotGp = QGroupBox()
        plotGp.setFont(QFont('Helvetica Neue', 12))
        plotGp.setMinimumWidth(300), plotGp.setMinimumHeight(400)
        gridFig = QGridLayout()
        vbox2_middle.addWidget(plotGp)
        plotGp.setLayout(gridFig)

        # add GroupBox to layout and load buttons in GroupBox
        gridFig.addWidget(self.slider1H2S, 1, 1)
        gridFig.addWidget(self.sldH2S1_label, 1, 0)
        gridFig.addWidget(self.canvasH2Ss, 2, 1)
        gridFig.addWidget(H2Strim_label, 3, 0)
        gridFig.addWidget(self.H2Strim_edit, 3, 1)

        # bottom group for navigation panel
        naviGp = QGroupBox("Navigation panel")
        naviGp.setFont(QFont('Helvetica Neue', 12))
        naviGp.setMinimumWidth(300), naviGp.setFixedHeight(75)
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

        # allow only discrete values according to existing cores
        sample_select = min(self.ddata[self.Core].keys(), key=lambda x: abs(x - self.slider1EP.value()))

        # update slider position and label
        self.slider1EP.setValue(sample_select)
        self.sldEP1_label.setText('sample: {}'.format(sample_select))

        fig, self.ax1 = plot_adjustEP(core=self.Core, sample=sample_select, dfCore=self.ddata[self.Core], col=self.colEP,
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
        scaleEP = (round(self.scale[0], 2), round(self.scale[1], 2))

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
        if self.ls_out:
            dcore_crop = self.popData_EP(dcore_crop=dcore_crop)

        # update the general dictionary
        self.ddata[self.Core][s] = dcore_crop
        fig = plot_EPUpdate(core=self.Core, nr=s, df=dcore_crop, ddcore=self.ddata[self.Core], col=self.colEP,
                            scale=self.scale, ax=self.axEPs, fig=self.figEPs)
        self.figEPs.canvas.draw()

        #  update range for pH plot and plot in main window
        self.EPtrim_edit.setText(str(round(self.scale[0], 2)) + ' - ' + str(round(self.scale[1], 2)))
        fig0 = plot_initalProfile(data=self.ddata, para='EP', unit='mV', col_name='EP_mV', core=self.Core, ls=self.ls,
                                  ls_core=self.ddata.keys(), scale=self.scale, fig=self.figEP, ax=self.axEP)
        self.figEP.canvas.draw()
        self.status_EP += 1

    def resetPlotEP(self):
        print('start all over again and use the raw data')

    def close_windowEP(self):
        self.hide()


def plot_initalProfile(data, para, unit, col_name, core, ls_core, scale, ls='-.', fig=None, ax=None, show=True):
    plt.ioff()
    # identify closest value in list
    core_select = closest_core(ls_core=ls_core, core=core)

    # initialize figure
    if ax is None:
        fig, ax = plt.subplots(figsize=(3, 4))
    else:
        ax.cla()
    ax.set_xlabel('{} / {}'.format(para, unit)), ax.set_ylabel('Depth / µm')
    ax.invert_yaxis()

    if core_select != 0:
        ax.title.set_text('{} depth profile for core {}'.format(para, core_select))
        ax.axhline(0, lw=.5, color='k')
        for en, nr in enumerate(data[core_select].keys()):
            lw = 0.75 if ls == '-.' else 1.
            mark = '.' if ls == '-.' else None
            ax.plot(data[core_select][nr][col_name], data[core_select][nr].index, lw=lw, ls=ls, marker=mark, alpha=0.75,
                    color=ls_col[en], label='sample ' + str(nr))
        ax.legend(frameon=True, fontsize=10)

    # update layout
    scale_min = -1 * scale[1]/10 if scale[0] == 0 else scale[0]*0.95
    ax.set_xlim(scale_min, scale[1]*1.015)
    fig.tight_layout(pad=1.5)

    if show is False:
        plt.close(fig)
    else:
        fig.canvas.draw()
    return fig


def plot_adjustEP(core, sample, col, dfCore, scale, fig=None, ax=None):
    # initialize first plot with first core and sample
    fig, ax1 = GUI_adjustDepthEP(core=core, nr=sample, dfCore=dfCore, col=col, scale=scale, fig=fig, ax=ax)
    fig.canvas.draw()
    return fig, ax1


def plot_EPUpdate(core, nr, df, ddcore, scale, col, fig, ax):
    # clear coordinate system but keep the labels
    ax.cla()
    ax.title.set_text('EP profile for core {} - sample {}'.format(core, nr))
    ax.set_xlabel('EP / mV'), ax.set_ylabel('Depth / µm')

    # plotting part
    ax.axhline(0, lw=.5, color='k')
    for en in enumerate(ddcore.keys()):
        if en[1] == nr:
            pos = en[0]
    ax.plot(df[col], df.index, lw=0.75, ls='-.', marker='.', ms=4, color=ls_col[pos], alpha=0.75)

    # general layout
    scale_min = -1 * scale[1]/10 if scale[0] == 0 else scale[0]*0.95
    ax.invert_yaxis(), ax.set_xlim(scale_min, scale[1]*1.015)
    sns.despine(), plt.subplots_adjust(bottom=0.2, right=0.95, top=0.8, left=0.15)
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
        ax.title.set_text('EP profile for core {} - sample {}'.format(core, nr))
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
    ax.invert_yaxis(), ax.set_xlim(scale_min, scale[1]*1.015)
    sns.despine(), fig.subplots_adjust(bottom=0.2, right=0.95, top=0.8, left=0.15)

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


# -----------------------------------------------
# general classes may apply to different wizard pages
class SalConvWindowO2(QDialog):
    def __init__(self, temp_edit_degC, salinity_edit):
        super().__init__()
        # get transferred parameter
        self.temp_degC = float(temp_edit_degC)
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
        self.msg.setWordWrap(True), self.msg.setFont(QFont('Helvetica Neue', int(fs_font*1.15)))

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
        self.temp_edit.setMaximumWidth(100), self.temp_edit.setText(str(self.temp_degC))

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
        MsgGp.setMinimumWidth(300)
        gridMsg = QGridLayout()
        vbox2_top.addWidget(MsgGp)
        MsgGp.setLayout(gridMsg)

        # add GroupBox to layout and load buttons in GroupBox
        gridMsg.addWidget(self.msg, 1, 0)

        # in-between for input parameter
        plotGp = QGroupBox("User input")
        plotGp.setFont(QFont('Helvetica Neue', 12))
        plotGp.setMinimumWidth(250), plotGp.setMinimumHeight(200)
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
        naviGp.setMinimumWidth(250), naviGp.setFixedHeight(75)
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
            salinity = sal.SalCon_Converter(temp_degC=self.temp_degC, p_dbar=10/1*float(self.atm_edit.text()), M=0,
                                            cnd=float(self.cnd_edit.text()))
            self.sal_edit.setText(str(round(salinity, 3)))
            results['salinity PSU'] = salinity

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
