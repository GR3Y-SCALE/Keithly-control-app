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
        try:
            # If a measurement thread is running, request it to cancel. This will call
            # the same K2636.cancelOperation() used by the thread so the instrument
            # abort happens on the shared connection.
            if hasattr(self, 'measureThread') and self.measureThread is not None and self.measureThread.isRunning():
                self.measureThread.cancel()
                self.statusbar.showMessage('Cancelling operation...')
                # Do not block the GUI waiting for the thread here; when the thread exits
                # it will emit finishedSig and UI will be updated in done().
                return

            # If no thread is running, try a standalone cancel (best-effort)
            if self.keithley is None:
                # create a temporary connection to send abort commands
                temp = device.K2636()
                temp.cancelOperation()
                temp.closeConnection()
                print("Cancelled pending operations and reset Keithly!")
            else:
                # If a keithley instance exists on the GUI (not common), use it
                self.keithley.cancelOperation()
                print("Cancelled pending operations on shared Keithley instance.")
        except Exception as e:
            print("Could not cancel pending operations. Check connection.", e)

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

    def __init__(self, params, keithley):
        """Initialise thread with params and a shared keithley instance."""
        QThread.__init__(self)
        self.params = params
        self.keithley = keithley
        self._cancel_requested = False

    def cancel(self):
        """Request cancellation: tell the instrument to abort and flag the thread."""
        self._cancel_requested = True
        try:
            # Use the shared keithley instance to abort any running script on the instrument.
            if self.keithley is not None:
                self.keithley.cancelOperation()
        except Exception:
            pass

    def __del__(self):
        """When thread is deconstructed wait for porcesses to complete."""
        self.wait()

    def run(self):
        """Logic to be run in background thread."""
        try:
            # Use the shared keithley instance passed from the GUI
            keithley = self.keithley
            begin_measure = time.time()

            if self.params['Measurement'] == 'transfer': # only transfer for now
                keithley.Transfer(self.params['Sample name'])

            # Close connection when finished (or if Transfer exits due to abort)
            try:
                keithley.closeConnection()
            except Exception:
                pass

            self.finishedSig.emit()
            finish_measure = time.time()
            print('-------------------------------------------\nAll measurements complete. Total time % .2f mins.'
                  % ((finish_measure - begin_measure) / 60))

        except ConnectionError:
            self.errorSig.emit('No measurement made. Please retry.')
            self.quit()
        except Exception as e:
            # If the operation was cancelled, emit finished to allow GUI to update.
            if self._cancel_requested:
                self.finishedSig.emit()
            else:
                self.errorSig.emit(str(e))
            self.quit()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    mainGUI = GUI()
    sys.exit(app.exec_())
