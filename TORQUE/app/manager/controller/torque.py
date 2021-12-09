from PyQt5.QtCore import QState, pyqtSignal, QObject
from paho.mqtt import publish
from threading import Timer
from cv2 import imread, imwrite
from copy import copy
import json


class Torquing (QState):
    finish  = pyqtSignal()
    reset   = pyqtSignal()
    def __init__(self, model = None):
        super().__init__(QState.ParallelStates)
        self.model = model

        self.chkReset   = ChkReset(model = self.model, parent = self)
        self.manager    = ToolsManager(model = self.model, parent = self)
        self.tool1      = NewTool(tool = "tool1", model = self.model, parent = self)
        self.tool2      = NewTool(tool = "tool2", model = self.model, parent = self)
        self.tool3      = NewTool(tool = "tool3", model = self.model, parent = self)

        #transición al clampear una caja
        self.manager.addTransition(self.model.transitions.clamp, self.manager)
        self.manager.addTransition(self.tool1.finish, self.manager)
        self.manager.addTransition(self.tool2.finish, self.manager)
        self.manager.addTransition(self.tool3.finish, self.manager)

        self.manager.ok1.connect(self.tool1.trigger.emit)
        self.manager.ok2.connect(self.tool2.trigger.emit)
        self.manager.ok3.connect(self.tool3.trigger.emit)


        #señal de finish de que finaliza el ciclo
        self.manager.finish.connect(self.finish.emit)
        self.chkReset.reset.connect(self.reset.emit)

    def clean(self):
        self.tool1.clean()
        self.tool2.clean()
        self.tool3.clean()


class NewTool (QState):
    finish  = pyqtSignal()
    trigger = pyqtSignal()

    def __init__(self, tool = "tool1", model = None, parent = None):
        super().__init__(parent)
        self.model = model
        self.tool = tool

        self.standby        = QState(parent = self)
        self.zone           = CheckZone(tool = self.tool, model = self.model, parent = self)
        self.chk_response   = CheckResponse(tool = self.tool, model = self.model, parent = self)
        self.NOK            = Error(tool = self.tool, model = self.model, parent = self)
        self.backward       = Backward(tool = self.tool, model = self.model, parent = self)

        self.standby.addTransition(self.trigger, self.zone)
        self.zone.addTransition(self.zone.nok, self.standby)
        self.zone.addTransition(self.model.transitions.zone, self.zone)
        self.zone.addTransition(self.model.transitions.torque, self.chk_response)
        self.chk_response.addTransition(self.chk_response.ok, self.zone)
        self.chk_response.addTransition(self.chk_response.nok, self.NOK)
        self.NOK.addTransition(self.model.transitions.retry_btn, self.NOK)
        self.NOK.addTransition(self.NOK.ok, self.backward)
        self.NOK.addTransition(self.model.transitions.key, self.backward)
        self.backward.addTransition(self.model.transitions.zone, self.backward)
        self.backward.addTransition(self.model.transitions.torque, self.zone)
        self.backward.addTransition(self.backward.ok, self.zone)
        self.addTransition(self.finish, self.standby)

        self.zone.ok.connect(self.finished)
        self.NOK.entered.connect(self.error)
        self.NOK.exited.connect(self.retry)

        self.setInitialState(self.standby)

    def error(self):
        self.model.torque_data[self.tool]["error"] = True

    def retry(self):
        Timer(0.1, self.retry_delay).start()
    
    def retry_delay(self):
        self.model.torque_data[self.tool]["error"] = False

    def clean(self):
        self.zone.img_name = ""
        self.zone.flex_BB_drawed = False

    def finished(self):
        self.clean()
        self.finish.emit()


class CheckZone (QState):
    ok      = pyqtSignal()
    nok     = pyqtSignal()

    def __init__(self, tool = "tool1", model = None, parent = None):
        super().__init__(parent)
        self.model = model
        self.tool = tool
        self.pub_topic = self.model.pub_topics["torque"][self.tool]
        self.queue = self.model.torque_data[self.tool]["queue"]
        self.stop = self.model.torque_data[self.tool]["stop_profile"]
        self.backward = self.model.torque_data[self.tool]["backward_profile"] 
        self.delay1 = 0.1
        self.delay2 = 1
        self.nut= ""
        self.oracle= ""
        self.currentTool= ""
        self.BB = self.model.BB
        self.img_name = ""
        self.start = True
        self.encoder = "encoder_" + self.tool[-1]
        self.flex_BB_drawed = False

    def onEntry(self, event):
        zone = "0"

        #si el mensaje del encoder trae enable = False ...
        if not(self.model.torque_data[self.tool]["enable"]):

            self.model.torque_data[self.tool]["rqst"] = False
            Timer(self.delay1, self.profilePub, args = (self.stop,)).start()
            #se emite un NOK y esto hace que vuelva a esperar una señal del encoder
            Timer(0.05, self.nok.emit).start()
            return

        try:
            #temp = valor actual de la zona para encoder de la clase (para este punto enable  fue igual a True)
            temp = self.model.input_data["plc"][self.encoder]["zone"] # {"caja": "torque_name"}
            if temp != "0":
                temp = json.loads(temp)
                #si el mensaje obtenido tiene una longitud (o sea que no es vacío el meensaje)
                if len(temp):
                    #zone toma el valor de la caja  y el torque que se detectó actual con el encoder
                    zone = [list(temp)[0], temp[list(temp)[0]]]  #  ["caja", "torque_name"]
                else:
                    zone = ""
 
        except Exception as ex:
            print (f"CheckZone {self.tool} Exception: ", ex)
            command = {
                "lbl_result" : {"text":f"CheckZone {self.tool} {ex.args}", "color": "red"},
                "lbl_steps" : {"text": "Verificar config. de encoders", "color": "black"}
                }
            #publish.single(self.model.torque_data[self.tool]["gui"],json.dumps(command),hostname='127.0.0.1', qos = 2)
            #self.nok.emit()
            return

        #se da el valor a current_trq de lo que está registrado en torque_data
        current_trq = self.model.torque_data[self.tool]["current_trq"]

        #si el valor de current_trq es None o config_data está en True el flexible_mode
        if current_trq == None or self.model.config_data["flexible_mode"]:
            #si aún hay tareas en cola pendientes por hacer (falta  torquear cosas)
            if len(self.queue):
                flex_BB_array = []

                #se iguala el current_trq a la tarea en cola (la ultima) con el valor de la caja , terminal, profile, y tuerca
                current_trq = self.queue[0] # ["PDC-P", "E1", 3, "tuerca_x"]

                #si la herramienta es la 2
                if self.tool == "tool2":
                    #si la caja en la tarea en cola es MFB-P1...
                    if current_trq[0] == "MFB-P1":
                        #se utiliza la gui_2 la segunda pantalla
                        self.model.torque_data[self.tool]["gui"] = self.model.pub_topics["gui_2"]
                    else:
                        #de lo contrario se utiliza la 1 primer pantalla
                        self.model.torque_data[self.tool]["gui"] = self.model.pub_topics["gui"]
                if self.model.config_data["flexible_mode"]:

                    #se recorren las tareas en cola para ver si es igual a alguna de las tareas pendientes
                    for i in range(len(self.queue)):
                        if not(self.flex_BB_drawed):
                            #se agrega el bounding box para pintarlo
                            flex_BB_array.append([self.queue[i][0], self.queue[i][1]])

                        #si la caja que marca actualmente el encoder es igual a la caja de la tarea en cola actual...
                        if len(zone) and zone[0] == self.queue[i][0]:

                            #si la terminal actual por el encoder es igual a la terminal de la tarea en cola
                            if zone[1] == self.queue[i][1]:

                                #current trq es igual a esa tarea pendiente de la que es igual la caja y la terminal
                                current_trq = self.queue[i]
                                if self.flex_BB_drawed:
                                    break


                self.model.torque_data[self.tool]["current_trq"] = current_trq
                self.nut = current_trq[3]
                print("Self.Nut: ",self.nut)
                print("Self.Tool: ",self.tool)
                if self.nut == "8mm Nut":
                    self.oracle = "Oracle: 1013224"
                if self.nut == "6mm Nut":
                    self.oracle = "Oracle: 1013225"
                if self.nut == "Battery Nut":
                    print("Evento Actual: ",self.model.evento)
                    # Modificación temporal; Si el arnés pertenece al evento PRO1, el oracle de las tuercas para las battery's cambiará. Próximamente se implementará el método automático de selección de oracle, basado en la información de la matriz Excel.
                    if "PRO1" in self.model.evento:
                        self.oracle = "Oracle: 1021441"
                    else:
                        self.oracle = "Oracle: 1013226"
                if self.tool == "tool1":
                    self.currentTool = "HERRAMIENTA 1"
                if self.tool == "tool3":
                    self.currentTool = "HERRAMIENTA 2"
                if self.tool == "tool2":
                    self.currentTool = "HERRAMIENTA 3"

                #se imprime la herramienta actual activa
                print("Current Tool: ",self.currentTool)

                img_name = self.model.imgs_path + "boxes/"+ current_trq[0] + ".jpg"
                #print(" IMG_NAME: ",img_name)

                if self.model.config_data["flexible_mode"]:
                    if not(self.flex_BB_drawed):
                        self.draw(flex_BB_array)
                        self.flex_BB_drawed = True
                else:
                    self.draw([current_trq[0], current_trq[1]])
                command = {
                    "img_nuts" : self.nut + ".jpg",
                    "lbl_nuts" : {"text": self.nut+"\n"+self.oracle, "color": "black"},
                    "img_toolCurrent" : self.currentTool+ ".jpg",
                    "lbl_toolCurrent" : {"text": self.currentTool, "color": "black"},
                    "img_center" : self.tool + ".jpg"
                    }
                publish.single(self.model.torque_data[self.tool]["gui"],json.dumps(command),hostname='127.0.0.1', qos = 2)
            else:
                self.finish()
                return


        #si no hay mensaje de zona: mandar profile a stop
        if not(len(zone)):
            if self.stop != self.model.torque_data[self.tool]["past_trq"]:
                command = {
                            "profile": self.stop
                          }
                print("TOPIC: ",self.pub_topic)
                print("STOP----------",command)
                publish.single(self.pub_topic,json.dumps(command),hostname='127.0.0.1', qos = 2)
                self.model.torque_data[self.tool]["past_trq"] = self.stop
            return

        #si esta variable es True...
        elif self.model.config_data["encoder_feedback"]["tool1"] == True:

            #se inicia profile como stop
            profile = self.stop
            command = {}
            #self.model.torque_data[self.tool]["rqst"] = False


            #si la caja actual es igual a la solicitada de las tareas en cola...
            if zone[0] == current_trq[0]:

                #si la terminal actual es igual a cero...
                if zone[1] == "0":
                    command = {
                        "lbl_result" : {"text":"Herramienta fuera de zona de torque", "color": "red"},
                        "lbl_steps" : {"text": "Coloca la herramienta en " + current_trq[0] + ": " + current_trq[1], "color": "black"}
                        }
                    profile = self.stop

                #si la terminal actual es igual a la terminal solicitada en la tarea actual en cola
                elif zone[1] == current_trq[1]:
                    self.model.torque_data[self.tool]["rqst"] = True
                    command = {
                        "lbl_result" : {"text": "Herramienta en " + zone[0] + ": " + zone[1], "color": "green"},
                        "lbl_steps" : {"text": "Herramienta activada", "color": "black"}
                        }
                    #se da a profile el valor del profile en cola solicitado para esa caja y esa terminal
                    profile = current_trq[2]
                    self.model.herramienta_activa = self.tool
                    print("herramienta activa: ",self.tool)


                    if self.model.config_data["untwist"]:
                        profile = self.model.torque_data[self.tool]["backward_profile"]
                    self.model.torque_data[self.tool]["current_trq"] = current_trq

                #si la terminal actual es diferente de cero y de la solicitada...
                else:
                    command = {
                        "lbl_result" : {"text":"Herramienta en " + zone[0] + ": " + zone[1], "color": "red"},
                        "lbl_steps" : {"text": "Coloca la herramienta en " + current_trq[0] + ": " + current_trq[1], "color": "black"}
                        }
                    profile = self.stop

            #si la caja actual es diferente de la caja solicitada de las tareas en cola...
            else:
                command = {
                    "lbl_result" : {"text":"Herramienta fuera de zona de torque", "color": "red"},
                    "lbl_steps" : {"text": "Coloca la herramienta en " + current_trq[0] + ": " + current_trq[1], "color": "black"}
                    }
                profile = self.stop

        #si self.model.config_data["encoder_feedback"]["tool1"] == False
        else:
            self.model.torque_data[self.tool]["rqst"] = True
            command = {
                "lbl_result" : {"text": "Coloca la herramienta en " + current_trq[0] + ": " + current_trq[1], "color": "green"},
                "lbl_steps" : {"text": "Herramienta activada", "color": "black"} 
                }
            profile = current_trq[2]
            if self.model.config_data["untwist"]:
                profile = self.model.torque_data[self.tool]["backward_profile"]
          

        #finalmente haces un publish del mensaje y le mandas el profile a la herramienta (siempre y cuando sea diferente del profile anterior)
        publish.single(self.model.torque_data[self.tool]["gui"],json.dumps(command),hostname='127.0.0.1', qos = 2)
        Timer(self.delay1, self.profilePub, args = (profile,)).start()

    def draw(self, BB):
        box = self.model.torque_data[self.tool]["current_trq"][0]
        self.model.imgs[box] = self.model.drawBB(
            img = self.model.imgs[box], BB = BB, color = (31, 186, 226))
        imwrite(self.model.imgs_path + self.tool + ".jpg", self.model.imgs[box])

    def profilePub (self, profile):
        if profile != self.model.torque_data[self.tool]["past_trq"]:
            command = {
                        "profile": profile
                      }
            print("TOPIC: ",self.pub_topic)
            print("PROFILE--------",command)
            publish.single(self.pub_topic,json.dumps(command),hostname='127.0.0.1', qos = 2)
            self.model.torque_data[self.tool]["past_trq"] = profile

    def finish(self):
        command = {
            "lbl_nuts" : {"text":"", "color": "black"},
            "lbl_toolCurrent" : {"text":"", "color": "black"},
            "img_nuts" : "blanco.jpg",
            "img_toolCurrent" : "blanco.jpg",
            "lbl_result" : {"text": f"Torques {self.tool} aplicados correctamente", "color": "green"},
            "lbl_steps" : {"text": f"{self.tool} OK", "color": "black"}
            }
        #publish.single(self.model.torque_data[self.tool]["gui"],json.dumps(command),hostname='127.0.0.1', qos = 2)
        Timer(self.delay1, self.profilePub, args = (self.stop,)).start()
        Timer(self.delay2, self.ok.emit).start()
        self.model.torque_data[self.tool]["enable"] = False


class CheckResponse (QState):
    ok      = pyqtSignal()
    nok     = pyqtSignal()

    def __init__(self, tool = "tool1", model = None, parent = None):
        super().__init__(parent)
        self.model = model
        self.tool = tool
        self.stop = self.model.torque_data[self.tool]["stop_profile"]
        self.pub_topic = self.model.pub_topics["torque"][self.tool]
        self.delay1 = 0.15
        self.delay2 = 1
        self.BB = self.model.BB
        self.queue = self.model.torque_data[self.tool]["queue"]

    def onEntry(self, event):
        try:
            if self.model.torque_data[self.tool]["rqst"] == False or self.model.input_data["torque"][self.tool] == {}:
                self.ok.emit()
                return
            else:
                self.model.torque_data[self.tool]["rqst"] = False
                print("TOPIC: ",self.pub_topic)
                print("STOP--------\n profile: ",self.stop)
                publish.single(self.pub_topic,json.dumps({"profile": self.stop}),hostname='127.0.0.1', qos = 2)
                self.model.torque_data[self.tool]["past_trq"] = self.stop
                
                response = copy(self.model.input_data["torque"][self.tool])
                self.model.input_data["torque"][self.tool].clear()
                current_trq = self.model.torque_data[self.tool]["current_trq"]
                box = current_trq[0]
                #print("AQUI ESTÁ LA CAJA: ",box)
                self.model.tries[box][current_trq[1]] += 1
                
                if "2" in self.tool:
                    info1 = self.model.local_data["lbl_info1.2_text"]
                else:
                    info1 = self.model.local_data["lbl_info1_text"]

                if "torque_min" in response:
                    response["torque_min"] = round(response["torque_min"],2)
                else:
                    response["torque_min"] = 0.00

                print("response[torque]: ",response["torque"])
                print("Tipo de dato response[torque]: ", type(response["torque"]))
                response["torque"] = "%.2f" % response["torque"]
                response["torque"] = float(response["torque"])
                print("Tipo de dato Final a base de datos: ", type(response["torque"]))

                if "torque_max" in response:
                    response["torque_max"] = round(response["torque_max"],2)
                else:
                    response["torque_max"] = 0.00

                if "angle_min" in response:
                    response["angle_min"] = int(response["angle_min"])
                else:
                    response["angle_min"] = 0.00
                response["angle"] = round(response["angle"],2)
                if "angle_max" in response :
                    response["angle_max"] = int(response["angle_max"])
                else:
                    response["angle_max"] = 0.00

                trq_zone = box + ":" +  current_trq[1]
                trq_min = str(response["torque_min"])
                trq_applied = str(response["torque"]) + "Nm"
                trq_max = str(response["torque_max"])

                angle_min = str(response["angle_min"])
                angle_applied = str(response["angle"]) + "°"
                angle_max = str(response["angle_max"])

                trq_range = trq_min + "<" + trq_applied + "<" + trq_max
                angle_range = angle_min + "<" + angle_applied + "<" + angle_max

                info2 = trq_zone + "\n"
                info2 += "(" + trq_range + ")\n"
                info2 += "(" + angle_range +")"

                if response["result"] == 1 or self.model.config_data["untwist"]:
                    self.model.imgs[box] = self.model.drawBB(
                    img = self.model.imgs[box], BB =[box, current_trq[1]] , color = (0, 255, 0))
                    imwrite(self.model.imgs_path + self.tool + ".jpg", self.model.imgs[box])
                    #info1 += trq_zone + " ["+ trq_applied + "]\n"

                    command = {
                        "lbl_info1" : {"text": info1, "color": "black"},
                        "lbl_info2" : {"text": info2, "color": "green"},
                        "lbl_result" : {"text": "Torque " + trq_zone + " OK", "color": "green"},
                        "lbl_steps" : {"text": "", "color": "black"},
                        "img_center" : self.tool + ".jpg"
                        }
                    publish.single(self.model.torque_data[self.tool]["gui"],json.dumps(command),hostname='127.0.0.1', qos = 2)

                    self.model.result[box][current_trq[1]] = response["torque"]
                    self.model.resultAngle[box][current_trq[1]] = response["angle"]

                    if "2" in self.tool:
                        self.model.local_data["lbl_info1.2_text"] = info1
                    else:
                        self.model.local_data["lbl_info1_text"] = info1

                    modularity = self.model.input_data["database"]["modularity"]
                    modularity[box].pop(modularity[box].index(current_trq[1]))

                    for i in range(len(self.queue)):
                        if box == self.queue[i][0]:
                            if current_trq[1] == self.queue[i][1]:
                                self.model.torque_data[self.tool]["queue"].pop(i)
                                break
                    
                    if not(len(modularity[box])):
                        modularity.pop(box)
                        Timer(1, self.releaseTorqueClamp, args = (box,)).start()

                    self.model.torque_data[self.tool]["current_trq"]  = None

                    #la herramienta activa terminó el torque bien y puedes habilitar otra
                    self.model.herramienta_activa = "0"
                    Timer(self.delay2, self.ok.emit).start()

                else:
                    self.model.imgs[box] = self.model.drawBB(
                    img = self.model.imgs[box], BB =[box, current_trq[1]] , color = (0, 0, 255))
                    imwrite(self.model.imgs_path + self.tool + ".jpg", self.model.imgs[box])
                    command = {
                        "lbl_info2" : {"text": info2, "color": "red"},
                        "lbl_result" : {"text": "Torque " + trq_zone + " NOK", "color": "red"},
                        "lbl_steps" : {"text": "", "color": "black"},
                        "img_center" : self.tool + ".jpg"
                        }
                    publish.single(self.model.torque_data[self.tool]["gui"],json.dumps(command),hostname='127.0.0.1', qos = 2)
           
                    if self.model.tries[box][current_trq[1]] % 1 == 0:
                        if box in self.model.local_data["nuts_scrap"]:
                            if current_trq[1] in self.model.local_data["nuts_scrap"][box]:
                                self.model.local_data["nuts_scrap"][box][current_trq[1]] += 1
                            else:
                                self.model.local_data["nuts_scrap"][box][current_trq[1]] = 1
                        else:
                            self.model.local_data["nuts_scrap"][box] = {current_trq[1]: 1}
                        command = {
                            "show":{"img_popOut": "scrap.jpg"}
                            }
                        publish.single(self.model.torque_data[self.tool]["gui"],json.dumps(command),hostname='127.0.0.1', qos = 2)
                    Timer(self.delay1, self.nok.emit).start()
        except Exception as ex:
            print("Torque.CheckResponse() Exception:\n", ex)


    def releaseTorqueClamp (self, box):
        #aquí se liberan las cajas desúes de haber finalizado con alguna
        print("Caja DESCLAMPEADA: ",box)
        if box == "PDC-RS":
            publish.single(self.model.pub_topics["plc"],json.dumps({"PDC-RMID" : False}),hostname='127.0.0.1', qos = 2)
        else:
            publish.single(self.model.pub_topics["plc"],json.dumps({box : False}),hostname='127.0.0.1', qos = 2)
        
        copy_box = box
        #caja adecuada:
        if "PDC-R" in box:
            if self.model.smallflag == True:
                copy_box = "PDC-RMID"
            if self.model.mediumflag == True:
                copy_box = "PDC-RMID"
            elif self.model.largeflag == True:
                copy_box = "PDC-R"
        #se avisa a la variable de cajas_habilitadas que ya se terminó esa caja
        self.model.cajas_habilitadas[copy_box] = 3
        


class Error (QState):
    ok      = pyqtSignal()
    nok     = pyqtSignal()

    def __init__(self, tool = "tool1", model = None, parent = None):
        super().__init__(parent)
        self.model = model
        self.tool = tool

    def onEntry(self, event):

        #################################
        self.model.reintento_torque = True
        #################################

        if self.model.config_data["retry_btn_mode"][self.tool] == True:
             command = {
                        "lbl_steps" : {"text": "Gira la llave o presiona el boton de reintento", "color": "black"}
                       }
             if self.model.input_data["plc"]["retry_btn"] == True:
                 Timer(0.05, self.ok.emit).start()
        else:
            command = {
                "lbl_steps" : {"text": "Gira la llave para reintentar", "color": "black"}
                }
        publish.single(self.model.torque_data[self.tool]["gui"],json.dumps(command),hostname='127.0.0.1', qos = 2)


class Backward (QState):
    ok      = pyqtSignal()
    nok     = pyqtSignal()

    def __init__(self, tool = "tool1", model = None, parent = None):
        super().__init__(parent)
        self.model = model
        self.tool = tool
        self.delay1 = 0.1
        self.pub_topic = self.model.pub_topics["torque"][self.tool]
        self.stop = self.model.torque_data[self.tool]["stop_profile"]
        self.backward = self.model.torque_data[self.tool]["backward_profile"]
        self.encoder = "encoder_" + self.tool[-1]

    def onEntry(self, event):

        #################################
        self.model.reintento_torque = False
        #################################

        current_trq = self.model.torque_data[self.tool]["current_trq"] # ["PDC-P", "E1", 3, "tuerca_x"]
        try:
            zone = "0"
            temp = self.model.input_data["plc"][self.encoder]["zone"] # {"caja": "torque_name"}
            if temp != "0":
                temp = json.loads(temp)
                if len(temp):
                    zone = [list(temp)[0], temp[list(temp)[0]]]  #  ["caja", "torque_name"]
                else:
                    return
        except Exception as ex:
            print (f"CheckZone {self.tool} Exception: ", ex)
            command = {
                "lbl_result" : {"text":f"Backward Exception {self.tool} {ex.args}", "color": "red"},
                "lbl_steps" : {"text": "Verificar config. de encoders", "color": "black"}
                }
            #publish.single(self.model.torque_data[self.tool]["gui"],json.dumps(command),hostname='127.0.0.1', qos = 2)
            return
       
        command = {
            "show":{"img_popOut": "close"}
            }
        publish.single(self.model.torque_data[self.tool]["gui"],json.dumps(command),hostname='127.0.0.1', qos = 2)

        if self.model.config_data["encoder_feedback"]["tool1"] == True:
            profile = self.stop
            command = {}
            if zone[0] == current_trq[0]:
                if zone[1] == "0":
                    command = {
                        "lbl_result" : {"text":"Herramienta fuera de zona de torque", "color": "red"},
                        "lbl_steps" : {"text": "Coloca la herramienta en " + current_trq[0] + ": " + current_trq[1], "color": "black"}
                        }
                    profile = self.stop
                elif zone[1] == current_trq[1]:
                    command = {
                        "lbl_result" : {"text": "Herramienta en " + zone[0] + ": " + zone[1], "color": "green"},
                        "lbl_steps" : {"text": "Herramienta activada en REVERSA", "color": "black"}
                        }
                    profile = self.backward
                else:
                    command = {
                        "lbl_result" : {"text":"Herramienta en " + zone[0] + ": " + zone[1], "color": "red"},
                        "lbl_steps" : {"text": "Coloca la herramienta en " + current_trq[0] + ": " + current_trq[1], "color": "black"}
                        }
                    profile = self.stop
            else:
                command = {
                    "lbl_result" : {"text":"Herramienta fuera de zona de torque", "color": "red"},
                    "lbl_steps" : {"text": "Coloca la herramienta en " + current_trq[0] + ": " + current_trq[1], "color": "black"}
                    }
                profile = self.stop
            publish.single(self.model.torque_data[self.tool]["gui"],json.dumps(command),hostname='127.0.0.1', qos = 2)
            Timer(self.delay1, self.profilePub, args = (profile,)).start()
        else:
            self.ok.emit()

    def profilePub (self, profile):
        if profile != self.model.torque_data[self.tool]["past_trq"]:
            command = {
                        "profile": profile
                      }
            print("TOPIC: ",self.pub_topic)
            print("PROFILE BACKWARD--------",command)
            publish.single(self.pub_topic,json.dumps(command),hostname='127.0.0.1', qos = 2)
            self.model.torque_data[self.tool]["past_trq"] = profile
             

class ToolsManager (QState):
    ok1      = pyqtSignal()
    ok2      = pyqtSignal()
    ok3      = pyqtSignal()
    finish  = pyqtSignal()

    def __init__(self, model = None, parent = None):
        super().__init__(parent)
        self.model = model
        self.emty_tools = {}
        self.ready_tools = {}
        self.temporal = ""
    
    def onEntry(self, event):
        modularity = self.model.input_data["database"]["modularity"]
        constraints = self.model.config_data["constraints"]["tools"]
        clamps = self.model.input_data["plc"]["clamps"]
        self.checkTools()
        if not(len (modularity)):
            #si no hay más en la modularidad se finaliza el ciclo
            Timer(0.05,self.finish.emit).start()
            return
        if len(clamps):
            if "PDC-R" in clamps and "PDC-RMID" in modularity:
                    clamps[clamps.index("PDC-R")] = "PDC-RMID"
            ######### Modificación para etiqueta PDC-RS #########
            if "PDC-R" in clamps and "PDC-RS" in modularity:
                    clamps[clamps.index("PDC-R")] = "PDC-RS"
            ######### Modificación para etiqueta PDC-RS #########
            for i in clamps:
                if i in modularity:
                    for j in modularity[i]:
                        if self.emty_tools[self.model.torque_cycles[i][j][0]]:
                            self.model.torque_data[self.model.torque_cycles[i][j][0]]["queue"].append([i, j, self.model.torque_cycles[i][j][1], self.model.torque_cycles[i][j][2]])
                self.checkTools()
            if len(constraints):
                for i in range(len(constraints)):
                    if self.ready_tools[constraints[i][0]] ^ self.ready_tools[constraints[i][1]]:
                        self.ready_tools[constraints[i][0]] = False
                        self.ready_tools[constraints[i][1]] = False
                    elif self.ready_tools[constraints[i][0]] and self.ready_tools[constraints[i][1]]:
                        if not(self.emty_tools[constraints[i][0]]) and not(self.emty_tools[constraints[i][1]]):
                            self.ready_tools[constraints[i][1]] = False
            for i in self.ready_tools:
                if self.ready_tools[i] and not(self.emty_tools[i]):
                    self.model.torque_data[i]["enable"] = True
                    #if len(self.model.torque_data["tool2"]["queue"]):
                    #    temporal = "ok2"
                    #if len(self.model.torque_data["tool1"]["queue"]):
                    #    temporal = "ok1"
                    #if len(self.model.torque_data["tool3"]["queue"]):
                    #    temporal = "ok3"
                elif self.emty_tools[i]:
                    command = {
                        "lbl_result": {"text": ""},
                        "lbl_steps" : {"text": "Coloca una caja en los nidos", "color": "black"},
                        "lbl_info2" : {"text": ""}
                        }
                    publish.single(self.model.torque_data[i]["gui"],json.dumps(command),hostname='127.0.0.1', qos = 2)
            #Timer(0.05, self.ok.emit).start()
            print("Tool que se activa: ",self.temporal)
            # Se activa la herramienta 1 (6mm,Izq)
            if self.temporal == "ok1":
                Timer(0.05, self.ok1.emit).start()
            # Se activa la herramienta 2 (6mm,Centro)
            if self.temporal == "ok2":
                Timer(0.05, self.ok2.emit).start()
            # Se activa la herramienta 3 (8mm,Der)
            if self.temporal == "ok3":
                Timer(0.05, self.ok3.emit).start()
            # Si la variable es "flexible", se activarán todas las herramientas, para permitir al usuario iniciar y seguir el orden que el deseé
            if self.temporal == "flexible":
                Timer(0.05, self.ok1.emit).start()
                Timer(0.05, self.ok2.emit).start()
                Timer(0.05, self.ok3.emit).start()
            if self.temporal == "":
                print("Ninguna Tool se activa!")

        else:
            command = {
                "lbl_result": {"text": ""},
                "lbl_steps" : {"text": "Coloca una caja en los nidos", "color": "black"},
                "lbl_info2" : {"text": ""}
                }
            for i in self.model.torque_data:
                publish.single(self.model.torque_data[i]["gui"],json.dumps(command),hostname='127.0.0.1', qos = 2)
    
    def checkTools(self):
        clamps = self.model.input_data["plc"]["clamps"]
        print("*********CHECK TOOLS*********")
        if self.model.config_data["flexible_mode"]:
            self.temporal = "flexible"
        else:
            if len(clamps):
                print("Clamps:",clamps)
                print("Clamps último:",clamps[-1])
                for x in self.model.torque_data["tool2"]["queue"]:
                    if clamps[-1] in x:
                        print("Aun hay elementos en tool2 para esta caja")
                        self.temporal = "ok2"
                for x in self.model.torque_data["tool1"]["queue"]:
                    if clamps[-1] in x:
                        print("Aun hay elementos en tool1 para esta caja")
                        self.temporal = "ok1"
                for x in self.model.torque_data["tool3"]["queue"]:
                    if clamps[-1] in x:
                        print("Aun hay elementos en tool3 para esta caja")
                        self.temporal = "ok3"

        print("Aquí Tool 1",self.model.torque_data["tool1"]["queue"])
        print("Aquí Tool 2",self.model.torque_data["tool2"]["queue"])
        print("Aquí Tool 3",self.model.torque_data["tool3"]["queue"])
        for item in self.model.torque_data:
            if not(len(self.model.torque_data[item]["queue"])):
                self.emty_tools[item] = True
            else:
                self.emty_tools[item] = False
            self.ready_tools[item] = not(self.model.torque_data[item]["enable"])       


class ChkReset (QState):
    reset   = pyqtSignal()

    def __init__(self, model = None, parent = None):
        super().__init__(parent)
        self.model = model
        
        self.standby = QState(parent = self)
        self.chk_errors = CheckErrors(model = model, parent = self)

        self.standby.addTransition(self.model.transitions.key, self.chk_errors)
        self.chk_errors.addTransition(self.chk_errors.ok, self.standby)
        self.chk_errors.addTransition(self.chk_errors.reset, self.standby)

        self.chk_errors.reset.connect(self.reset.emit)

        self.setInitialState(self.standby)


class CheckErrors (QState):
    ok      = pyqtSignal()
    reset   = pyqtSignal()

    def __init__(self, model = None, parent = None):
        super().__init__(parent)
        self.model = model
        self.errors = False
    def onEntry(self, event):
        self.errors = False
        for item in self.model.torque_data:
            if self.model.torque_data[item]["error"]:
                self.errors = True 
        if self.errors:
            self.errors = False
            self.ok.emit()
        else:
            self.reset.emit()

