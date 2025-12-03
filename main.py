#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
main program linking gui and measurement thread.

Author:  Ross <peregrine dot warren at physics dot ox dot ac dot uk>
         Maurice <maurice.townsendblake@qut.edu.au>

"""

import GUI
import k2636  # driver for keithly
import sys
import time
import pandas as pd
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtWidgets import QApplication


class GUI(GUI.mainWindow):
    """GUI linked to measurement thread."""

    def __init__(self):
        """Take GUI and add measurement thread connection."""
        super().__init__()
        self.params = {}  # for storing parameters
        self.setupConnections()

    def setupConnections(self):
        """Connect the GUI to the measurement thread."""
        self.buttonWidget.transferBtn.clicked.connect(self.transferSweep)

    def transferSweep(self, event):
        """Perform transfer sweep."""
        try:
            if self.buttonWidget.SampleName is None:
                raise AttributeError
            self.params['Sample name'] = self.buttonWidget.SampleName
            self.statusbar.showMessage('Performing Transfer Sweep...')
            self.buttonWidget.hideButtons()
            self.params['Measurement'] = 'transfer'
            self.measureThread = measureThread(self.params)
            self.measureThread.finishedSig.connect(self.done)
            self.measureThread.errorSig.connect(self.error)
            self.measureThread.start()
        except AttributeError:
            self.popupWarning.showWindow('No sample name given!')

    def done(self):
        """Update display when finished measurement."""
        self.statusbar.showMessage('Measurement(s) complete.')
        self.dislpayMeasurement()
        self.buttonWidget.showButtons()

    def error(self, message):
        """Raise error warning."""
        self.popupWarning.showWindow(str(message))
        self.statusbar.showMessage('Measurement error!')
        self.buttonWidget.hideButtons()

    def dislpayMeasurement(self):
        """Display the data on screen."""
        try:
            # TRANSFER graph display
            if self.params['Measurement'] == 'transfer': #TODO: Add functionality to read both forward and reverse transfer graphs
                df = pd.read_csv(f"{self.params['Sample name']}-neg-pos-{self.params['Measurement']}.csv", sep='\t')
                self.mainWidget.clear()
                self.mainWidget.drawTransfer(df)

        except FileNotFoundError:
            self.popupWarning.showWindow('Could not find data!')


class measureThread(QThread):
    """Thread for running measurements."""

    finishedSig = pyqtSignal()
    errorSig = pyqtSignal(str)

    def __init__(self, params):
        """Initialise threads."""
        QThread.__init__(self)
        self.params = params

    def __del__(self):
        """When thread is deconstructed wait for porcesses to complete."""
        self.wait()

    def run(self):
        """Logic to be run in background thread."""
        try:
            keithley = k2636.K2636()
            begin_measure = time.time()

            if self.params['Measurement'] == 'transfer': # only transfer for now
                keithley.Transfer(self.params['Sample name'])

            keithley.closeConnection()
            self.finishedSig.emit()
            finish_measure = time.time()
            print('-------------------------------------------\nAll measurements complete. Total time % .2f mins.'
                  % ((finish_measure - begin_measure) / 60))

        except ConnectionError:
            self.errorSig.emit('No measurement made. Please retry.')
            self.quit()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    mainGUI = GUI()
    sys.exit(app.exec_())
