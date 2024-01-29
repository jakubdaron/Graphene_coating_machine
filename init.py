import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QPushButton, QLineEdit
from PyQt5.uic import loadUi
from PyQt5.QtCore import pyqtSignal, QObject, QEventLoop, QTimer, Qt
import serial
import serial.tools.list_ports
import time


class Communicate(QObject):
    buttonClicked = pyqtSignal()


class MainWindow(QMainWindow):  # The main window class of the application that manages the process of graphene coating
    def __init__(self, ui_file, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowMinimizeButtonHint | Qt.CustomizeWindowHint)
        self.ui_file = ui_file
        self.communicate = Communicate()
        self.setup_ui()
        self.setFixedSize(800, 600)
        self.show()

    def setup_ui(self):
        self.load_ui()
        self.add_button_handler()

    def load_ui(self):
        loadUi(self.ui_file, self)

    def add_button_handler(self):
        button = self.findChild(QPushButton, "pushButton_2")
        button_2 = self.findChild(QPushButton, "pushButton")

        if button_2:
            button_2.clicked.connect(self.handle_button_click_2)
        if button:
            button.clicked.connect(self.handle_button_click)

    def handle_button_click(self):  # Handler of starting graphene coating proces
        self.communicate.buttonClicked.emit()

    def handle_button_click_2(self):  # Handler of closing app button
        self.communicate.buttonClicked.emit()
        sys.exit(0)


class PromptWindow(QWidget):  # The prompt window class with button to continue the process
    def __init__(self, ui_file, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowMinimizeButtonHint | Qt.CustomizeWindowHint)
        self.ui_file = ui_file
        self.communicate = Communicate()
        self.setup_ui()
        self.setFixedSize(410, 120)
        self.show()

    def setup_ui(self):
        self.load_ui()
        self.add_button_handler()

    def load_ui(self):
        loadUi(self.ui_file, self)

    def add_button_handler(self):
        button = self.findChild(QPushButton, "pushButton")
        if button:
            button.clicked.connect(self.handle_button_click)

    def handle_button_click(self):
        self.communicate.buttonClicked.emit()


class ProcessWindow(QWidget):  # Class of processing window
    def __init__(self, parent=None):
        super().__init__(parent)
        self.window = QWidget()
        loadUi("window6.ui", self)
        self.setFixedSize(410, 120)
        self.show()


def signal_check():  # Check every available port to find connection with Arduino UNO
    available_ports = list(serial.tools.list_ports.comports())

    for port, desc, hwid in available_ports:
        print(desc)
        if "CH340" in desc:
            return port  # If found - return the name of port
    return 0  # If not - return 0


def read_data(ser):  # Function that reads sent data from arduino (from Serial.println())
    buffer = b''  # Init of empty buffer
    timeout = time.time() + 1  # Max wait time for data (2 seconds)

    while time.time() < timeout:
        if ser.in_waiting > 0:
            buffer += ser.read(ser.in_waiting)  # Read of available data
            if b'\n' in buffer:
                line, buffer = buffer.split(b'\n', 1)
                return line.decode('utf-8').strip()

    return None  # If the data haven't been read in time


def detection():  # Function for towrope detection
    try:
        ser = serial.Serial(signal_check(), 9600)
        start_time = time.time()
        duration = 6
        counter = 0
        func_num = "s:"

        while time.time() - start_time < duration:
            ser.write(func_num.encode())
            time.sleep(0.1)
            val = read_data(ser)  # Use a function for non-blocking data flow
            if val is not None:
                val = int(val)
                if val > 340:  # If the value is greater than empty machine - start the process
                    counter = counter + 1
                else:
                    counter = 0
            if counter == 5:
                return True
        return False
    except KeyboardInterrupt:
        ser.close()


def realisation(func_str, event_loop):  # Function that realises each function on arduino by sending the function string and then waiting for ending info
    try:
        ser = serial.Serial(signal_check(), 9600)
        start_time = time.time()
        duration = 9999
        close_flag = 0
        time.sleep(3)
        ser.write(func_str.encode())

        while time.time() - start_time < duration:
            val = read_data(ser)  # Use a function for non-blocking data flow
            print(f"Arduino: {val}")
            ending_info = ["Koniec"]
            if val in ending_info:
                break
    except KeyboardInterrupt:
        pass
    finally:
        if 'ser' in locals() and ser.is_open:
            ser.close()

    event_loop.quit()


def wait_for_signal(win_sel):  # Function waiting for button click to continue the process
    event_loop = QEventLoop()
    win_sel.communicate.buttonClicked.connect(event_loop.quit)
    event_loop.exec_()


def wait_for_arduino(func_str):  # Function waiting for signal from arduino
    event_loop = QEventLoop()
    QTimer.singleShot(100, lambda: realisation(func_str, event_loop))
    event_loop.exec_()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win2 = None

    if signal_check() == 0:  # If computer doesn't connect with arduino - display window with error and close
        win2 = PromptWindow('window1.ui')
        win2.communicate.buttonClicked.connect(app.quit)
        wait_for_signal(win2)
        sys.exit()

    while True:

        try:
            win = MainWindow('mainwindow.ui')  # Initialisation of main window
            wait_for_signal(win)
            win.setEnabled(False)

            le = win.findChild(QLineEdit, "lineEdit")  # Reading value typed in line windows in main window
            le2 = win.findChild(QLineEdit, "lineEdit_2")
            force = round(float(le.text()), 1)  # Fitting of read force and cycles values
            cycles = int(le2.text())

            if not (0.5 <= force <= 5.0) or not (1 <= cycles <= 12):  # If variables are different from specified ranges in main window - raise a value error
                win2 = PromptWindow('window2.ui')
                wait_for_signal(win2)
                win2.close()
                raise ValueError("Nieprawidłowe wartości force lub cycles")

            print("force:", force)
            print("cycles:", cycles)

            win2 = ProcessWindow()  # Go upwards to "base" point with limit switch
            wait_for_arduino("u:")
            win2.close()

            if not detection():  # If object is not detected on machine table - raise a value error
                win2 = PromptWindow('window_detection.ui')
                wait_for_signal(win2)
                win2.close()
                raise ValueError("Brak wykrycia ciągadła w maszynie")
                #win2.communicate.buttonClicked.connect(app.quit)

            win2 = ProcessWindow()  # Go downwards to detect object on the table
            wait_for_arduino("d:")
            win2.close()

            win2 = ProcessWindow()  # Go upwards with precise amount of steps to prepare for placing graphene powder
            wait_for_arduino("r2000:")
            win2.close()

            win2 = PromptWindow('window4.ui')  # Inform about graphene refill
            wait_for_signal(win2)
            win2.close()

            one_rotation = 3200*1.6  # Steps required to make one rotation (including gear ratio)
            rest = one_rotation % cycles

            for i in range(cycles):  # Including rest from division to divide cycles in most equal way
                if rest > 0:
                    steps = int(one_rotation/cycles) + 1
                    rest -= 1
                else:
                    steps = int(one_rotation/cycles)

                print(steps)

                win2 = ProcessWindow()  # Go downwards to detect object on the table
                wait_for_arduino("d:")
                win2.close()

                win2 = ProcessWindow()  # Perform precise downward movement to get the closest sensor read to given force value
                wait_for_arduino(f"m{force}:")
                win2.close()

                win2 = PromptWindow('window3.ui')  # Inform about running up the electrode
                wait_for_signal(win2)
                win2.close()

                win2 = ProcessWindow()  # Go upwards with precise amount of steps to make enough space for table spin
                wait_for_arduino("r14000:")
                win2.close()

                win2 = ProcessWindow()  # Spin the table with precise amount of steps
                wait_for_arduino(f"p{steps}:")
                win2.close()

            win2 = ProcessWindow()  # Go downwards to detect object on the table
            wait_for_arduino("d:")
            win2.close()

            win2 = ProcessWindow()  # Perform precise downward movement to get the closest sensor read to given force value
            wait_for_arduino(f"m{force}:")
            win2.close()

            win2 = PromptWindow('window3.ui')  # Inform about running up the electrode
            wait_for_signal(win2)
            win2.close()

            win2 = ProcessWindow()  # Go upwards to "base" point with limit switch
            wait_for_arduino("u:")
            win2.close()

            win2 = ProcessWindow()  # Make a full rotation in opposite direction to compensate cycles spins
            wait_for_arduino(f"p{-1*one_rotation}:")
            win2.close()

            win.setEnabled(True)

        except ValueError as e:
            print("Błąd:", e)
            continue  # Start the while loop from beginning when the error is detected

    sys.exit(app.exec())
