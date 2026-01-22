#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
main program linking gui and measurement thread.

Author:  Ross <peregrine dot warren at physics dot ox dot ac dot uk>
         Maurice <maurice.townsendblake@qut.edu.au>

"""

import GUI
import device  # driver for keithly
import sys
import time
import pandas as pd
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtWidgets import QApplication
from device import UserCancelledError


class GUI(GUI.mainWindow):
    """GUI linked to measurement thread."""

    def __init__(self):
        """Take GUI and add measurement thread connection."""
        super().__init__()
        self.params = {}  # for storing parameters
        self.measureThread = None
        self.keithley = None
        self.setupConnections()

    def setupConnections(self):
        """Connect the GUI to the measurement thread."""
        self.buttonWidget.transferBtn.clicked.connect(self.transferSweep)
        self.buttonWidget.cancelBtn.clicked.connect(self.cancelOperation)

    def cancelOperation(self):
        """Cancel any pending instrument functions and request measurement thread to stop."""
        self.statusbar.showMessage('Cancelling...')
        if self.measureThread and self.measureThread.isRunning():
            try:
                self.measureThread.requestCancel()
            except:
                pass
        else:
            try:
                temp = device.K2636()
                temp.cancelOperation()
                temp.closeConnection()
            except:
                pass
            self.statusbar.showMessage('No operation to cancel')

    def transferSweep(self, event):
        """Perform transfer sweep."""
        try:
            if self.buttonWidget.SampleName is None:
                raise AttributeError
            self.params['Sample name'] = self.buttonWidget.SampleName
            self.statusbar.showMessage('Performing Transfer Sweep...')
            self.buttonWidget.hideButtons()
            self.params['Measurement'] = 'transfer'

            # Create a single K2636 instance and pass it to the worker thread so
            # both GUI (cancel) and the thread operate on the same instrument.
            self.keithley = device.K2636()
            self.measureThread = measureThread(self.params, self.keithley)
            self.measureThread.finishedSig.connect(self.done)
            self.measureThread.errorSig.connect(self.error)
            self.measureThread.dataUpdateSig.connect(self.updateRealTimeDisplay)
            self.measureThread.start()
        except AttributeError:
            self.popupWarning.showWindow('No sample name given!')

    def done(self):
        """Update display when finished measurement."""
        self.statusbar.showMessage('Operations done')
        if self.measureThread:
            try:
                if self.keithley:
                    self.keithley.closeConnection()
            except:
                pass
            self.keithley = None
        # self.dislpayMeasurement()
        self.buttonWidget.showButtons()

    def updateRealTimeDisplay(self, df):
        """Update the plot with real-time data."""
        if df is not None and not df.empty:
            self.mainWidget.clear()
            self.mainWidget.drawTransfer(df)

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
    progressSig = pyqtSignal(str)
    dataUpdateSig = pyqtSignal(pd.DataFrame)

    def __init__(self, params, keithley):
        """Initialise thread with params and a shared keithley instance."""
        QThread.__init__(self)
        self.params = params
        self.keithley = keithley
        self._cancel_requested = False

    def requestCancel(self):
        """Request cancellation: tell the instrument to abort and flag the thread."""
        self._cancel_requested = True

    def __del__(self):
        """When thread is deconstructed wait for porcesses to complete."""
        self.wait()

    def run(self):
        """Logic to be run in background thread."""
        begin_measure = time.time()
        finish_measure = time.time()
        try:
            # Use the shared keithley instance passed from the GUI
            keithley = self.keithley
            begin_measure = time.time()

            if self.params['Measurement'] == 'transfer':
                df_callback = lambda df: self.dataUpdateSig.emit(df)
                keithley.Transfer(
                    self.params['Sample name'],
                    cancel_check=lambda: self._cancel_requested,
                    data_callback=df_callback
                    )

            finish_measure = time.time()
            self.finishedSig.emit()

        except UserCancelledError:
            finish_measure = time.time()
            self.finishedSig.emit()
        except Exception as e:
            finish_measure = time.time()
            self.errorSig.emit(str(e))

        finally:
            pass

        print('-------------------------------------------\nAll measurements complete. Total time %.2f mins.'
                  % ((finish_measure - begin_measure) / 60))


if __name__ == '__main__':
    app = QApplication(sys.argv)
    mainGUI = GUI()
    sys.exit(app.exec_())
