# -*- coding: utf-8 -*-
"""
@author: MSc. Marco Rutiaga Quezada
"""

from PyQt5.QtWidgets import QDialog, QMainWindow, QLineEdit, QMessageBox, QAction
from PyQt5.QtCore import pyqtSignal, pyqtSlot, Qt, QTimer
from PyQt5.QtGui import QPixmap
from threading import Timer
from os.path import exists
from os import system 
import json 

from gui.view import resources_rc, main, login, scanner, img_popout
from gui.view.comm import MqttClient
from gui.model import Model

class MainWindow (QMainWindow):

    output = pyqtSignal(dict)

    def __init__(self, name = "GUI", topic = "gui", parent = None):
        super().__init__(parent)

        self.model = Model()
        self.ui = main.Ui_main()
        self.qw_login = Login(parent = self)
        self.qw_scanner = Scanner(parent = self)
        self.qw_img_popout = Img_popout(parent = self)
        self.pop_out = PopOut(self)
        
        self.client = MqttClient(self.model, self)
        self.client.subscribe.connect(self.input)
        self.output.connect(self.client.publish)

        self.model.name = name
        self.model.setTopic = topic.lower() + "/set"
        self.model.statusTopic = topic.lower() + "/status"
        self.ui.setupUi(self)
        self.ui.lbl_result.setText("")
        self.ui.lbl_steps.setText("")
        self.ui.lbl_nuts.setText("")
        self.ui.lbl_toolCurrent.setText("")
        self.ui.lbl_user.setText("")
        self.ui.lbl_info1.setText("")
        self.ui.lbl_info2.setText("")
        self.ui.lbl_info3.setText("")
        self.ui.lbl_info4.setText("")
        ######### Modificación para etiqueta PDC-R #########
        self.ui.lbl_boxPDCR.setText("")
        ######### Modificación para etiqueta PDC-R #########
        ######### Modificación para etiqueta MFB-P2 #########
        self.ui.lbl_boxMFBP2.setText("")
        ######### Modificación para etiqueta MFB-P2 #########
        ######### Modificación para etiqueta MFB-E #########
        self.ui.lbl_boxMFBE.setText("")
        ######### Modificación para etiqueta MFB-E #########
        ######### Modificación para etiqueta BATTERY-2 #########
        self.ui.lbl_boxBATTERY2.setText("")
        ######### Modificación para etiqueta BATTERY-2 #########
        ########################################################
        self.ui.lbl_boxPDCP.setText("")
        self.ui.lbl_boxPDCD.setText("")
        self.ui.lbl_boxMFBP1.setText("")
        self.ui.lbl_boxMFBS.setText("")
        self.ui.lbl_boxBATTERY.setText("")
        self.ui.lbl_info5.setText("")
        ########################################################
        self.setWindowTitle(self.model.name)
        self.ui.lineEdit.setFocusPolicy(Qt.StrongFocus)
        self.ui.lineEdit.setPlaceholderText("Fuse boxes QR")
        self.ui.lineEdit.setFocus()
        self.ui.lineEdit.setVisible(False)

        menu = self.ui.menuMenu
        actionLogin = QAction("Login",self)
        actionLogout = QAction("Logout",self)
        actionConfig = QAction("Config",self)
        actionWEB = QAction("WEB",self)
        menu.addAction(actionLogin)
        menu.addAction(actionLogout)
        menu.addAction(actionConfig)
        menu.addAction(actionWEB)
        menu.triggered[QAction].connect(self.menuProcess)


        self.ui.lineEdit.returnPressed.connect(self.qrBoxes)
        self.qw_login.ui.lineEdit.returnPressed.connect( self.login)
        self.qw_login.ui.btn_ok.clicked.connect(self.login)
        self.qw_scanner.ui.btn_ok.clicked.connect(self.scanner)
        self.qw_scanner.ui.lineEdit.returnPressed.connect(self.scanner)
        self.qw_scanner.ui.btn_cancel.clicked.connect(self.qw_scanner.ui.lineEdit.clear)
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.status)
        #self.timer.start(200)

        self.allow_close        = True
        self.cycle_started      = False
        self.shutdown           = False

    def menuProcess(self, q):
        try:
            case = q.text()               
            if case == "Login":
                self.qw_login.ui.lineEdit.setText("")
                self.qw_login.ui.lineEdit.setPlaceholderText("Escanea o escribe tu codigo")
                self.output.emit({"request":"login"})
            elif case == "Logout":
                if self.cycle_started == False:
                    self.qw_login.ui.lineEdit.setText("")
                    self.qw_login.ui.lineEdit.setPlaceholderText("Escanea o escribe tu codigo")
                    self.output.emit({"request":"logout"})
                else:
                    self.pop_out.setText("Ciclo en proceso no se permite el logout")
                    self.pop_out.setWindowTitle("Warning")
                    QTimer.singleShot(2000, self.pop_out.button(QMessageBox.Ok).click)
                    self.pop_out.exec()
            elif case == "Config":
                if self.cycle_started == False:
                    self.output.emit({"request":"config"})
                else:
                    self.pop_out.setText("Ciclo en proceso no se permite la configuración")
                    self.pop_out.setWindowTitle("Warning")
                    QTimer.singleShot(2000, self.pop_out.button(QMessageBox.Ok).click)
                    self.pop_out.exec()
            elif case == "WEB":
                if exists("C:\BIN\WEB.url"):
                    Timer(0.05, self.launchWEB).start()
                else:   
                    self.pop_out.setText("No se encontró la página WEB")
                    self.pop_out.setWindowTitle("Error")
                    QTimer.singleShot(2000, self.pop_out.button(QMessageBox.Ok).click)
                    self.pop_out.exec()
        except Exception as ex:
            print("menuProcess() exceptión: ", ex)

    def launchWEB(self):
        self.output.emit({"WEB": "open"})
        system("C:\BIN\WEB.url")

    @pyqtSlot()
    def status (self):
        try:
            if self.isVisible() != self.model.status["visible"]["gui"]:
                self.model.status["visible"]["gui"] = self.isVisible()
                self.output.emit({"visible": {"gui": self.isVisible()}})
        
            if self.qw_login.isVisible() != self.model.status["visible"]["login"]:
                self.model.status["visible"]["login"] = self.qw_login.isVisible()
                self.output.emit({"visible": {"login": self.qw_login.isVisible()}})

            if self.qw_scanner.isVisible() != self.model.status["visible"]["scanner"]:
                self.model.status["visible"]["scanner"] = self.qw_scanner.isVisible()
                self.output.emit({"visible": {"scanner": self.qw_scanner.isVisible()}})

            if self.pop_out.isVisible() != self.model.status["visible"]["pop_out"]:
                self.model.status["visible"]["pop_out"] = self.pop_out.isVisible()
                self.output.emit({"visible": {"pop_out": self.pop_out.isVisible()}})

        except Exception as ex:
            print("status() exception: ", ex)

    @pyqtSlot()
    def login (self):
        try:
            text = self.qw_login.ui.lineEdit.text()
            if len(text) > 0: 
                self.output.emit({"ID":text})
                self.qw_login.ui.lineEdit.setPlaceholderText("Código de acceso")
            else:
                self.qw_login.ui.lineEdit.setPlaceholderText("Código vacío intenta de nuevo.")
            self.qw_login.ui.lineEdit.clear()
            self.qw_login.ui.lineEdit.setFocus()
        except Exception as ex:
            print("login() exception: ", ex)

    @pyqtSlot()
    def scanner (self):
        try:
            text = self.qw_scanner.ui.lineEdit.text().upper()
            if len(text) > 0: 
                self.output.emit({"code":text})
                self.qw_scanner.ui.lineEdit.setPlaceholderText("Código Qr")
            else:
                self.qw_scanner.ui.lineEdit.setPlaceholderText("Código vacío intenta de nuevo.")
            self.qw_scanner.ui.lineEdit.clear()
            self.qw_scanner.ui.lineEdit.setFocus()
        except Exception as ex:
            print("scanner exception:", ex)

    @pyqtSlot()
    def qrBoxes (self):
        try:
            text = self.ui.lineEdit.text().upper()
            if len(text) > 0: 
                self.output.emit({"qr_box":text})
                self.ui.lineEdit.setPlaceholderText("Fuse boxes QR")
            else:
                self.ui.lineEdit.setPlaceholderText("Fuse boxes QR")
            self.ui.lineEdit.clear()
            #self.ui.lineEdit.setFocus()
        except Exception as ex:
            print("qrBoxes exception:", ex)

    @pyqtSlot(dict)
    def input(self, message):
        try:
            #print(message)
            if "shutdown" in message:
                if message["shutdown"] == True:
                    self.shutdown = True
                    QTimer.singleShot(4000, self.close)
            if "allow_close" in message:
                if type(message["allow_close"]) == bool:
                    self.allow_close = message["allow_close"]
                else:
                    raise ValueError('allow_close must a boolean.')
            if "cycle_started" in message:
                if type(message["cycle_started"]) == bool:
                    self.cycle_started = message["cycle_started"]
                else:
                    raise ValueError('allow_close must a boolean.')
            if "request" in message:
                if message["request"] == "status":
                    QTimer.singleShot(100, self.sendStatus)
            ######### Etiqueta Titulo Raffis #########
            if "lbl_boxTITLE" in message:
                self.ui.lbl_boxTITLE.setText(message["lbl_boxTITLE"]["text"])
                if "color" in message["lbl_boxTITLE"]:
                    self.ui.lbl_boxTITLE.setStyleSheet("color: " + message["lbl_boxTITLE"]["color"])
            ######### Modificación para etiqueta PDC-R #########
            if "lbl_boxPDCR" in message:
                self.ui.lbl_boxPDCR.setText(message["lbl_boxPDCR"]["text"])
                if "color" in message["lbl_boxPDCR"]:
                    self.ui.lbl_boxPDCR.setStyleSheet("color: " + message["lbl_boxPDCR"]["color"])
            ######################################################################################
            if "lbl_boxPDCP" in message:
                self.ui.lbl_boxPDCP.setText(message["lbl_boxPDCP"]["text"])
                if "color" in message["lbl_boxPDCP"]:
                    self.ui.lbl_boxPDCP.setStyleSheet("color: " + message["lbl_boxPDCP"]["color"])
            if "lbl_boxPDCD" in message:
                self.ui.lbl_boxPDCD.setText(message["lbl_boxPDCD"]["text"])
                if "color" in message["lbl_boxPDCD"]:
                    self.ui.lbl_boxPDCD.setStyleSheet("color: " + message["lbl_boxPDCD"]["color"])
            if "lbl_boxMFBP1" in message:
                self.ui.lbl_boxMFBP1.setText(message["lbl_boxMFBP1"]["text"])
                if "color" in message["lbl_boxMFBP1"]:
                    self.ui.lbl_boxMFBP1.setStyleSheet("color: " + message["lbl_boxMFBP1"]["color"])
            if "lbl_boxMFBS" in message:
                self.ui.lbl_boxMFBS.setText(message["lbl_boxMFBS"]["text"])
                if "color" in message["lbl_boxMFBS"]:
                    self.ui.lbl_boxMFBS.setStyleSheet("color: " + message["lbl_boxMFBS"]["color"])
            if "lbl_boxBATTERY" in message:
                self.ui.lbl_boxBATTERY.setText(message["lbl_boxBATTERY"]["text"])
                if "color" in message["lbl_boxBATTERY"]:
                    self.ui.lbl_boxBATTERY.setStyleSheet("color: " + message["lbl_boxBATTERY"]["color"])
            if "lbl_info5" in message:
                self.ui.lbl_info5.setText(message["lbl_info5"]["text"])
                if "color" in message["lbl_info5"]:
                    self.ui.lbl_info5.setStyleSheet("color: " + message["lbl_info5"]["color"])
            ######################################################################################
            ######### Modificación para etiqueta PDC-R #########
            ######### Modificación para etiqueta MFB-P2 #########
            if "lbl_boxMFBP2" in message:
                self.ui.lbl_boxMFBP2.setText(message["lbl_boxMFBP2"]["text"])
                if "color" in message["lbl_boxMFBP2"]:
                    self.ui.lbl_boxMFBP2.setStyleSheet("color: " + message["lbl_boxMFBP2"]["color"])
            ######### Modificación para etiqueta MFB-P2 #########
            ######### Modificación para etiqueta MFB-E #########
            if "lbl_boxMFBE" in message:
                self.ui.lbl_boxMFBE.setText(message["lbl_boxMFBE"]["text"])
                if "color" in message["lbl_boxMFBE"]:
                    self.ui.lbl_boxMFBE.setStyleSheet("color: " + message["lbl_boxMFBE"]["color"])
            ######### Modificación para etiqueta MFB-E #########
            ######### Modificación para etiqueta BATTERY-2 #########
            if "lbl_boxBATTERY2" in message:
                self.ui.lbl_boxBATTERY2.setText(message["lbl_boxBATTERY2"]["text"])
                if "color" in message["lbl_boxBATTERY2"]:
                    self.ui.lbl_boxBATTERY2.setStyleSheet("color: " + message["lbl_boxBATTERY2"]["color"])
            ######### Modificación para etiqueta BATTERY-2 #########
            if "lbl_info1" in message:
                self.ui.lbl_info1.setText(message["lbl_info1"]["text"])
                if "color" in message["lbl_info1"]:
                    self.ui.lbl_info1.setStyleSheet("color: " + message["lbl_info1"]["color"])
            if "lbl_info2" in message:
                self.ui.lbl_info2.setText(message["lbl_info2"]["text"])
                if "color" in message["lbl_info2"]:
                    self.ui.lbl_info2.setStyleSheet("color: " + message["lbl_info2"]["color"])
            if "lbl_info3" in message:
                self.ui.lbl_info3.setText(message["lbl_info3"]["text"])
                if "color" in message["lbl_info3"]:
                    self.ui.lbl_info3.setStyleSheet("color: " + message["lbl_info3"]["color"])
            if "lbl_info4" in message:
                self.ui.lbl_info4.setText(message["lbl_info4"]["text"])
                if "color" in message["lbl_info4"]:
                    self.ui.lbl_info4.setStyleSheet("color: " + message["lbl_info4"]["color"])
            if "lbl_nuts" in message:
                self.ui.lbl_nuts.setText(message["lbl_nuts"]["text"])
                if "color" in message["lbl_nuts"]:
                    self.ui.lbl_nuts.setStyleSheet("color: " + message["lbl_nuts"]["color"])
            ###
            if "lbl_toolCurrent" in message:
                self.ui.lbl_toolCurrent.setText(message["lbl_toolCurrent"]["text"])
                if "color" in message["lbl_toolCurrent"]:
                    self.ui.lbl_toolCurrent.setStyleSheet("color: " + message["lbl_toolCurrent"]["color"])
            ###
            if "lbl_result" in message:
                self.ui.lbl_result.setText(message["lbl_result"]["text"])
                if "color" in message["lbl_result"]:
                    self.ui.lbl_result.setStyleSheet("color: " + message["lbl_result"]["color"])
            if "lbl_steps" in message:
                self.ui.lbl_steps.setText(message["lbl_steps"]["text"])
                if "color" in message["lbl_steps"]:
                    self.ui.lbl_steps.setStyleSheet("color: " + message["lbl_steps"]["color"])   
            if "lbl_user" in message:
                self.ui.lbl_user.setText(message["lbl_user"]["type"] + "\n" + message["lbl_user"]["user"])
                if "color" in message["lbl_user"]:
                    self.ui.lbl_user.setStyleSheet("color: " + message["lbl_user"]["color"])
                self.model.user = message["lbl_user"]
                self.qw_login.setVisible(False)
            if "img_user" in message:
                 if message["img_user"] != "":
                    if exists(self.model.imgsPath + message["img_user"]):
                        self.ui.img_user.setPixmap(QPixmap(self.model.imgsPath + message["img_user"]).scaled(110, 110, Qt.KeepAspectRatio))
                    else:
                        self.ui.img_user.setPixmap(QPixmap(":/images/images/usuario_x.jpg").scaled(110, 110, Qt.KeepAspectRatio))
            if "img_nuts" in message:
                if message["img_nuts"] != "":
                    if exists(self.model.imgsPath + message["img_nuts"]):
                        self.ui.img_nuts.setPixmap(QPixmap(self.model.imgsPath + message["img_nuts"]).scaled(110, 110, Qt.KeepAspectRatio))
            #####
            if "img_toolCurrent" in message:
                if message["img_toolCurrent"] != "":
                    if exists(self.model.imgsPath + message["img_toolCurrent"]):
                        self.ui.img_toolCurrent.setPixmap(QPixmap(self.model.imgsPath + message["img_toolCurrent"]).scaled(110, 110, Qt.KeepAspectRatio))
            #####
            if "img_center" in message: 
               if message["img_center"] != "":
                    if exists(self.model.imgsPath + message["img_center"]):
                        self.model.centerImage = self.model.imgsPath + message["img_center"]
                        self.ui.img_center.setPixmap(QPixmap(self.model.centerImage).scaled(self.ui.img_center.width(), self.ui.img_center.height(), Qt.KeepAspectRatio))
            if "show" in message:
                self.launcher(message["show"])         
            if "popOut" in message:
                self.launcher(message) 
            if "statusBar" in message:
                if type(message["statusBar"]) == str:
                    if message["statusBar"] == "clear":
                        self.ui.statusbar.clearMessage()
                    else:
                        self.ui.statusbar.showMessage(message["statusBar"])
        except Exception as ex:
            print("\ninput() exception : \nMessage: ", message, "\nException: ", ex)
            self.output.emit({"Exception":"Input error"})
    
    @pyqtSlot()
    def launcher(self, show):
        try:
            if "login" in show:
                self.qw_login.ui.lineEdit.setPlaceholderText("Escanea o escribe tu codigo")
                self.qw_login.setVisible(show["login"])
            if "scanner" in show:
                self.qw_scanner.ui.lineEdit.setPlaceholderText("Escanea el Código Qr")
                self.qw_scanner.setVisible(show["scanner"])
            if "popOut" in show:
                if show["popOut"] == "close" and self.pop_out.isVisible: 
                    self.pop_out.button(QMessageBox.Ok).click()
                else:
                    self.pop_out.setText(show["popOut"])
                    self.pop_out.setWindowTitle("Info")
                    self.pop_out.exec()
            if "img_popOut" in show:
                if show["img_popOut"] == "close":
                    self.qw_img_popout.ui.label.setPixmap(QPixmap(":/images/images/blanco.png"))
                    self.qw_img_popout.close()
                else:
                    self.qw_img_popout.ui.label.setPixmap(QPixmap(self.model.imgsPath + show["img_popOut"]))
                    self.qw_img_popout.show()
        except Exception as ex:
            print("launcher exception: ", ex)

    @pyqtSlot()
    def sendStatus (self):
        try:
            self.output.emit(self.model.status)
        except Exception as ex:
            print("sendStatus() exception: ", ex)

    @pyqtSlot()
    def resizeEvent(self, event):
        try:
            self.ui.img_center.setPixmap(QPixmap(self.model.centerImage).scaled(self.ui.img_center.width(), self.ui.img_center.height(), Qt.KeepAspectRatio))
            #print("[1]", self.width()-self.ui.frame.width())
            self.ui.frame.setMaximumWidth(self.width() - 328)
            #print("[2]", self.width()-self.ui.frame.width())
        except Exception as ex:
            print("resizeEvent() exception: ", ex)

    @pyqtSlot()
    def closeEvent(self, event):
        if self.shutdown == True:
            #self.shutdown = False
            self.timer.stop()
            self.output.emit({"gui": False})
            print ("Bye...")
            event.accept()
            self.deleteLater()
        elif self.allow_close == True:
            choice = QMessageBox.question(self, 'Salir', "Estas seguro de cerrar la aplicacion?",QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if choice == QMessageBox.Yes:
                self.timer.stop()
                self.output.emit({"gui": False})
                self.deleteLater()
                print ("Bye...")
                event.accept()
            else:
                event.ignore()
        else:
            event.ignore()
            self.pop_out.setText("No se permite cerrar esta ventana")
            self.pop_out.setWindowTitle("Warning")
            QTimer.singleShot(2000, self.pop_out.button(QMessageBox.Ok).click)
            self.pop_out.exec()


class Login (QDialog):
    def __init__(self, parent = None):
        super().__init__(parent)
        self.ui = login.Ui_login()
        self.ui.setupUi(self)
        self.ui.lineEdit.setEchoMode(QLineEdit.Password)
        self.ui.lineEdit.setStyleSheet('lineedit-password-character: 9679')
        self.ui.btn_ok.setFocusPolicy(Qt.NoFocus)
        self.ui.lineEdit.setFocus()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            print("Escape key was pressed")
     
            
class Scanner (QDialog):
    def __init__(self, parent = None):
        super().__init__(parent)
        self.ui = scanner.Ui_scanner()
        self.ui.setupUi(self) 
        self.ui.lineEdit.setEchoMode(QLineEdit.Password)
        self.ui.lineEdit.setStyleSheet('lineedit-password-character: 9679')
        self.ui.btn_ok.setFocusPolicy(Qt.NoFocus)
        self.ui.btn_cancel.setFocusPolicy(Qt.NoFocus)
        self.ui.lineEdit.setFocus()

    def closeEvent(self, event):
        event.ignore() 

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            print("Escape key was pressed")


class Img_popout (QDialog):
    def __init__(self, parent = None):
        super().__init__(parent)
        self.ui = img_popout.Ui_img_popout()
        self.ui.setupUi(self) 
        self.ui.label.setText("")
        

class PopOut (QMessageBox):
    def __init__(self, parent = None):
        super().__init__(parent)
        self.setIcon(QMessageBox.Information)
        self.setStandardButtons(QMessageBox.Ok)
        self.button(QMessageBox.Ok).setVisible(False)

    def closeEvent(self, event):
        event.ignore() 

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            print("Escape key was pressed")


if __name__ == "__main__":
    from PyQt5.QtWidgets import QApplication
    import sys
    app = QApplication(sys.argv)
    Window = Login()
    Window.show()
    sys.exit(app.exec_())
    

    
