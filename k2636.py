"""
Module for interacting with the Keithley 2636B SMU.
Author:  Ross <peregrine dot warren at physics dot ox dot ac dot uk>
         Maurice <maurice.townsendblake@qut.edu.au>
"""

import pyvisa as visa
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.style as style
import time
import serial
import platform

import config # Used for parameters

class K2636():
    """Class for Keithley control."""

    def __init__(self, address=None, read_term='\n',
                 baudrate=57600):
        """Make instrument connection instantly on calling class."""
        if platform.system() == "Windows":
            try:
                rm = visa.ResourceManager() # Pyvisa backend cannot be used, NI-VISA is used instead
                #self.inst.timeout = 500000 # Backend times out inbetween sweeps, need to fix as it is specific to NI-VISA
            except:
                raise ConnectionError("Cannot find VISA backend on Windows.")
        else:
            try:
                 rm = visa.ResourceManager('@py')
            except:
                raise ConnectionError("Cannot find PY-VISA backend on this machine")

        # Read address from device config
        if address is None:
            address = config.ADDRESS
        self.makeConnection(rm, address, read_term, baudrate)

    def makeConnection(self, rm, address, read_term, baudrate):
        try:
            if any(x in str(address) for x in ('ttyS', 'ttyUSB', 'USB')):
                self.inst = rm.open_resource(config.ADDRESS)
                self.inst.read_termination = str(read_term)
                self.inst.baud_rate = baudrate
                #self.inst.timeout = 500000
            else:
                raise ConnectionError("Unsupported address: {}".format(address))
        except:
            print("CONNECTION ERROR: Check instrument address.")
            raise ConnectionError

    def closeConnection(self):
        """Close connection to keithley."""
        try:
            self.inst.close()

        except(NameError):
            print('CONNECTION ERROR: No connection established.')

        except(AttributeError):
            print('CONNECTION ERROR: No connection established.')

    def _write(self, m):
        """Write to instrument."""
        try:
            assert type(m) == str
            self.inst.write(m)
        except AttributeError:
            print('CONNECTION ERROR: No connection established.')

    def _read(self):
        """Read instrument."""
        r = self.inst.read()
        return r

    def _query(self, s):
        """Query instrument."""
        try:
            r = self.inst.query(s)
            return r
        except serial.SerialException:
            return ('Serial port busy, try again.')
        except FileNotFoundError:
            return ('CONNECTION ERROR: No connection established.')
        except AttributeError:
            print('CONNECTION ERROR: No connection established.')
            return ('CONNECTION ERROR: No connection established.')

    def loadTSP(self, tsp):
        """Load an anonymous TSP script into the K2636 nonvolatile memory."""
        try:
            tsp_dir = config.TSP_DIR
            self._write('loadscript')
            line_count = 1
            for line in open(str(tsp_dir + tsp), mode='r'):
                self._write(line)
                line_count += 1
            self._write('endscript')
            print('----------------------------------------')
            print('Uploaded TSP script: ', tsp)

        except FileNotFoundError:
            print('ERROR: Could not find tsp script. Check path: ' + config.TSP_DIR)
            raise SystemExit

    def runTSP(self):
        """Run the anonymous TSP script currently loaded in the K2636 memory."""
        self._write('script.anonymous.run()')
        print('Measurement in progress...')

    def readBuffer(self):
        """Read buffer in memory and return an array."""
        try:
            vg = [float(x) for x in self._query('printbuffer' +
                  '(1, smua.nvbuffer1.n, smua.nvbuffer1.sourcevalues)').split(',')]
            ig = [float(x) for x in self._query('printbuffer' +
                  '(1, smua.nvbuffer1.n, smua.nvbuffer1.readings)').split(',')]
            vd = [float(x) for x in self._query('printbuffer' +
                  '(1, smub.nvbuffer1.n, smub.nvbuffer1.sourcevalues)').split(',')]
            c = [float(x) for x in self._query('printbuffer' +
                 '(1, smub.nvbuffer1.n, smub.nvbuffer1.readings)').split(',')]

            df = pd.DataFrame({'Gate Voltage [V]': vg,
                               'Channel Voltage [V]': vd,
                               'Channel Current [A]': c,
                               'Gate Leakage [A]': ig})
            return df

        except serial.SerialException:
            print('Cannot read buffer.')
            return  

    def DisplayMeasurement(self, sample):
        """Show graphs of measurements."""
        try:
            style.use('ggplot')
            fig, ([ax1, ax2], [ax3, ax4]) = plt.subplots(2, 2, figsize=(20, 10),
                                                         dpi=80, facecolor='w',
                                                         edgecolor='k')

            df1 = pd.read_csv(str(sample+'-transfer.csv'), '\t')
            ax1.plot(df1['Gate Voltage [V]'],
                     df1['Channel Current [A]'], '.')
            ax1.set_title('Transfer Curves')
            ax1.set_xlabel('Gate Voltage [V]')
            ax1.set_ylabel('Channel Current [A]')

            fig.tight_layout()
            fig.savefig(sample)
            plt.show()

        except(FileNotFoundError):
            print('Sample name not found.')

    def Output(self, sample):
        """K2636 Output sweeps."""
        try:
            begin_time = time.time()
            self.loadTSP('output-charact.tsp')
            self.runTSP()
            df = self.readBuffer()
            output_name = str(sample + '-output.csv')
            df.to_csv(output_name, sep='\t', index=False)
            finish_time = time.time()
            print('Output sweeps complete. Elapsed time %.2f mins.'
                  % ((finish_time - begin_time) / 60))

        except(AttributeError):
            print('Cannot perform output sweep: no keithley connected.')

    def Transfer(self, sample):
        """K2636 Transfer sweeps."""
        try:
            begin_time = time.time()
            self.loadTSP('transfer-charact.tsp')
            self.runTSP()
            while True:
                line = self.inst.read() # read single line printed from keithly
                if line[:2] == "@@": # Realtime data sent by keithly
                    print("Received: " + line)
                elif line[:2] == "EE": # Terminating characters
                    break
            df = self.readBuffer()
            output_name = str(sample + '-neg-pos-transfer.csv')
            df.to_csv(output_name, sep='\t', index=False)

            # transfer reverse scan
            self.loadTSP('transfer-charact-2.tsp')
            self.runTSP()
            df = self.readBuffer()
            output_name = str(sample + '-pos-neg-transfer.csv')
            df.to_csv(output_name, sep='\t', index=False)

            finish_time = time.time()
            print('Transfer curves measured. Elapsed time %.2f mins.'
                  % ((finish_time - begin_time) / 60))

        except(AttributeError):
            print('Cannot perform transfer sweep: no keithley connected.')
########################################################################


if __name__ == '__main__':
    """For testing methods in the K2636 class."""
    keithley = K2636(address='ASRL/dev/ttyUSB0', read_term='\n', baudrate=57600)
    sample = 'blank-20-1'
    keithley.IVsweep(sample)
    # keithley.Output(sample)
    # keithley.Transfer(sample)
    # keithley.DisplayMeasurement(sample)
    keithley.closeConnection()
