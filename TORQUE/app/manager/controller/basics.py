from PyQt5.QtCore import QState, pyqtSignal, QTimer
from paho.mqtt import publish
from datetime import datetime
from threading import Timer
from os.path import exists
from time import strftime
from pickle import load
from copy import copy
from os import system
import requests
import json

from toolkit.admin import Admin

class Startup(QState):
    ok  = pyqtSignal()

    def __init__(self, model = None, parent = None):
        super().__init__(parent)
        self.model = model

    def onEntry(self, event):
        Timer(0.05, self.model.log, args = ("STARTUP",)).start() 
        if exists("data\config"):
            with open("data\config", "rb") as f:
                data = load(f)
                if "encoder_feedback" in data:
                    for i in data["encoder_feedback"]:
                        if type(data["encoder_feedback"][i]) == bool:
                            self.model.config_data["encoder_feedback"][i] = data["encoder_feedback"][i]
                if "retry_btn_mode" in data:
                    for i in data["retry_btn_mode"]:
                        if type(data["retry_btn_mode"][i]) == bool:
                            self.model.config_data[ "retry_btn_mode"][i] = data[ "retry_btn_mode"][i]
        self.model.config_data["untwist"] = False
        self.model.config_data["flexible_mode"] = False

        if self.model.local_data["user"]["type"] != "":
            Timer(0.05, self.logout, args = (copy(self.model.local_data["user"]),)).start()

        self.model.local_data["user"]["type"] = ""
        self.model.local_data["user"]["name"] = ""
        self.model.local_data["user"]["pass"] = ""
        command = {
            "lbl_info1" : {"text": "", "color": "black"},
            "lbl_info2" : {"text": "", "color": "green"},
            "lbl_info3" : {"text": "", "color": "black"},
            "lbl_info4" : {"text": "", "color": "black"},
            "lbl_nuts"  : {"text": "", "color": "black"},
            "lbl_toolCurrent"  : {"text": "", "color": "black"},
            "lbl_boxTITLE" : {"text": "", "color": "black"},
            "lbl_boxPDCR" : {"text": "", "color": "black"},
            "lbl_boxPDCP" : {"text": "", "color": "black"},
            "lbl_boxPDCD" : {"text": "", "color": "black"},
            "lbl_boxMFBP1" : {"text": "", "color": "black"},
            "lbl_boxMFBP2" : {"text": "", "color": "black"},
            "lbl_boxMFBE" : {"text": "", "color": "black"},
            "lbl_boxMFBS" : {"text": "", "color": "black"},
            "lbl_boxBATTERY" : {"text": "", "color": "black"},
            "lbl_boxBATTERY2" : {"text": "", "color": "black"},
            "lbl_result" : {"text": "Se requiere un login para continuar", "color": "green"},
            "lbl_steps" : {"text": "Ingresa tu código de acceso", "color": "black"},
            "lbl_user" : {"type":"", "user": "", "color": "black"},
            "img_user" : "blanco.jpg",
            "img_nuts" : "blanco.jpg",
            "img_toolCurrent" : "blanco.jpg",
            "img_center" : "logo.jpg"
            }
        publish.single(self.model.pub_topics["gui"],json.dumps(command),hostname='127.0.0.1', qos = 2)
        publish.single(self.model.pub_topics["gui_2"],json.dumps(command),hostname='127.0.0.1', qos = 2)
        command = {
            "lbl_boxTITLE" : {"text": " Teclas para\nSujetar/Liberar\nCajas\n", "color": "black"},
            "lbl_boxPDCR" : {"text": " F9 = PDC-R", "color": "blue"},
            "lbl_boxMFBP2" : {"text": " F8 = MFB-P2", "color": "blue"},
            "lbl_boxMFBS" : {"text": " F7 = MFB-S", "color": "blue"},
            "lbl_boxMFBP1" : {"text": " F6 = MFB-P1", "color": "blue"},
            "lbl_boxBATTERY" : {"text": " F5 = BATTERY", "color": "blue"},
            "lbl_boxBATTERY2" : {"text": " F4 = BATTERY-2", "color": "blue"},
            "lbl_boxMFBE" : {"text": " F3 = MFB-E", "color": "blue"},
            "lbl_boxPDCD" : {"text": " F2 = PDC-D", "color": "blue"},
            "lbl_boxPDCP" : {"text": " F1 = PDC-P", "color": "blue"},
            }
        publish.single(self.model.pub_topics["gui_2"],json.dumps(command),hostname='127.0.0.1', qos = 2)

        QTimer.singleShot(100, self.stopTorque)
        #QTimer.singleShot(15000, self.kioskMode)
        self.ok.emit()

    def stopTorque (self):
        publish.single(self.model.pub_topics["torque"]["tool1"],json.dumps({"profile" : 0}),hostname='127.0.0.1', qos = 2)
        publish.single(self.model.pub_topics["torque"]["tool2"],json.dumps({"profile" : 0}),hostname='127.0.0.1', qos = 2)
        publish.single(self.model.pub_topics["torque"]["tool3"],json.dumps({"profile" : 0}),hostname='127.0.0.1', qos = 2)

    def kioskMode(self):
        system("taskkill /f /im explorer.exe")
        publish.single("modules/set",json.dumps({"window" : False}),hostname='127.0.0.1', qos = 2)
        publish.single("visycam/set",json.dumps({"window" : False}),hostname='127.0.0.1', qos = 2)

    def logout(self, user):
        try:
            Timer(0.05, self.model.log, args = ("LOGOUT",)).start() 
            data = {
                "NAME": user["name"],
                "GAFET": user["pass"],
                "TYPE": user["type"],
                "LOG": "LOGOUT",
                "DATETIME": strftime("%Y/%m/%d %H:%M:%S"),
                }
            endpoint = "http://{}/api/post/login".format(self.model.server)
            resp = requests.post(endpoint, data=json.dumps(data))
        except Exception as ex:
            print("Logout Exception: ", ex)


class Login (QState):
    def __init__(self, model = None, parent = None):
        super().__init__(parent)
        self.model = model
    def onEntry(self, event):
        command = {
            "show":{"login": True},
            "allow_close": True
            }
        publish.single(self.model.pub_topics["gui"],json.dumps(command),hostname='127.0.0.1', qos = 2)


class CheckLogin (QState):
    ok      = pyqtSignal()
    nok     = pyqtSignal()

    def __init__(self, model = None, parent = None):
        super().__init__(parent)
        self.model = model

    def onEntry(self, event):
        command = {
            "lbl_result" : {"text": "ID recibido", "color": "green"},
            "lbl_steps" : {"text": "Validando usuario...", "color": "black"},
            "show":{"login": False}
            }
        publish.single(self.model.pub_topics["gui"],json.dumps(command),hostname='127.0.0.1', qos = 2)
        publish.single(self.model.pub_topics["gui_2"],json.dumps(command),hostname='127.0.0.1', qos = 2)
        Timer(0.05,self.API_requests).start()

    def API_requests (self):
        try:
            endpoint = ("http://{}/api/get/usuarios/GAFET/=/{}/ACTIVE/=/1".format(self.model.server, self.model.input_data["gui"]["ID"]))
            response = requests.get(endpoint).json()

            if "TYPE" in response:
                self.model.local_data["user"]["type"] = response["TYPE"]
                self.model.local_data["user"]["name"] = response["NAME"]
                self.model.local_data["user"]["pass"] = copy(self.model.input_data["gui"]["ID"])
                data = {
                    "NAME": self.model.local_data["user"]["name"],
                    "GAFET":  self.model.local_data["user"]["pass"],
                    "TYPE": self.model.local_data["user"]["type"],
                    "LOG": "LOGIN",
                    "DATETIME": strftime("%Y/%m/%d %H:%M:%S"),
                    }
                endpoint = "http://{}/api/post/login".format(self.model.server)
                resp = requests.post(endpoint, data=json.dumps(data))

                command = {
                    "lbl_user" : {"type":self.model.local_data["user"]["type"],
                                  "user": self.model.local_data["user"]["name"], 
                                  "color": "black"
                                  },
                    "img_user" : self.model.local_data["user"]["name"] + ".jpg"
                    }
                publish.single(self.model.pub_topics["gui"],json.dumps(command),hostname='127.0.0.1', qos = 2)
                publish.single(self.model.pub_topics["gui_2"],json.dumps(command),hostname='127.0.0.1', qos = 2)
                Timer(0.05, self.model.log, args = ("LOGIN",)).start() 
                self.ok.emit()
            else:
                 command = {
                    "lbl_result" : {"text": "Intentalo de nuevo", "color": "red"},
                    "lbl_steps" : {"text": "Ingresa tu código de acceso", "color": "black"}
                    }
                 publish.single(self.model.pub_topics["gui"],json.dumps(command),hostname='127.0.0.1', qos = 2)
                 publish.single(self.model.pub_topics["gui_2"],json.dumps(command),hostname='127.0.0.1', qos = 2)
                 self.nok.emit()
        except Exception as ex:
            print("Login request exception: ", ex)
            command = {
                "lbl_result" : {"text": "Intentalo de nuevo", "color": "red"},
                "lbl_steps" : {"text": "Ingresa tu código de acceso", "color": "black"}
                }
            publish.single(self.model.pub_topics["gui"],json.dumps(command),hostname='127.0.0.1', qos = 2)
            publish.single(self.model.pub_topics["gui_2"],json.dumps(command),hostname='127.0.0.1', qos = 2)
            self.nok.emit()


class StartCycle (QState):
    ok = pyqtSignal()
    def __init__(self, model = None, parent = None):
        super().__init__(parent)
        self.model = model
        self.clamps = True

    def onEntry(self, event):
        self.model.cajas_habilitadas = {"PDC-P": 0,"PDC-D": 0,"MFB-P1": 0,"MFB-P2": 0,"PDC-R": 0,"PDC-RMID": 0,"BATTERY": 0,"BATTERY-2": 0,"MFB-S": 0,"MFB-E": 0}
        self.model.raffi = {"PDC-P": 0,"PDC-D": 0,"MFB-P1": 0,"MFB-P2": 0,"PDC-R": 0,"PDC-RMID": 0,"BATTERY": 0,"BATTERY-2": 0,"MFB-S": 0,"MFB-E": 0}
        for i in self.model.raffi:
            raffi_clear = {f"raffi_{i}":False}
            publish.single(self.model.pub_topics["plc"],json.dumps(raffi_clear),hostname='127.0.0.1', qos = 2)
        self.model.mediumflag = False
        self.model.largeflag = False
        self.model.smallflag = False
        self.model.pdcr_serie = ""
        self.model.mfbp2_serie = ""
        self.model.herramienta_activa = "0"     # Se resetea la herramienta activa en cada inicio de ciclo... para que el sistema pueda activar la herramienta requerida y no interfiera con las demás.

        self.model.reset()
        Timer(0.05, self.model.log, args = ("IDLE",)).start() 
        command = {
            "lbl_info1" : {"text": "", "color": "black"},
            "lbl_info2" : {"text": "", "color": "green"},
            "lbl_info3" : {"text": "", "color": "black"},
            "lbl_nuts" : {"text": "", "color": "orange"},
            "lbl_toolCurrent" : {"text": "", "color": "orange"},
            "lbl_boxTITLE" : {"text": "", "color": "black"},
            "lbl_boxPDCR" : {"text": "", "color": "black"},
            "lbl_boxPDCP" : {"text": "", "color": "black"},
            "lbl_boxPDCD" : {"text": "", "color": "black"},
            "lbl_boxMFBP1" : {"text": "", "color": "black"},
            "lbl_boxMFBP2" : {"text": "", "color": "black"},
            "lbl_boxMFBE" : {"text": "", "color": "black"},
            "lbl_boxMFBS" : {"text": "", "color": "black"},
            "lbl_boxBATTERY" : {"text": "", "color": "black"},
            "lbl_boxBATTERY2" : {"text": "", "color": "black"},
            "lbl_result" : {"text": "Nuevo ciclo iniciado", "color": "green"},
            "lbl_steps" : {"text": "Escanea el numero HM", "color": "black"},
            "img_nuts" : "blanco.jpg",
            "img_toolCurrent" : "blanco.jpg",
            "img_center" : "logo.jpg",
            "allow_close": False,
            "cycle_started": False,
            "statusBar": "clear"
            }
        if self.model.shutdown == True:
            Timer(0.05, self.logout, args = (copy(self.model.local_data["user"]),)).start()
            command["lbl_result"] = {"text": "Apagando equipo...", "color": "green"}
            command["lbl_steps"] = {"text": ""}
            command["shutdown"] = True
            self.clamps = False
            QTimer.singleShot(3000, self.torqueClamp)
        if self.model.config_data["untwist"]:
            command["lbl_info3"] = {"text": "MODO:\n\nREVERSA", "color": "blue"}
        if self.model.config_data["flexible_mode"]:
            if len(command["lbl_info3"]["text"]) < 1:
                command["lbl_info3"] = {"text": "MODO:\n\nAPRIETE\nPUNTUAL", "color": "blue"}
            else:
                command["lbl_info3"]["text"] += "\nPUNTUAL"
                command["lbl_info3"]["color"] = "blue"
        publish.single(self.model.pub_topics["gui"],json.dumps(command),hostname='127.0.0.1', qos = 2)
        command.pop("shutdown", None)
        command.pop("show", None)
        publish.single(self.model.pub_topics["gui_2"],json.dumps(command),hostname='127.0.0.1', qos = 2)
        command = {
            "lbl_boxTITLE" : {"text": " Teclas para\nSujetar/Liberar\nCajas\n", "color": "black"},
            "lbl_boxPDCR" : {"text": " F9 = PDC-R", "color": "blue"},
            "lbl_boxMFBP2" : {"text": " F8 = MFB-P2", "color": "blue"},
            "lbl_boxMFBS" : {"text": " F7 = MFB-S", "color": "blue"},
            "lbl_boxMFBP1" : {"text": " F6 = MFB-P1", "color": "blue"},
            "lbl_boxBATTERY" : {"text": " F5 = BATTERY", "color": "blue"},
            "lbl_boxBATTERY2" : {"text": " F4 = BATTERY-2", "color": "blue"},
            "lbl_boxMFBE" : {"text": " F3 = MFB-E", "color": "blue"},
            "lbl_boxPDCD" : {"text": " F2 = PDC-D", "color": "blue"},
            "lbl_boxPDCP" : {"text": " F1 = PDC-P", "color": "blue"},
            }
        publish.single(self.model.pub_topics["gui_2"],json.dumps(command),hostname='127.0.0.1', qos = 2)
        QTimer.singleShot(100, self.stopTorque)

        if not(self.model.shutdown):
            self.ok.emit()

    def torqueClamp (self):
        command = {}
        for i in self.model.torque_cycles:
             command[i] = self.clamps
        publish.single(self.model.pub_topics["plc"],json.dumps(command),hostname='127.0.0.1', qos = 2)

    def stopTorque (self):
        for i in self.model.pub_topics["torque"]:
            profile = self.model.torque_data[i]["stop_profile"]
            publish.single(self.model.pub_topics["torque"][i],json.dumps({"profile" : profile}),hostname='127.0.0.1', qos = 2)

    def logout(self, user):
        try:
            Timer(0.05, self.model.log, args = ("LOGOUT",)).start() 
            data = {
                "NAME": user["name"],
                "GAFET": user["pass"],
                "TYPE": user["type"],
                "LOG": "LOGOUT",
                "DATETIME": strftime("%Y/%m/%d %H:%M:%S"),
                }
            endpoint = "http://{}/api/post/login".format(self.model.server)
            resp = requests.post(endpoint, data=json.dumps(data))
        except Exception as ex:
            print("Logout Exception: ", ex)


class Config (QState):
    def __init__(self, model = None, parent = None):
        super().__init__(parent)
        self.model = model
        self.admin = None

    def onEntry(self, event):
        Timer(0.05, self.model.log, args = ("CONFIG",)).start() 
        admin = Admin(data = self.model)

        command = {
            "lbl_result" : {"text": "Sistema en configuración", "color": "green"},
            "lbl_steps" : {"text": "Ciclo de operación deshabilitado", "color": "black"}
            }
        publish.single(self.model.pub_topics["gui"],json.dumps(command),hostname='127.0.0.1', qos = 2)
        publish.single(self.model.pub_topics["gui_2"],json.dumps(command),hostname='127.0.0.1', qos = 2)

    def onExit (self, event):
        if exists("data\config"):
            with open("data\config", "rb") as f:
                data = load(f)
                if "encoder_feedback" in data:
                    for i in data["encoder_feedback"]:
                        if type(data["encoder_feedback"][i]) == bool:
                            self.model.config_data["encoder_feedback"][i] = data["encoder_feedback"][i]
                if "retry_btn_mode" in data:
                    for i in data["retry_btn_mode"]:
                        if type(data["retry_btn_mode"][i]) == bool:
                            self.model.config_data[ "retry_btn_mode"][i] = data[ "retry_btn_mode"][i]
                if "untwist" in data:
                    if type(data["untwist"]) == bool:
                        self.model.config_data["untwist"] = data["untwist"]


class ScanQr (QState):
    def __init__(self, model = None, parent = None):
        super().__init__(parent)
        self.model = model

    def onEntry(self, event):
        command = {
            "show":{"scanner": True}
            }
        publish.single(self.model.pub_topics["gui"],json.dumps(command),hostname='127.0.0.1', qos = 2)
        command.pop("show")
        publish.single(self.model.pub_topics["gui_2"],json.dumps(command),hostname='127.0.0.1', qos = 2)

    def onExit(self, QEvent):
        command = {
            "show":{"scanner": False}
            }
        publish.single(self.model.pub_topics["gui"],json.dumps(command),hostname='127.0.0.1', qos = 2)


class CheckQr (QState):
    ok      = pyqtSignal()
    nok     = pyqtSignal()
    rework  = pyqtSignal()

    def __init__(self, model = None, parent = None):
        super().__init__(parent)
        self.model = model

    def onEntry(self, event):
        command = {
            "lbl_result" : {"text": "Datamatrix escaneado", "color": "green"},
            "lbl_steps" : {"text": "Validando", "color": "black"}
            }
        publish.single(self.model.pub_topics["gui"],json.dumps(command),hostname='127.0.0.1', qos = 2)
        publish.single(self.model.pub_topics["gui_2"],json.dumps(command),hostname='127.0.0.1', qos = 2)
        Timer(0.05, self.API_requests).start()

    def API_requests (self):
        try:
            pedido = None
            dbEvent = None
            coincidencias = 0
            self.model.qr_codes["FET"] = self.model.input_data["gui"]["code"]
            temp = self.model.input_data["gui"]["code"].split (" ")
            self.model.qr_codes["HM"] = "--"
            self.model.qr_codes["REF"] = "--"
            correct_lbl = False
            for i in temp:
                if "HM" in i:
                    self.model.qr_codes["HM"] = i
                ############# MODIFICACIÓN #############
                if "ILX" in i or "IRX" in i: #Se agregó la opción de escanear etiquetas con prefijo "IRX"
                ############# MODIFICACIÓN #############
                    self.model.qr_codes["REF"] = i
                if "EL." in i:
                    correct_lbl = True

            if not(correct_lbl):
                command = {
                        "lbl_result" : {"text": "Datamatrix incorrecto", "color": "red"},
                        "lbl_steps" : {"text": "Inténtalo de nuevo", "color": "black"}
                        }
                publish.single(self.model.pub_topics["gui"],json.dumps(command),hostname='127.0.0.1', qos = 2)
                self.nok.emit()
                return

            endpoint = "http://{}/api/get/eventos".format(self.model.server)
            eventos = requests.get(endpoint).json()
            #print("Lista eventos:\n",eventos)
            #print("Eventos: ",eventos["eventos"])
            #print("Eventos KEYS: ",eventos["eventos"].keys())
            for key in eventos["eventos"].keys():
                print("++++++++++++++Evento Actual++++++++++++++++:\n ",key)
                print("Valor Activo del Evento actual: ",eventos["eventos"][key][1])
                if eventos["eventos"][key][1] == 1:
                    endpoint = "http://{}/api/get/{}/pedidos/PEDIDO/=/{}/ACTIVE/=/1".format(self.model.server, key, self.model.qr_codes["REF"])
                    response = requests.get(endpoint).json()
                    #print("Response: ",response)
                    if "PEDIDO" in response:
                        dbEvent = key
                        coincidencias += 1
                        print("En este Evento se encuentra la modularidad \n")
                        pedido = response
            print("Coincidencias = ",coincidencias)
            if dbEvent != None:
                print("La Modularidad pertenece al Evento: ",dbEvent)
                if coincidencias != 1:
                    print("Datamatrix Redundante")
                    command = {
                        "lbl_result" : {"text": "Datamatrix redundante", "color": "red"},
                        "lbl_steps" : {"text": "Inténtalo de nuevo", "color": "black"}
                        }
                    publish.single(self.model.pub_topics["gui"],json.dumps(command),hostname='127.0.0.1', qos = 2)
                    publish.single(self.model.pub_topics["gui_2"],json.dumps(command),hostname='127.0.0.1', qos = 2)
                    self.nok.emit()
                    return
                else:
                    print("Datamatrix Correcto")
            else:
                print("La Modularidad NO pertenece a ningún evento")
                command = {
                    "lbl_result" : {"text": "Datamatrix no registrado", "color": "green"},
                    "lbl_steps" : {"text": "Inténtalo de nuevo", "color": "black"}
                    }
                publish.single(self.model.pub_topics["gui"],json.dumps(command),hostname='127.0.0.1', qos = 2)
                publish.single(self.model.pub_topics["gui_2"],json.dumps(command),hostname='127.0.0.1', qos = 2)
                self.nok.emit()
                return

            #endpoint = "http://{}/api/get/pedidos/PEDIDO/=/{}/ACTIVE/=/1".format(self.model.server, self.model.qr_codes["REF"])
            #response = requests.get(endpoint).json()
            #if "PEDIDO" in response:
            #    if type(response["PEDIDO"]) != list: 
            #        if response["ACTIVE"]:
            #            pedido = response
            #        else:
            #            command = {
            #                        "lbl_result" : {"text": "Datamatrix desactivado", "color": "red"},
            #                        "lbl_steps" : {"text": "Inténtalo de nuevo", "color": "black"}
            #                      }
            #            publish.single(self.model.pub_topics["gui"],json.dumps(command),hostname='127.0.0.1', qos = 2)
            #            command.pop("show")
            #            publish.single(self.model.pub_topics["gui_2"],json.dumps(command),hostname='127.0.0.1', qos = 2)
            #            self.nok.emit()
            #            return
            #    else: 
            #        command = {
            #                    "lbl_result" : {"text": "Datamatrix redundante", "color": "red"},
            #                    "lbl_steps" : {"text": "Inténtalo de nuevo", "color": "black"}
            #                  }
            #        publish.single(self.model.pub_topics["gui"],json.dumps(command),hostname='127.0.0.1', qos = 2)
            #        publish.single(self.model.pub_topics["gui_2"],json.dumps(command),hostname='127.0.0.1', qos = 2)
            #        self.nok.emit()
            #        return
            
            #else:
            #    command = {
            #            "lbl_result" : {"text": "Datamatrix no registrado", "color": "green"},
            #            "lbl_steps" : {"text": "Inténtalo de nuevo", "color": "black"}
            #            }
            #    publish.single(self.model.pub_topics["gui"],json.dumps(command),hostname='127.0.0.1', qos = 2)
            #    publish.single(self.model.pub_topics["gui_2"],json.dumps(command),hostname='127.0.0.1', qos = 2)
            #    self.nok.emit()
            #    return

            endpoint = "http://{}/api/get/{}/pdcr/variantes".format(self.model.server, dbEvent)
            pdcrVariantes = requests.get(endpoint).json()
            print("Lista Final de Variantes PDC-R:\n",pdcrVariantes)

            endpoint = "http://{}/api/get/historial/HM/=/{}/RESULTADO/=/1".format(self.model.server, self.model.qr_codes["HM"])
            response = requests.get(endpoint).json()

            if ("items" in response and not(response["items"])) or self.model.local_data["qr_rework"] or self.model.config_data["untwist"] or self.model.config_data["flexible_mode"]:
                if self.model.config_data["flexible_mode"]:
                    print("Response*******: ",response["SERIALES"])
                    if type(response["SERIALES"]) != list:
                        print("ES UN SOLO REGISTRO!")
                        qr_retrabajo = json.loads(response["SERIALES"])
                        [qr_retrabajo.pop(key, None) for key in ['FET','HM','REF']]
                        self.model.input_data["database"]["qr_retrabajo"] = qr_retrabajo
                        print("Qr_retrabajo modelo: ",self.model.input_data["database"]["qr_retrabajo"])
                    else:
                        print("ES UNA LISTA DE REGISTROS!")
                        qr_retrabajo = json.loads(response["SERIALES"][-1])
                        [qr_retrabajo.pop(key, None) for key in ['FET','HM','REF']]
                        self.model.input_data["database"]["qr_retrabajo"] = qr_retrabajo
                        print("Qr_retrabajo modelo: ",self.model.input_data["database"]["qr_retrabajo"])
                modules = json.loads(pedido["MODULOS_TORQUE"])
                modules = modules[list(modules)[0]]
                print("\n\t+++++++++++MODULARIDAD REFERENCIA+++++++++++\n",self.model.qr_codes["REF"])
                print(f"\n\t\tMODULOS_TORQUE:\n{modules}")
                #### MODIFICACIÓN PDCR ####
                flag_s = False
                flag_m = False
                flag_l = False
                flag_variantes = True
                flag_mfbp2_der = False
                flag_mfbp2_izq = False
                mfbp2_serie = ""
                mfbeBox = ""
                battery2Box = ""
                flag_294 = False
                flag_296 = False
                if "294" in self.model.qr_codes["REF"]:
                    print("Evento 294")
                    flag_294 = True
                if "296" in self.model.qr_codes["REF"]:
                    print("Evento 296")
                    flag_296 = True
                    #print("Aqui",pdcrVariantes)
                for s in pdcrVariantes["small"]:
                    if s in modules:
                        #print("Tiene un modulo de caja SMALL")
                        flag_s = True
                for m in pdcrVariantes["medium"]:
                    if m in modules:
                        #print("Tiene un modulo de caja Medium")
                        flag_m = True
                for l in pdcrVariantes["large"]:
                    if l in modules:
                        #print("Tiene un modulo de caja LARGE")
                        flag_l = True
                if "ILX" in self.model.qr_codes["REF"]:
                    print("Modularidad de MFB-P2 Izquierda")
                    flag_mfbp2_izq = True
                if "IRX" in self.model.qr_codes["REF"]:
                    print("Modularidad de MFB-P2 Derecha")
                    flag_mfbp2_der = True

                print("\t\tFLAGS:\n Flag S - ",flag_s," Flag M - ",flag_m," Flag L - ",flag_l,"\n Flag MFB-P2 DER - ",flag_mfbp2_der," Flag MFB-P2 IZQ - ",flag_mfbp2_izq)
                if flag_s == False and flag_m == False and flag_l == False:
                    flag_variantes = False

                #para mensajes que se publican
                if flag_l == True:
                    varianteDominante = "PDC-R"
                    self.model.largeflag = True
                    self.model.pdcr_serie = "12239061602"
                if flag_m == True and flag_l == False:
                    varianteDominante = "PDC-RMID"
                    self.model.mediumflag = True
                    self.model.pdcr_serie = "12239061502"
                if flag_s == True and flag_m == False and flag_l == False:
                    varianteDominante = "PDC-RS"
                    self.model.smallflag = True
                    self.model.pdcr_serie = "12239061402"

                if flag_mfbp2_der == True and flag_mfbp2_izq == False:
                    self.model.mfbp2_serie = "12975407216"
                if flag_mfbp2_der == False and flag_mfbp2_izq == True:
                    self.model.mfbp2_serie = "12975407316"
                if flag_mfbp2_der == False and flag_mfbp2_izq == False:
                    self.model.mfbp2_serie = "Sin especificar"


                #### MODIFICACIÓN PDCR ####
                for i in modules:
                    endpoint = "http://{}/api/get/{}/modulos_torques/MODULO/=/{}/_/=/_".format(self.model.server, dbEvent, i)
                    response = requests.get(endpoint).json()
                    if "MODULO" in response:
                        if type(response["MODULO"]) != list:
                            temp = {}
                            for i in response:
                                if "CAJA_" in i:
                                    temp.update(json.loads(response[i]))
                            for i in temp:
                                newBox = False
                                #print("Caja: ******: ",i)
                                if len(temp[i]) == 0:
                                    continue
                                if not(i in self.model.input_data["database"]["modularity"]):
                                    newBox = True
                                for j in temp[i]:
                                    if temp[i][j] == True:
                                        if newBox:
                                            if flag_296 == True or flag_294 == True:
                                                if flag_variantes == True:
                                                    #si hay una caja PDC-R se modifica por la variable PDC-R dominante
                                                    if i == "PDC-R" or i == "PDC-RMID" or i == "PDC-RS":
                                                        i = varianteDominante
                                                else:
                                                    #print("LA MODULARIDAD NO CONTIENE MÓDULOS QUE ESPECIFIQUEN SU VARIANTE EN LA PDC-R")
                                                    command = {
                                                        "lbl_result" : {"text": "La Modularidad no contiene módulos que especifiquen su variante en la PDC-R", "color": "red"},
                                                        "lbl_steps" : {"text": "Inténtalo de nuevo", "color": "black"}
                                                        }
                                                    publish.single(self.model.pub_topics["gui"],json.dumps(command),hostname='127.0.0.1', qos = 2)
                                                    publish.single(self.model.pub_topics["gui_2"],json.dumps(command),hostname='127.0.0.1', qos = 2)
                                                    self.model.input_data["database"]["modularity"].clear()
                                                    self.model.torque_data["tool1"]["queue"].clear()
                                                    self.model.torque_data["tool2"]["queue"].clear()
                                                    self.model.torque_data["tool3"]["queue"].clear()
                                                    self.nok.emit()
                                            self.model.input_data["database"]["modularity"][i] = []
                                            #print(" AQUI ESTÁ EL NUEVO I!!!!!!!!!: ",i)#### MODIFICACIÓN PDCR ####
                                            newBox = False
                                        if not(j in self.model.input_data["database"]["modularity"][i]):
                                            self.model.input_data["database"]["modularity"][i].append(j)
                                            #print(" AQUI ESTÁ EL J valor!!!!!!!!!: ",j)#### MODIFICACIÓN PDCR ####
                                if not(newBox):
                                    self.model.input_data["database"]["modularity"][i].sort()
                        else:
                            command = {
                                    "lbl_result" : {"text": "Módulos de torque redundantes", "color": "red"},
                                    "lbl_steps" : {"text": "Inténtalo de nuevo", "color": "black"}
                                  }
                            publish.single(self.model.pub_topics["gui"],json.dumps(command),hostname='127.0.0.1', qos = 2)
                            publish.single(self.model.pub_topics["gui_2"],json.dumps(command),hostname='127.0.0.1', qos = 2)
                            self.nok.emit()
                            return
                    else:
                        command = {
                                "lbl_result" : {"text": "Modulos de torque no encontrados", "color": "red"},
                                "lbl_steps" : {"text": "Inténtalo de nuevo", "color": "black"}
                                }
                        publish.single(self.model.pub_topics["gui"],json.dumps(command),hostname='127.0.0.1', qos = 2)
                        publish.single(self.model.pub_topics["gui_2"],json.dumps(command),hostname='127.0.0.1', qos = 2)
                        self.nok.emit()
                        return

                ###############################
                for i in self.model.input_data["database"]["modularity"]:
                    print("cajas dentro de modularity: ",i)
                    current_boxx = i
                    current_boxx = current_boxx.replace("-","")

                    if "PDC-R" in i:
                        if self.model.smallflag == True:    
                            self.model.cajas_habilitadas["PDC-RMID"] = 2
                        if self.model.mediumflag == True:
                            self.model.cajas_habilitadas["PDC-RMID"] = 2
                        if self.model.largeflag == True:
                            self.model.cajas_habilitadas["PDC-R"] = 2
                        current_boxx = "PDCR"
                    else:
                        self.model.cajas_habilitadas[i] = 2

                    serie = ""
                    if i == "MFB-P2":
                        serie = self.model.mfbp2_serie
                    if "PDC-R" in i:
                        serie = self.model.pdcr_serie

                    pub_i = i
                    if i == "PDC-P" or i == "BATTERY" or i == "BATTERY-2" or i == "MFB-E":
                        command = {f"lbl_box{current_boxx}" : {"text": f"{pub_i}:\n Habilitada", "color": "blue"}}
                    else:
                        #si no se activan estas banderas es porque es R LARGE
                        if "PDC-R" in i:
                            if self.model.smallflag == True:
                                pub_i = "PDC-RSMALL"
                            if self.model.mediumflag == True:
                                pub_i = "PDC-RMID"
                            if self.model.largeflag == True:
                                pub_i = "PDC-R"
                        command = {f"lbl_box{current_boxx}" : {"text": f"{pub_i} {serie}:\n Esperando QR", "color": "purple"}}
                    publish.single(self.model.pub_topics["gui"],json.dumps(command),hostname='127.0.0.1', qos = 2)
                print("cajas habilitadas CICLO: ",self.model.cajas_habilitadas)

                    #publish.single(self.model.pub_topics["gui_2"],json.dumps(command),hostname='127.0.0.1', qos = 2)

                ###############################
                
                print("\t\tCOLECCIÓN:\n", self.model.input_data["database"]["modularity"])
                self.model.input_data["database"]["pedido"] = pedido
                self.model.datetime = datetime.now()

                if self.model.local_data["qr_rework"]:
                    self.model.local_data["qr_rework"] = False

                if flag_296 == True or flag_294 == True:
                    print("dbEvent: ",dbEvent)
                    event = dbEvent.upper()
                    evento = event.replace('_',' ')
                    #Se agrega el nombre del evento a una variable en el modelo, el cual servirá para definir el oracle de las tuercas en caso de pertenecer a PRO1
                    self.model.evento = evento
                    command = {
                        "lbl_result" : {"text": "Datamatrix OK", "color": "green"},
                        "lbl_steps" : {"text": "Comenzando etapa de torque", "color": "black"},
                        "statusBar" : pedido["PEDIDO"] +" "+self.model.qr_codes["HM"]+" "+evento,
                        "cycle_started": True
                    }
                else:
                    command = {
                        "lbl_result" : {"text": "Datamatrix OK", "color": "green"},
                        "lbl_steps" : {"text": "Comenzando etapa de torque", "color": "black"},
                        "statusBar" : pedido["PEDIDO"],
                        "cycle_started": True
                    }
                publish.single(self.model.pub_topics["gui"],json.dumps(command),hostname='127.0.0.1', qos = 2)
                publish.single(self.model.pub_topics["gui_2"],json.dumps(command),hostname='127.0.0.1', qos = 2)
                command = {
                    "lbl_boxTITLE" : {"text": "||Cajas a utilizar||", "color": "black"},
                    "lbl_result" : {"text": "Datamatrix OK", "color": "green"},
                    "lbl_steps" : {"text": "Comenzando etapa de torque", "color": "black"},
                    "statusBar" : pedido["PEDIDO"] +" "+self.model.qr_codes["HM"]+" "+evento,
                    "cycle_started": True
                }
                publish.single(self.model.pub_topics["gui"],json.dumps(command),hostname='127.0.0.1', qos = 2)
                Timer(0.1, self.torqueClamp).start()
                Timer(0.05, self.model.log, args = ("RUNNING",)).start() 
                self.ok.emit()
            else:
                self.rework.emit()
                return

        except Exception as ex:
            print("Datamatrix request exception: ", ex) 
            if flag_variantes == False:
                print("La Modularidad no contiene módulos que especifiquen su variante en la PDC-R")
                temp = "La Modularidad no contiene módulos que especifiquen su variante en la PDC-R"
            else:
                temp = f"Database Exception: {ex.args}"
            command = {
                "lbl_result" : {"text": temp, "color": "red"},
                "lbl_steps" : {"text": "Inténtalo de nuevo", "color": "black"}
                }
            publish.single(self.model.pub_topics["gui"],json.dumps(command),hostname='127.0.0.1', qos = 2)
            publish.single(self.model.pub_topics["gui_2"],json.dumps(command),hostname='127.0.0.1', qos = 2)
            self.model.input_data["database"]["modularity"].clear()
            self.model.torque_data["tool1"]["queue"].clear()
            self.model.torque_data["tool2"]["queue"].clear()
            self.model.torque_data["tool3"]["queue"].clear()
            self.nok.emit()

    def torqueClamp (self):
        command = {}
        master_qr_boxes = json.loads(self.model.input_data["database"]["pedido"]["QR_BOXES"])
        print(f"\t\tQR_BOXES:\n{master_qr_boxes}\n")
        for i in self.model.torque_cycles:
            command[i] = False
            if i in self.model.input_data["database"]["modularity"]:
                if i in master_qr_boxes:
                    if not(master_qr_boxes[i][1]):
                        command[i] = True
                else:
                    command[i] = True
        publish.single(self.model.pub_topics["plc"],json.dumps(command),hostname='127.0.0.1', qos = 2)


class QrRework (QState):
    ok = pyqtSignal()
    def __init__(self, model = None, parent = None):
        super().__init__(parent)
        self.model = model

        self.model.transitions.key.connect(self.rework)
        self.model.transitions.code.connect(self.noRework)

    def onEntry(self, QEvent):
        command = {
            "lbl_result" : {"text": "Datamatrix procesado anteriormente", "color": "green"},
            "lbl_steps" : {"text": "Escanea otro código o gira la llave para continuar", "color": "black"},
            "show":{"scanner": True}
            }
        publish.single(self.model.pub_topics["gui"],json.dumps(command),hostname='127.0.0.1', qos = 2)
        command.pop("show")
        publish.single(self.model.pub_topics["gui_2"],json.dumps(command),hostname='127.0.0.1', qos = 2)

    def onExit(self, QEvent):
        command = {
            "show":{"scanner": False}
            }
        publish.single(self.model.pub_topics["gui"],json.dumps(command),hostname='127.0.0.1', qos = 2)

    def rework (self):
        self.model.local_data["qr_rework"] = True
        Timer(0.05, self.ok.emit).start()

    def noRework(self):
        Timer(0.05, self.ok.emit).start()


class Finish (QState):
    ok      = pyqtSignal()
    nok     = pyqtSignal()

    def __init__(self, model = None, parent = None):
        super().__init__(parent)
        self.model = model

    def onEntry(self, event):

        self.model.cajas_habilitadas = {"PDC-P": 0,"PDC-D": 0,"MFB-P1": 0,"MFB-P2": 0,"PDC-R": 0,"PDC-RMID": 0,"BATTERY": 0,"BATTERY-2": 0,"MFB-S": 0,"MFB-E": 0}
        self.model.raffi = {"PDC-P": 0,"PDC-D": 0,"MFB-P1": 0,"MFB-P2": 0,"PDC-R": 0,"PDC-RMID": 0,"BATTERY": 0,"BATTERY-2": 0,"MFB-S": 0,"MFB-E": 0}
        for i in self.model.raffi:
            raffi_clear = {f"raffi_{i}":False}
            publish.single(self.model.pub_topics["plc"],json.dumps(raffi_clear),hostname='127.0.0.1', qos = 2)
        self.model.mediumflag = False
        self.model.largeflag = False
        self.model.smallflag = False
        self.model.pdcr_serie = ""
        self.model.mfbp2_serie = ""

        lblbox_clean = {
            "lbl_boxTITLE" : {"text": "", "color": "black"},
            "lbl_boxPDCR" : {"text": "", "color": "black"},
            "lbl_boxPDCP" : {"text": "", "color": "black"},
            "lbl_boxPDCD" : {"text": "", "color": "black"},
            "lbl_boxMFBP1" : {"text": "", "color": "black"},
            "lbl_boxMFBP2" : {"text": "", "color": "black"},
            "lbl_boxMFBE" : {"text": "", "color": "black"},
            "lbl_boxMFBS" : {"text": "", "color": "black"},
            "lbl_boxBATTERY" : {"text": "", "color": "black"},
            "lbl_boxBATTERY2" : {"text": "", "color": "black"},
            }
        publish.single(self.model.pub_topics["gui"],json.dumps(lblbox_clean),hostname='127.0.0.1', qos = 2)
        command = {
            "lbl_boxTITLE" : {"text": " Teclas para\nSujetar/Liberar\nCajas\n", "color": "black"},
            "lbl_boxPDCR" : {"text": " F9 = PDC-R", "color": "blue"},
            "lbl_boxMFBP2" : {"text": " F8 = MFB-P2", "color": "blue"},
            "lbl_boxMFBS" : {"text": " F7 = MFB-S", "color": "blue"},
            "lbl_boxMFBP1" : {"text": " F6 = MFB-P1", "color": "blue"},
            "lbl_boxBATTERY" : {"text": " F5 = BATTERY", "color": "blue"},
            "lbl_boxBATTERY2" : {"text": " F4 = BATTERY-2", "color": "blue"},
            "lbl_boxMFBE" : {"text": " F3 = MFB-E", "color": "blue"},
            "lbl_boxPDCD" : {"text": " F2 = PDC-D", "color": "blue"},
            "lbl_boxPDCP" : {"text": " F1 = PDC-P", "color": "blue"},
            }
        publish.single(self.model.pub_topics["gui_2"],json.dumps(command),hostname='127.0.0.1', qos = 2)

        flag_1 = False
        historial = {
            "HM": self.model.qr_codes["HM"],
            "RESULTADO": "1",
            "VISION": {},
            "ALTURA":{},
            "INTENTOS_VA": {},
            "TORQUE": self.model.result,
            "ANGULO": self.model.resultAngle,
            "INTENTOS_T": self.model.tries,
            "SERIALES": self.model.qr_codes,
            "INICIO": self.model.datetime.isoformat(),
            "FIN": strftime("%Y/%m/%d %H:%M:%S"),
            "USUARIO": self.model.local_data["user"]["type"] + ": " + self.model.local_data["user"]["name"],
            "NOTAS": {"TORQUE": ["OK"]},
            "SCRAP": self.model.local_data["nuts_scrap"]
            }
        if self.model.config_data["untwist"]:
            historial["RESULTADO"] = "0"
            historial["NOTAS"]["TORQUE"].insert(0,"DESAPRIETE")
            self.model.config_data["untwist"] = False
        else:
            historial["NOTAS"]["TORQUE"].insert(0,"APRIETE")
            flag_1 = True
        if self.model.config_data["flexible_mode"]:
            historial["NOTAS"]["TORQUE"].insert(-1, "FLEXIBLE")
            self.model.config_data["flexible_mode"] = False
            #flag_1 = False
        endpoint = "http://{}/api/post/historial".format(self.model.server)
        resp = requests.post(endpoint, data=json.dumps(historial))
        resp = resp.json()

        endpoint = ("http://{}/api/get/trazabilidad/HM/=/{}/_/_/_".format(self.model.server, self.model.qr_codes["HM"]))
        response = requests.get(endpoint).json()
        print("RESPONSE DE TRAZABILIDAD : ",response)
        if "items" in response:
            print("No hay registros en Trazabilidad")
        else:
            print("Si hay registros en Trazabilidad")
            print("ID DEL REGISTRO A ELIMINAR: ",response["ID"])
            print("Es un array de varios ID a eliminar?: ", isinstance(response["ID"], list))
            if isinstance(response["ID"], list):
                #print("Código para eliminar varios registros")
                for i in response["ID"]:
                    print("ID a eliminar: ",i)
                    endpoint = "http://{}/api/delete/trazabilidad/{}".format(self.model.server, i)
                    resp = requests.post(endpoint)
                    resp = resp.json()
                    print("RESP del DELETE: ", resp)
            else:
                #print("Código para eliminar solo un registro (El que ya tenía escrito)")
                print("ID a eliminar: ",response["ID"])
                endpoint = "http://{}/api/delete/trazabilidad/{}".format(self.model.server, response["ID"])
                resp = requests.post(endpoint)
                resp = resp.json()
                print("RESP del DELETE: ", resp)

        trazabilidad = {
            "HM": self.model.qr_codes["HM"],
            "ENTTORQUE": historial["INICIO"],
            "SALTORQUE": historial["FIN"],
            "NAMETORQUE": self.model.serial
            }
        endpoint = "http://{}/api/post/trazabilidad".format(self.model.server)
        resp = requests.post(endpoint, data=json.dumps(trazabilidad))
        resp = resp.json()

        ###### Guardar Datos en Servidor Remoto ######
        #if flag_1:
        #    try:
        #        endpoint = ("http://{}/seghm/get/seghm/HM/=/{}/_/_/_".format(self.model.server, self.model.qr_codes["HM"]))
        #        response = requests.get(endpoint).json()
        #        print("RESPONSE : ",response)
        #    except Exception as ex:
        #        print("Excepción al momento de guardar datos en el Servidor Remoto", ex)
        #    #try:
        #    flag_2 = False
        #    if not("items" in response):
        #        #print("Si se encontraron Concidencias!!")
        #        if type(response["id"]) == list:
        #            print("Información Redundante en la Base de Datos, se verá afectado el primer ID encontrado")
        #            flag_2 = True
        #            ID_1 = response["id"][0]
        #        else:
        #            ID_1 = response["id"]
        #        update = {
        #            "ENTTORQUE": historial["INICIO"],
        #            "SALTORQUE": historial["FIN"],
        #            "NAMETORQUE": self.model.serial
        #            }
        #        endpoint = "http://{}/seghm/update/seghm/{}".format(self.model.server, ID_1)
        #        print("Endpoint : ",endpoint)
        #        resp = requests.post(endpoint, data=json.dumps(update))
        #        resp = resp.json()
        #    else:
        #        print("El HM no existe en el servidor remoto")
        #    #except Exception as ex:
        #      #  print("Excepción al momento de guardar datos en el Servidor Remoto", ex)
        #else:
        #    print("Flag OFF")
        ###############################################

        if "items" in resp:
            if resp["items"] == 1:
                label = {
                    "DATE":  "FECHA"+ self.model.datetime.strftime("%Y/%m/%d %H:%M:%S"),
                    "REF":   "REF" + self.model.qr_codes["REF"],
                    "QR":    self.model.input_data["database"]["pedido"]["PEDIDO"],
                    "TITLE": "Estación de torques en arnes Interior" ,
                    "HM":    "HM" + self.model.qr_codes["HM"]
                }
                for i in self.model.result:
                    temp = []
                    for j in self.model.result[i]:
                        temp.append(str(self.model.result[i][j]))
                    label[i] = i + ": " + str(temp)

                #publish.single(self.model.pub_topics["printer"], json.dumps(label), hostname='127.0.0.1', qos = 2)
                QTimer.singleShot(100, self.finalMessage)
                QTimer.singleShot(1500,self.ok.emit)
                
            else:
                command = {
                    "lbl_result" : {"text": "Error al guardar los datos", "color": "red"},
                    "lbl_steps" : {"text": "Gire la llave de reset", "color": "black"}
                    }
                publish.single(self.model.pub_topics["gui"],json.dumps(command),hostname='127.0.0.1', qos = 2)
                publish.single(self.model.pub_topics["gui_2"],json.dumps(command),hostname='127.0.0.1', qos = 2)
        else:
            command = {
                "lbl_result" : {"text": "Error de conexión con la base de datos", "color": "red"},
                "lbl_steps" : {"text": "Gire la llave de reset", "color": "black"}
                }
            publish.single(self.model.pub_topics["gui"],json.dumps(command),hostname='127.0.0.1', qos = 2)
            publish.single(self.model.pub_topics["gui_2"],json.dumps(command),hostname='127.0.0.1', qos = 2)

    def finalMessage(self):
        command = {
            "lbl_result" : {"text": "Ciclo terminado", "color": "green"},
            "lbl_steps" : {"text": "Retira las cajas", "color": "black"}
            }
        publish.single(self.model.pub_topics["gui"],json.dumps(command),hostname='127.0.0.1', qos = 2)
        publish.single(self.model.pub_topics["gui_2"],json.dumps(command),hostname='127.0.0.1', qos = 2)


class Reset (QState):
    ok      = pyqtSignal()
    nok     = pyqtSignal()
    def __init__(self, model = None, parent = None):
        super().__init__(parent)
        self.model = model

    def onEntry(self, event):
        self.model.cajas_habilitadas = {"PDC-P": 0,"PDC-D": 0,"MFB-P1": 0,"MFB-P2": 0,"PDC-R": 0,"PDC-RMID": 0,"BATTERY": 0,"BATTERY-2": 0,"MFB-S": 0,"MFB-E": 0}
        self.model.raffi = {"PDC-P": 0,"PDC-D": 0,"MFB-P1": 0,"MFB-P2": 0,"PDC-R": 0,"PDC-RMID": 0,"BATTERY": 0,"BATTERY-2": 0,"MFB-S": 0,"MFB-E": 0}
        for i in self.model.raffi:
            raffi_clear = {f"raffi_{i}":False}
            publish.single(self.model.pub_topics["plc"],json.dumps(raffi_clear),hostname='127.0.0.1', qos = 2)
        self.model.mediumflag = False
        self.model.largeflag = False
        self.model.smallflag = False
        self.model.pdcr_serie = ""
        self.model.mfbp2_serie = ""

        command = {
            "lbl_result" : {"text": "Se giró la llave de reset", "color": "green"},
            "lbl_steps" : {"text": "Reiniciando", "color": "black"},
            "lbl_boxPDCR" : {"text": "", "color": "black"},
            "lbl_boxPDCP" : {"text": "", "color": "black"},
            "lbl_boxPDCD" : {"text": "", "color": "black"},
            "lbl_boxMFBP1" : {"text": "", "color": "black"},
            "lbl_boxMFBP2" : {"text": "", "color": "black"},
            "lbl_boxMFBE" : {"text": "", "color": "black"},
            "lbl_boxMFBS" : {"text": "", "color": "black"},
            "lbl_boxBATTERY" : {"text": "", "color": "black"},
            "lbl_boxBATTERY2" : {"text": "", "color": "black"},
            }
        publish.single(self.model.pub_topics["gui"],json.dumps(command),hostname='127.0.0.1', qos = 2)
        publish.single(self.model.pub_topics["gui_2"],json.dumps(command),hostname='127.0.0.1', qos = 2)
        command = {
            "lbl_boxPDCR" : {"text": " F9 = PDC-R", "color": "blue"},
            "lbl_boxMFBP2" : {"text": " F8 = MFB-P2", "color": "blue"},
            "lbl_boxMFBS" : {"text": " F7 = MFB-S", "color": "blue"},
            "lbl_boxMFBP1" : {"text": " F6 = MFB-P1", "color": "blue"},
            "lbl_boxBATTERY" : {"text": " F5 = BATTERY", "color": "blue"},
            "lbl_boxBATTERY2" : {"text": " F4 = BATTERY-2", "color": "blue"},
            "lbl_boxMFBE" : {"text": " F3 = MFB-E", "color": "blue"},
            "lbl_boxPDCD" : {"text": " F2 = PDC-D", "color": "blue"},
            "lbl_boxPDCP" : {"text": " F1 = PDC-P", "color": "blue"},
            }
        publish.single(self.model.pub_topics["gui_2"],json.dumps(command),hostname='127.0.0.1', qos = 2)

        command = {}
        for i in self.model.torque_cycles:
             command[i] = False
        publish.single(self.model.pub_topics["plc"],json.dumps(command),hostname='127.0.0.1', qos = 2)
        if self.model.datetime != None:
            historial = {
                "HM": self.model.qr_codes["HM"],
                "RESULTADO": "0",
                "VISION": {},
                "ALTURA":{},
                "INTENTOS_VA": {},
                "TORQUE": self.model.result,
                "ANGULO": self.model.resultAngle,
                "INTENTOS_T": self.model.tries,
                "SERIALES": self.model.qr_codes,
                "INICIO": self.model.datetime.isoformat(),
                "FIN": strftime("%Y/%m/%d %H:%M:%S"),
                "USUARIO": self.model.local_data["user"]["type"] + ": " + self.model.local_data["user"]["name"],
                "NOTAS": {"TORQUE": ["RESET"]},
                "SCRAP": self.model.local_data["nuts_scrap"]
                }
            if self.model.config_data["untwist"]:
                historial["NOTAS"]["TORQUE"].insert(0, "DESAPRIETE")
                self.model.config_data["untwist"] = False
            else:
                historial["NOTAS"]["TORQUE"].insert(0, "APRIETE")
            if self.model.config_data["flexible_mode"]:
                historial["NOTAS"]["TORQUE"].insert(-1, "FLEXIBLE")
                self.model.config_data["flexible_mode"] = False
            endpoint = "http://{}/api/post/historial".format(self.model.server)
            resp = requests.post(endpoint, data=json.dumps(historial))
            resp = resp.json()

            ####### Guardar Datos en Servidor Remoto ######
            #endpoint = ("http://{}/seghm/get/test/HM/=/{}/_/_/_".format(self.model.server, self.model.qr_codes["HM"]))
            #response = requests.get(endpoint).json()

            #try:
            #    if len(response)>1:
            #        response = response[1]
            #    if not("items" in response):
            #        ID_1 = response["id"]
            #        update = {
            #            "ENTTORQUE": historial["INICIO"],
            #            "SALTORQUE": historial["FIN"],
            #            "NAMETORQUE": self.model.serial
            #            }
            #        endpoint = "http://{}/seghm/update/test/{}".format(self.model.server, ID_1)
            #        resp = requests.post(endpoint, data=json.dumps(update))
            #        resp = resp.json()
            #except Exception as ex:
            #    print("Excepción al momento de guardar datos en el Servidor Remoto", ex)
            ################################################
            
            if "items" in resp:
                if resp["items"] == 1:
                    pass
                else:
                    command = {
                        "lbl_result" : {"text": "Error de conexión", "color": "red"},
                        "lbl_steps" : {"text": "Datos no guardados", "color": "black"}
                        }
                    publish.single(self.model.pub_topics["gui"],json.dumps(command),hostname='127.0.0.1', qos = 2)
                    publish.single(self.model.pub_topics["gui_2"],json.dumps(command),hostname='127.0.0.1', qos = 2)
        QTimer.singleShot(500,self.ok.emit)
