"""
Qt5 GUI for making OFET measurements with a Keithley 2636.

Author:  Ross <peregrine dot warren at physics dot ox dot ac dot uk>
         Maurice <maurice.townsendblake@qut.edu.au>

"""

import k2636  # Driver
import config # adjustable parameters
import sys
import fnmatch
import pandas as pd
from PyQt5.QtCore import pyqtSignal, Qt, QObject
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (QMainWindow, QDockWidget, QWidget, QDesktopWidget,
                             QApplication, QGridLayout, QPushButton, QLabel,
                             QDoubleSpinBox, QAction, qApp, QSizePolicy,
                             QTextEdit, QFileDialog, QInputDialog, QLineEdit,
                             QMessageBox, QComboBox)

import matplotlib
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as mplToolb
import matplotlib.style as style
from matplotlib.figure import Figure

matplotlib.use("Qt5Agg")


class mainWindow(QMainWindow):
    """Create mainwindow of GUI."""

    def __init__(self):
        """Initalise mainwindow."""
        super().__init__()
        self.initUI()

    def initUI(self):
        """Make signal connections."""
        # Add central widget
        self.mainWidget = mplWidget()
        self.setCentralWidget(self.mainWidget)

        # Add other window widgets
        self.keithleySettingsWindow = keithleySettingsWindow()
        self.keithleyConnectionWindow = keithleyConnectionWindow()
        self.keithleyErrorWindow = keithleyErrorWindow()
        self.popupWarning = warningWindow()

        # Dock setup
        # Keithley dock widget
        self.buttonWidget = keithleyButtonWidget()
        self.dockWidget1 = QDockWidget('Keithley Control')
        self.dockWidget1.setWidget(self.buttonWidget)
        self.addDockWidget(Qt.BottomDockWidgetArea, self.dockWidget1)

        # Console stream widget
        self.console = consoleStreamWidget()
        self.dockConsole = QDockWidget('Console')
        self.dockConsole.setWidget(self.console)
        self.addDockWidget(Qt.RightDockWidgetArea, self.dockConsole)
        self.stdout_stream = EmittingStream()
        self.stdout_stream.text_written.connect(self.console.console.append)
        sys.stdout = self.stdout_stream
        sys.stderr = self.stdout_stream


        # Matplotlib control widget
        self.dockWidget2 = QDockWidget('Plotting controls')
        self.dockWidget2.setWidget(mplToolb(self.mainWidget, self))
        self.addDockWidget(Qt.BottomDockWidgetArea, self.dockWidget2)

        # Menu bar setup
        # Shutdown program
        exitAction = QAction('&Exit', self)
        exitAction.setShortcut('Ctrl+Q')
        exitAction.setStatusTip('Exit application')
        exitAction.triggered.connect(qApp.quit)
        # Load old data
        loadAction = QAction('&Load', self)
        loadAction.setShortcut('Ctrl+L')
        loadAction.setStatusTip('Load data to be displayed')
        loadAction.triggered.connect(self.showFileOpen)
        # Load old ALL data
        loadALLAction = QAction('&Load ALL', self)
        loadALLAction.setShortcut('Ctrl+A')
        loadALLAction.setStatusTip(
            'Load iv, output and transfer data to be displayed')
        loadALLAction.triggered.connect(self.showFileOpenALL)
        # Clear data
        clearAction = QAction('Clear', self)
        clearAction.setShortcut('Ctrl+C')
        clearAction.setStatusTip('Clear data on graph')
        clearAction.triggered.connect(self.mainWidget.clear)
        # Keithley settings popup
        keithleyAction = QAction('Settings', self)
        keithleyAction.setShortcut('Ctrl+K')
        keithleyAction.setStatusTip('Adjust scan parameters')
        keithleyConAction = QAction('Connect', self)
        keithleyConAction.setShortcut('Ctrl+J')
        keithleyConAction.setStatusTip('Reconnect to keithley 2636')
        keithleyAction.triggered.connect(self.keithleySettingsWindow.show)
        keithleyConAction.triggered.connect(self.keithleyConnectionWindow.show)
        keithleyError = QAction('Error Log', self)
        keithleyError.setShortcut('Ctrl+E')
        keithleyError.triggered.connect(self.keithleyErrorWindow.show)

        # Add items to menu bars
        menubar = self.menuBar()
        fileMenu = menubar.addMenu('&File')
        fileMenu.addAction(loadAction)
        fileMenu.addAction(loadALLAction)
        fileMenu.addAction(clearAction)
        fileMenu.addSeparator()
        fileMenu.addAction(exitAction)
        keithleyMenu = menubar.addMenu('&Keithley')
        keithleyMenu.addAction(keithleyConAction)
        keithleyMenu.addAction(keithleyAction)
        keithleyMenu.addAction(keithleyError)

        # Status bar setup
        self.statusbar = self.statusBar()

        # Attempt to connect to a keithley
        self.testKeithleyConnection()
        self.keithleyConnectionWindow.connectionSig.connect(self.buttonWidget.showButtons)

        # Window setup
        self.resize(800, 800)
        self.centre()
        self.setWindowTitle('K2636 Control Application')
        self.show()

    def testKeithleyConnection(self):
        """Connect to the keithley on initialisation."""
        try:
            self.keithley = k2636.K2636(address=config.ADDRESS,
                                        read_term='\n', baudrate=57600)
            self.statusbar.showMessage('Keithley found.')
            self.buttonWidget.showButtons()
            self.keithley.closeConnection()
        except ConnectionError:
            self.buttonWidget.hideButtons()
            self.statusbar.showMessage('Not connected to Keithly. Check address and connection.')

    def centre(self):
        """Find screen size and place in centre."""
        screen = QDesktopWidget().screenGeometry()
        size = self.geometry()
        self.move((int(round(screen.width()-size.width())/2)),
                    int(round((screen.height()-size.height())/2)))

    def showFileOpen(self):
        """Pop up for file selection."""
        filt1 = '*.csv'
        fname = QFileDialog.getOpenFileName(self, 'Open file', filter=filt1)
        if fname[0]:
            try:
                df = pd.read_csv(fname[0], sep='\t')
                if fnmatch.fnmatch(fname[0], '*transfer.csv'):
                    self.mainWidget.drawTransfer(df)
                else:
                    raise FileNotFoundError
            except KeyError or FileNotFoundError:
                self.popupWarning.showWindow('Unsupported file.')

    def showFileOpenALL(self):
        """Pop up for file selection for ALL measurements."""
        filt1 = '*.csv'
        fname = QFileDialog.getOpenFileName(self, 'Open file', filter=filt1)
        if fname[0]:
            try:
                fileN = fname[0]
                if fnmatch.fnmatch(fname[0], '*transfer.csv'):
                    fileN = fileN[:-21]
                self.mainWidget.drawAll(fileN)

            except KeyError or FileNotFoundError:
                self.popupWarning.showWindow('Unsupported file.')


    def updateStatusbar(self, s):
        """Put text in status bar."""
        self.statusbar.showMessage(s)


class keithleyButtonWidget(QWidget):
    """Defines class with buttons controlling keithley."""

    def __init__(self):
        """Initialise setup of widget."""
        super().__init__()
        self.initWidget()

    def initWidget(self):
        """Initialise connections."""
        # Set widget layout
        grid = QGridLayout()
        self.setLayout(grid)

        # Push button setup
        self.transferBtn = QPushButton('Transfer Sweep')
        grid.addWidget(self.transferBtn, 1, 3)
        self.transferBtn.clicked.connect(self.showSampleNameInput)

        self.cancelBtn = QPushButton('Cancel Operation')
        grid.addWidget(self.cancelBtn, 2, 3)
        

    def showSampleNameInput(self):
        """Popup for sample name input."""
        samNam = QInputDialog()
        try:
            text, ok = samNam.getText(self, 'Sample Name',
                                        'Enter sample name:',
                                        QLineEdit.Normal,
                                        str(self.SampleName))

        except AttributeError:
            text, ok = samNam.getText(self, 'Sample Name',
                                        'Enter sample name:')
        if ok:
            if text != '':  # to catch empty input
                self.SampleName = str(text)
        else:
            self.SampleName = None

    def hideButtons(self):
        """Hide control buttons."""
        self.transferBtn.setEnabled(False)

    def showButtons(self):
        """Show control buttons."""
        self.transferBtn.setEnabled(True)


class mplWidget(FigureCanvas):
    """Widget for matplotlib figure."""

    def __init__(self, parent=None):
        """Create plotting widget."""
        self.initWidget()

    def initWidget(self, parent=None, width=5, height=4, dpi=100):
        """Set parameters of plotting widget."""
        style.use('ggplot')  # Looks the best?

        self.fig = Figure(figsize=(width, height), dpi=dpi)
        self.ax1 = self.fig.add_subplot(111)

        self.ax1.set_title('IV')
        self.ax1.set_xlabel('Channel Voltage [V]')
        self.ax1.set_ylabel('Channel Current [A]')

        FigureCanvas.__init__(self, self.fig)
        self.setParent(parent)
        FigureCanvas.setSizePolicy(self, QSizePolicy.Expanding,
                                    QSizePolicy.Expanding)
        FigureCanvas.updateGeometry(self)

    def drawTransfer(self, df):
        """Take a data frame and draw it."""
        self.ax1 = self.fig.add_subplot(111)
        self.ax1.semilogy(df['Gate Voltage [V]'],
                            abs(df['Channel Current [A]']), '.')
        self.ax1.set_title('Transfer Curve')
        self.ax1.set_xlabel('Gate Voltage [V]')
        self.ax1.set_ylabel('Channel Current [A]')
        FigureCanvas.draw(self)

    def clear(self):
        """Clear the plot."""
        self.fig.clear()
        FigureCanvas.draw(self)


class keithleySettingsWindow(QWidget):
    """Keithley settings popup."""

    def __init__(self):
        """Initialise setup."""
        super().__init__()
        self.initWidget()

    def initWidget(self):
        """Initialise connections."""
        # Set widget layout
        grid = QGridLayout()
        self.setLayout(grid)
        # Columns
        col1 = QLabel('Initial Voltage')
        col2 = QLabel('Final Voltage')
        col3 = QLabel('Voltage Step')
        col4 = QLabel('Step Time')
        grid.addWidget(col1, 1, 2)
        grid.addWidget(col2, 1, 3)
        grid.addWidget(col3, 1, 4)
        grid.addWidget(col4, 1, 5)
        # Rows
        row1 = QLabel('IV')
        row2 = QLabel('Ouput')
        row3 = QLabel('Transfer')
        grid.addWidget(row1, 2, 1)
        grid.addWidget(row2, 3, 1)
        grid.addWidget(row3, 4, 1)

        # transfer Settings
        transferFirstV = QDoubleSpinBox(self)
        grid.addWidget(transferFirstV, 4, 2)
        transferLastV = QDoubleSpinBox(self)
        grid.addWidget(transferLastV, 4, 3)
        transferStepV = QDoubleSpinBox(self)
        grid.addWidget(transferStepV, 4, 4)
        transferStepT = QDoubleSpinBox(self)
        grid.addWidget(transferStepT, 4, 5)
        
        # OK button
        setSettings = QPushButton('Ok')
        grid.addWidget(setSettings, 5, 4)
        
        # Cancel button
        cancelSet = QPushButton('Cancel')
        grid.addWidget(cancelSet, 5, 5)
        cancelSet.clicked.connect(self.close)
        
        # Window setup
        self.centre()
        self.setWindowTitle('K2636 - Settings')

    def centre(self):
        """Find screen size and place in centre."""
        screen = QDesktopWidget().screenGeometry()
        size = self.geometry()
        self.move((int(round(screen.width()-size.width())/2)),
                    (int(round(screen.height()-size.height())/2)))

class keithleyConnectionWindow(QWidget):
    """Popup for connecting to instrument."""

    connectionSig = pyqtSignal()

    def __init__(self):
        """Initialise setup."""
        super().__init__()
        self.initWidget()

    def initWidget(self):
        """Initialise connections."""
        # Set widget layout
        grid = QGridLayout()
        self.setLayout(grid)

        # Connection status box
        self.connStatus = QLabel('Connect to Keithly. Ensure correct device address.')
        self.connAddress = QLineEdit(config.ADDRESS)
        self.connButton = QPushButton('Connect')
        self.connButton.clicked.connect(self.reconnect2keithley)
        grid.addWidget(self.connStatus, 1, 1)
        grid.addWidget(self.connAddress,2, 1)
        grid.addWidget(self.connButton, 3, 1)

        # Window setup
        self.resize(300, 100)
        self.centre()
        self.setWindowTitle('K2636 - Connecting')

    def centre(self):
        """Find screen size and place in centre."""
        screen = QDesktopWidget().screenGeometry()
        size = self.geometry()
        self.move((int(round(screen.width()-size.width()) / 2)),
                    int(round((screen.height()-size.height()) / 2)))

    def reconnect2keithley(self):
        """Reconnect to instrument."""
        try:
            self.keithley = k2636.K2636(address=self.connAddress.text(),
                                        read_term='\n', baudrate=57600)
            self.connStatus.setText('Connection successful')
            self.connectionSig.emit()
            self.keithley.closeConnection()
            if config.ADDRESS != self.connAddress.text():
                config.set_address(self.connAddress.text())

        except ConnectionError:
            self.connStatus.setText('No Keithley can be found at specified address')



class keithleyErrorWindow(QWidget):
    """Popup for reading error messages."""

    def __init__(self):
        """Initialise setup."""
        super().__init__()
        self.initWidget()

    def initWidget(self):
        """Initialise connections."""
        # Set widget layout
        grid = QGridLayout()
        self.setLayout(grid)

        # Connection status box
        self.errorStatus = QTextEdit('ERROR CODE------------------MESSAGE')
        self.errorButton = QPushButton('Read error')
        self.errorButton.clicked.connect(self.readError)
        grid.addWidget(self.errorStatus, 1, 1)
        grid.addWidget(self.errorButton, 2, 1)

        # Window setup
        self.resize(600, 300)
        self.centre()
        self.setWindowTitle('K2636 - Error Log')

    def centre(self):
        """Find screen size and place in centre."""
        screen = QDesktopWidget().screenGeometry()
        size = self.geometry()
        self.move((int(round(screen.width()-size.width()) / 2)),
                    int(round((screen.height()-size.height()) / 2)))

    def readError(self):
        """Reconnect to instrument."""
        self.keithley = k2636.K2636(address='ASRL/dev/ttyUSB0',
                                    read_term='\n', baudrate=57600)

        self.keithley._write('errorCode, message, severity, errorNode' +
                                '= errorqueue.next()')
        self.keithley._write('print(errorCode, message)')
        error = self.keithley._query('')
        self.errorStatus.append(error)
        self.keithley.closeConnection()


class warningWindow(QWidget):
    """Warning window popup."""

    def __init__(self):
        """Intial setup."""
        super().__init__()
        self.initWidget()

    def initWidget(self):
        """Initialise connections."""
        # Set widget layout
        grid = QGridLayout()
        self.setLayout(grid)

        # Connection status box
        self.warning = QLabel()
        self.continueButton = QPushButton('Continue')
        self.continueButton.clicked.connect(self.hide)
        grid.addWidget(self.warning, 1, 1)
        grid.addWidget(self.continueButton, 2, 1)

        # Window setup
        self.resize(180, 80)
        self.centre()
        self.setWindowTitle('Error!')

    def centre(self):
        """Find screen size and place in centre."""
        screen = QDesktopWidget().screenGeometry()
        size = self.geometry()
        self.move((int(round(screen.width()-size.width()) / 2)),
                    int(round((screen.height()-size.height()) / 2)))

    def showWindow(self, s):
        """Write error message and show window."""
        self.warning.setText(s)
        self.show()

# STDERR and STDOUT redirects for console debug
class consoleStreamWidget(QWidget):
    """Console widget"""
    def __init__(self):
        super().__init__()
        self.initWidget()
    def initWidget(self):
        grid = QGridLayout()
        self.setLayout(grid)
        self.console = QTextEdit('Initialised console')
        self.console.setReadOnly(True)

        font =  QFont("Courier New")
        font.setStyleHint(QFont.Monospace)
        font.setPointSize(10)
        self.console.setFont(font)


        grid.addWidget(self.console, 0,0)

class EmittingStream(QObject):
    text_written = pyqtSignal(str)

    def write(self, text):
        self.text_written.emit(str(text))

    def flush(self):
        pass



if __name__ == '__main__':

        app = QApplication(sys.argv)
        GUI = mainWindow()
        sys.exit(app.exec_())
