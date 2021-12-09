"""
@authors: MS. Marco Rutiaga Quezada
          MS. Aarón Castillo Tobías
          Ing. Rogelio García

###############################################################################
command to exe generation:
        pyinstaller --noconsole --icon=icon.ico --add-data data;data app.py
        pyinstaller --icon=icon.ico --add-data data;data app.py
commands for User Experience:
        Reg add HKCU\Software\Microsoft\Windows\CurrentVersion\Policies\System /v DisableTaskMgr /t REG_DWORD /d 1 /f
        taskkill /f /im explorer.exe
        start explorer.exe
###############################################################################
"""

from gui import MainWindow
from manager import Controller

if __name__ == "__main__":
    from PyQt5.QtWidgets import QApplication
    from time import sleep
    import sys

    app = QApplication(sys.argv)
    gui_1 = MainWindow(name = "Interior 1.1", topic = "gui")
    gui_2 = MainWindow(name = "Interior 1.2", topic = "gui_2", parent = gui_1)
    manager = Controller(gui_1)

    gui_2.allow_close = False
    gui_2.show()
    gui_2.move(-1920,0)
    gui_1.showMaximized()
    gui_2.showMaximized()
    
    sys.exit(app.exec_())

