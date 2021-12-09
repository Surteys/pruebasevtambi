
from PyQt5.QtCore import QObject, pyqtSignal, QTimer
from paho.mqtt.client import Client
from threading import Timer
from copy import copy
import json

class MqttClient (QObject):
    
    conn_ok     =   pyqtSignal()
    conn_nok    =   pyqtSignal()
    clamp       =   pyqtSignal()
    emergency   =   pyqtSignal()
    key         =   pyqtSignal()
    zone        =   pyqtSignal()
    retry_btn   =   pyqtSignal()
    torque      =   pyqtSignal()
    login       =   pyqtSignal()
    logout      =   pyqtSignal()
    config      =   pyqtSignal()
    config_ok   =   pyqtSignal()
    ID          =   pyqtSignal()
    code        =   pyqtSignal()
    visible     =   pyqtSignal()
    qr_box      =   pyqtSignal(str)

    keyboard_key = ""
    keyboard_value = False
    llave = False

    
    nido = ["PDC-P","PDC-D","MFB-P1","MFB-P2","PDC-R","PDC-RMID","BATTERY","BATTERY-2","MFB-S","MFB-E"]
    nido_pub = ""
    color_nido = "blue"


    def __init__(self, model = None, parent = None):
        super().__init__(parent)
        self.model = model
        self.client = Client()
        QTimer.singleShot(5000, self.setup)

    def setup(self):
        try:
            self.client.on_connect = self.on_connect
            self.client.on_message = self.on_message
            self.client.connect(host = "127.0.0.1", port = 1883, keepalive = 60)
            self.client.loop_start()
        except Exception as ex:
            print("Manager MQTT client connection fail. Exception: ", ex)

    def stop (self):
        self.client.loop_stop()
        self.client.disconnect()
        
    def reset (self):
        self.stop()
        self.setup()

    def raffi_check(self, current_box, expected_key):

        if self.keyboard_key == expected_key:

            #si las cajas están habilitadas por el ciclo:
            if self.model.cajas_habilitadas[current_box] == 1 or self.model.cajas_habilitadas[current_box] == 2:

                if self.keyboard_value == True:
                    self.model.raffi[current_box] = 1

                    command_plc = {f"raffi_{current_box}": True}
                    self.client.publish(self.model.pub_topics["plc"],json.dumps(command_plc), qos = 2)

                elif self.keyboard_value == False:
                    self.model.raffi[current_box] = 0

                    command_plc = {f"raffi_{current_box}": False}
                    self.client.publish(self.model.pub_topics["plc"],json.dumps(command_plc), qos = 2)
        

    def mensajes_clamp (self, current_box, payload):

        #variable para poner la serie de la caja en las cajas que sea necesario
        serie = ""
        if "MFB-P2" in current_box:
            serie = self.model.mfbp2_serie
        if "PDC-R" in current_box:
            serie = self.model.pdcr_serie

        payload_str = json.dumps(payload)       # convertir diccionario payload a string y guardarlo

        if current_box in payload_str: #busca en el string el nombre del nido

            #0, no se solicitan en ciclo
            #1, ya no requiere QR
            #2, requiere QR
            #3, cajas terminadas en el ciclo

            current_box_pub = current_box.replace("-","")
            if current_box == "PDC-RMID":
                current_box_pub = "PDCR"

            #cajas que no están en ciclo
            if self.model.cajas_habilitadas[current_box] == 0 or self.model.cajas_habilitadas[current_box] == 3:

                command = {f"lbl_box{current_box_pub}" : {"text": "", "color": "blue"}}

            #se busca que la caja esté habilitada por el ciclo
            elif self.model.cajas_habilitadas[current_box] == 1 or self.model.cajas_habilitadas[current_box] == 2:

                if f"raffi_{current_box}" in payload:
                    if payload[f"raffi_{current_box}"] == False:
                        self.nido_pub = f"{current_box} {serie}:\n clampeada"
                        self.color_nido = "green"
                        if self.model.cajas_habilitadas[current_box] == 2:
                            self.nido_pub = f"{current_box} {serie}:\n Esperando QR"
                            self.color_nido = "purple"
                            if current_box == "PDC-P" or current_box == "BATTERY" or current_box == "BATTERY-2" or current_box == "MFB-E":
                                self.nido_pub = f"{current_box}:\n Habilitada"
                                self.color_nido = "blue"
                if current_box in payload:
                    if payload[current_box] == True:
                        self.nido_pub = f"{current_box} {serie}:\n Habilitada"
                        self.color_nido = "blue"
                        self.model.raffi[current_box] = 0 # se reinicia el raffi a 0 (desactivado)
                    if payload[current_box] == False:
                        self.nido_pub = ""
                        self.color_nido = "blue"
                        self.model.raffi[current_box] = 0 # se reinicia el raffi a 0 (desactivado)
                        if self.model.cajas_habilitadas[current_box] == 2:
                            self.nido_pub = f"{current_box} {serie}:\n Esperando QR"
                            self.color_nido = "purple"
                            if current_box == "PDC-P" or current_box == "BATTERY" or current_box == "BATTERY-2" or current_box == "MFB-E":
                                self.nido_pub = f"{current_box}:\n Habilitada"
                                self.color_nido = "blue"
                if f"clamp_{current_box}" in payload:
                    if payload[f"clamp_{current_box}"] == True:
                        self.nido_pub = f"{current_box} {serie}:\n clampeada"
                        self.color_nido = "green"
                        self.model.raffi[current_box] = 0 # se reinicia el raffi a 0 (desactivado)
                if f"raffi_{current_box}" in payload:
                    if payload[f"raffi_{current_box}"] == True:
                        self.nido_pub = f"{current_box} {serie}:\n raffi activado"
                        self.color_nido = "orange"

                #casos especiales:
                if "clamp_MFB-E" in payload:
                    if payload["clamp_MFB-E"] == False:
                        self.nido_pub = ""
                        self.color_nido = "blue"
                        self.model.raffi["MFB-E"] = 0
                if "clamp_BATTERY" in payload:
                    if payload["clamp_BATTERY"] == False:
                        self.nido_pub = ""
                        self.color_nido = "blue"
                        self.model.raffi["BATTERY"] = 0
                if "clamp_PDC-P" in payload:
                    if payload["clamp_PDC-P"] == False:
                        self.nido_pub = ""
                        self.color_nido = "blue"
                        self.model.raffi["PDC-P"] = 0
            

                #cuando es SMALL se habilita el nido en MID, entonces si la bandera es true, cambiar mensaje
                if self.model.smallflag == True:
                    self.nido_pub = self.nido_pub.replace("PDC-RMID","PDC-RSMALL")

                if "encoder" in payload_str:
                    pass
                else:
                    command = {f"lbl_box{current_box_pub}" : {"text": f"{self.nido_pub}", "color": f"{self.color_nido}"}}
                    self.client.publish(self.model.pub_topics["gui"],json.dumps(command), qos = 2)


    def on_connect(self, client, userdata, flags, rc):
        try:
            connections = {
               "correct": True,
               "fails": "" 
               }
            for topic in self.model.sub_topics:
                client.subscribe(self.model.sub_topics[topic])
                if rc == 0:
                    print(f"Manager MQTT client connected to {topic} with code [{rc}]")
                else:
                    connections["correct"] = False
                    connection["fails"] += topic + "\n"
                    print("Manager MQTT client connection to " + topic + " fail, code [{}]".format(rc))
            if connections["correct"] == True:
               self.conn_ok.emit()
            else:
                print("Manager MQTT client connections fail:\n" + connection["fails"])
                self.conn_nok.emit()
        except Exception as ex:
            print("Manager MQTT client connection fail. Exception: ", ex)
            self.conn_nok.emit()

    def on_message(self, client, userdata, message):
        try:
            payload = json.loads(message.payload)
            print ("   " + message.topic + " ", payload) 

            if message.topic == self.model.sub_topics["plc"]:
                if "emergency" in payload:
                    self.model.input_data["plc"]["emergency"] = payload["emergency"]
                    Timer(0.05, self.model.log, args = ("STOP",)).start() 
                    if payload["emergency"] == False:
                        self.emergency.emit()
                        command = {
                            "popOut":"Paro de emergencia activado"
                            }
                        self.client.publish(self.model.pub_topics["gui"],json.dumps(command), qos = 2)
                    else:
                        #QTimer.singleShot(1000, self.closePopout)
                        self.closePopout()

            if self.model.input_data["plc"]["emergency"] == False:
                return

            if message.topic == self.model.sub_topics["keyboard"]:
                #ejemplo de mensaje: { "keyboard_E" : true }
                payload_str = json.dumps(payload)       # convertir diccionario payload a string y guardarlo
                payload_str = payload_str.replace("{","")
                payload_str = payload_str.replace("}","")
                payload_str = payload_str.replace('"',"")
                payload_str = payload_str.replace("true","True")
                payload_str = payload_str.replace("false","False")
                payload_str = payload_str.replace(" ","")
                separate_msj = payload_str.rsplit(":")
                self.keyboard_key = separate_msj[0]
                #eval() evalua una cadena de caracteres y decide si es True o False si cumple con las entradas esperadas convirtiendolo a booleano
                self.keyboard_value = eval(separate_msj[1])

                #print("key: ",self.keyboard_key)
                #print("value: ",self.keyboard_value)

                if self.llave == True:

                    if self.keyboard_key == "keyboard_esc":
                        command = {"popOut":"close"}
                        self.client.publish(self.model.pub_topics["gui"],json.dumps(command), qos = 2)
                        print("key no emit")
                    elif self.keyboard_key == "keyboard_enter":
                        command = {"popOut":"close"}
                        self.client.publish(self.model.pub_topics["gui"],json.dumps(command), qos = 2)
                        self.key.emit()
                        print("key emit")
                    else:
                        command = {"popOut":"Mensaje no recibido, gire la llave nuevamente"}
                        self.client.publish(self.model.pub_topics["gui"],json.dumps(command), qos = 2)
                        print("key no emit")


                    self.llave = False

                self.raffi_check("PDC-R", "keyboard_F9")
                self.raffi_check("PDC-RMID", "keyboard_F9")
                self.raffi_check("MFB-P2", "keyboard_F8")
                self.raffi_check("MFB-S", "keyboard_F7")
                self.raffi_check("MFB-P1", "keyboard_F6")
                self.raffi_check("BATTERY", "keyboard_F5")
                #self.raffi_check("BATTERY-2", "keyboard_F4")
                #self.raffi_check("MFB-E", "keyboard_F3")
                self.raffi_check("PDC-D", "keyboard_F2")
                self.raffi_check("PDC-P", "keyboard_F1")
                #print("raffi: ")
                #print(self.model.raffi)


            if message.topic == self.model.sub_topics["plc"]:
                for i in list(payload):
                    if "clamp_" in i:
                        box = i[6:]
                        if payload[i] == True:
                            if not(box in self.model.input_data["plc"]["clamps"]):
                                self.model.input_data["plc"]["clamps"].append(box)
                                self.clamp.emit() 
                        else:
                            if box in self.model.input_data["plc"]["clamps"]:
                                self.model.input_data["plc"]["clamps"].pop(self.model.input_data["plc"]["clamps"].index(box))

                if "key" in payload:
                    if payload["key"] == True:
                        # si la variable es True, quiere decir que hubo un mal torqueo y se requiere llave para habilitar la reversa
                        if self.model.reintento_torque == True:
                            self.key.emit()
                        # si la variable es False, quiere decir que estás en otra parte del proceso y la llave reiniciará el ciclo
                        elif self.model.reintento_torque == False:
                            command = {"popOut":"¿Seguro que desea dar llave?\n Presione Esc. para salir, Enter para continuar..."}
                            self.client.publish(self.model.pub_topics["gui"],json.dumps(command), qos = 2)
                            self.llave = True

                if "button" in payload:
                    if payload["button"] == True:
                        print("Activando clamp para BATTERY-2")
                        #print("Input data plc clamps ANTES: ",self.model.input_data["plc"]["clamps"])
                        if not("BATTERY-2" in self.model.input_data["plc"]["clamps"]):
                            self.model.input_data["plc"]["clamps"].append("BATTERY-2")
                            #print("Input data plc clamps DESPUES: ",self.model.input_data["plc"]["clamps"])
                            ######### Modificación para etiqueta BATTERY-2 #########
                            command = {
                                "lbl_boxBATTERY2" : {"text": "", "color": "purple"},
                                }
                            self.client.publish(self.model.pub_topics["gui"],json.dumps(command), qos = 2)
                            self.client.publish(self.model.pub_topics["gui_2"],json.dumps(command), qos = 2)
                            ######### Modificación para etiqueta BATTERY-2 #########
                            self.clamp.emit() 

                #ejemplo de mensaje:
                #PLC/1/status       {"encoder":1,"name":{"PDC-D":"E1"},"value":True}
                #DESDE GDI SERÍA:   {"encoder": 2,"name": "{\"PDC-R\":\"E1\"}","value":true}
                # SI EL MENSAJE MQTT CONTIENE ENCODER, NAME y VALUE...
                if "encoder" in payload and "name" in payload and "value" in payload:

                    #CAMBIAR {"PDC-R":"E1"} por {"PDC-RMID":"E1"} o {"PDC-RS":"E1"} según corresponda
                    if "PDC-R" in payload["name"] and "PDC-RMID" in self.model.input_data["database"]["modularity"]:
                        payload["name"] = payload["name"].replace("PDC-R", "PDC-RMID")
                    if "PDC-R" in payload["name"] and "PDC-RS" in self.model.input_data["database"]["modularity"]:
                        payload["name"] = payload["name"].replace("PDC-R", "PDC-RS")

                    #obtener encoder_1, encoder_2 o encoder_3
                    encoder = "encoder_" + str(payload["encoder"])

                    #aquí entra cuando "value = False"...
                    if not(payload["value"]):
                        #actualizar payload["name"] actual con 0, ejemplo: {"PDC-D":"0"}
                        payload["name"] = payload["name"][:payload["name"].find(":") + 1] + '"0"}'


                    current_tool = "tool"+ str(payload["encoder"])
                    print("current_tool: ",current_tool)
                    

                    #a este punto llegas con un payload["name"] que vale a la caja:terminal {"PDC-D":"E1"} o con un valor de 0 {"PDC-D":"0"}
                    #las zonas se inicializan en zone = "0" desde el código torque.py línea 120.. entonces
                    #si zona guardada para el encoder actual ..es diferente de la zona actual...  (porque al ser true la zona vale "E1" en lugar de "0"
                    if self.model.input_data["plc"][encoder]["zone"] != payload["name"]:
                        for i in self.model.input_data["plc"]:

                            #i = emergency, encoder_1, etc.
                            if "encoder" in i:
                                if i == encoder:
                                    #ejemplo: en self.model.input_data["plc"] ::::: [encoder_2]["zone"] = "{"PDC-D":"E1"}"
                                    self.model.input_data["plc"][i]["zone"] = payload["name"]
                                else:
                                    #ejemplo: en self.model.input_data["plc"] ::::: [encoder_2]["zone"] = {}
                                    self.model.input_data["plc"][i]["zone"] = "{}"
                        
                        print("herramienta activa: ",self.model.herramienta_activa)
                        #si la herramienta actual es igual a la herramienta activa o la herramienta activa es cero
                        if self.model.herramienta_activa == "0" or (current_tool == self.model.herramienta_activa):
                            self.zone.emit()
                            print("emit zoneeeee")
                        
                            

                if "retry_btn" in payload:
                    self.model.input_data["plc"]["retry_btn"] = bool(payload["retry_btn"])
                    if payload["retry_btn"] == True:
                        self.retry_btn.emit()

                #se habilita la función mensajes_clamp cada que llega un mensaje del PLC
                for i in self.nido:
                    self.mensajes_clamp(i,payload)

            if message.topic == self.model.sub_topics["torque_1"] or message.topic == self.model.sub_topics["torque_2"] or message.topic == self.model.sub_topics["torque_3"]:
            #if "torque/" in message.topic and "/status" in message.topic:
                if "result" in payload: 
                    for item in payload:
                        payload[item] = float(payload[item])

                    if message.topic == self.model.sub_topics["torque_1"]:
                        tool = "tool1"
                    if message.topic == self.model.sub_topics["torque_2"]:
                        tool = "tool2"
                    if message.topic == self.model.sub_topics["torque_3"]:
                        tool = "tool3"

                    #tool = "tool" + message.topic[7]
                    if tool in self.model.input_data["torque"]:
                        self.model.input_data["torque"][tool] = copy(payload)
                        self.torque.emit() 

            if message.topic == self.model.sub_topics["gui"]:
                if "request" in payload:
                    self.model.input_data["gui"]["request"] = payload["request"]
                    if payload["request"] == "login":
                        self.login.emit()
                    elif payload["request"] == "logout":
                        self.logout.emit()
                    elif payload["request"] == "config":
                        self.config.emit()
                if "ID" in payload:
                    self.model.input_data["gui"]["ID"] = payload["ID"]
                    self.ID.emit()
                if "code" in payload:
                    self.model.input_data["gui"]["code"] = payload["code"]
                    self.code.emit()
                if "visible" in payload:
                    self.model.input_data["gui"]["visible"] = payload["visible"]
                    self.visible.emit()

            if message.topic == self.model.sub_topics["config"]:
                if "finish" in payload:
                    if payload["finish"] == True:
                        self.config_ok.emit()
                if "shutdown" in payload:
                    if payload["shutdown"] == True:
                        self.model.shutdown = True

            if message.topic == self.model.sub_topics["gui"] or message.topic == self.model.sub_topics["gui_2"]:
                if "qr_box" in payload:
                    self.qr_box.emit(payload["qr_box"])  

        except Exception as ex:
            print("input exception", ex)

    def closePopout (self):
        command = {
            "popOut":"close"
            }
        self.client.publish(self.model.pub_topics["gui"],json.dumps(command), qos = 2)

if __name__ == "__main__":
    from PyQt5.QtWidgets import QApplication
    from manager.model import model
    import sys
    app = QApplication(sys.argv)
    model = model.manager()
    client = mqttClient(model)
    sys.exit(app.exec_())

