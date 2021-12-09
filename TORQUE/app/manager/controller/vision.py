from PyQt5.QtCore import QState, pyqtSignal
from paho.mqtt import publish
from threading import Timer
from cv2 import imwrite, imread
from time import strftime
from shutil import copy
from math import ceil
import json

class WaitClamp (QState):

    def __init__(self, module = "module1", model = None, parent = None):
        super().__init__(parent)
        self.model = model
        self.module = module

    def onEntry(self, event):
        for item in self.model.vision_data[self.module]["trigs"]:
            self.model.vision_data[self.module]["queue"].append(item)
        command = {
            "lbl_info1" : {"text": "", "color": "black"},
            "lbl_info2" : {"text": "", "color": "green"},
            "lbl_result" : {"text": "Inspección de visión preparada", "color": "green"},
            "lbl_steps" : {"text": "Coloca las cajas en los nidos de visión", "color": "black"}
            }
        publish.single(self.model.pub_topics["gui"],json.dumps(command),hostname='127.0.0.1', qos = 2)
        Timer(0.1, self.visionClam).start()

    def visionClam (self):
        publish.single(self.model.pub_topics["plc"],json.dumps({"nidosv1" : True, "nidosv2" : True}),hostname='127.0.0.1', qos = 2)

    def onExit(self, QEvent):
        command = {
            "lbl_result" : {"text": "Realizando inspección por visión", "color": "green"},
            "lbl_steps" : {"text": "Espera el resultado", "color": "black"},
            "img_center" : "fusibles.jpg",
            }
        publish.single(self.model.pub_topics["gui"],json.dumps(command),hostname='127.0.0.1', qos = 2)    


class Triggers (QState):
    ok      = pyqtSignal()
    nok     = pyqtSignal()

    def __init__(self, module = "module1", model = None, parent = None):
        super().__init__(parent)
        self.model = model
        self.module = module
        self.pub_topic = self.model.pub_topics["vision"][self.module]
        self.queue = self.model.vision_data[self.module]["queue"]
        self.BB = self.model.vision_BB

    def onEntry(self, event):
        current_trig = self.model.vision_data[self.module]["current_trig"]
        if current_trig == None:
            if len(self.queue) > 0:
                current_trig = self.queue.pop(0)
                self.model.vision_data[self.module]["current_trig"] = current_trig
            else:
                self.finish()
                return
        command = {
                    "trigger": current_trig
                    }
        publish.single(self.pub_topic, json.dumps(command), hostname='127.0.0.1', qos = 2)

    def finish (self):
        
        results = self.model.vision_data[self.module]["results"]
        print ("\nVision Results: ", results, "\n")
        img = self.model.vision_img
        error = False
        filter = []
        BB_cnt = 0

        epoches = self.model.vision_data[self.module]["epoches"]
        thresh = ceil(epoches/2)

        for i in range(len(results)):
            filter.append([0]* len(results[i][0]))
            for j in range(len(results[i])):
                for k in range(len(results[i][j])):
                    filter[i][k] = filter[i][k] + results[i][j][k]

            for item in range(len(filter[i])):
                temp = [self.BB[BB_cnt], self.BB[BB_cnt + 1]]
                if filter[i][item] >= thresh:
                    img = self.model.drawBB(img = img, BB = temp, color = (0, 255, 0))
                else:
                    error = True
                    img = self.model.drawBB(img = img, BB = temp, color = (0, 0, 255))
                BB_cnt += 2

        imwrite("imgs/fusibles.jpg", img)
        #print("\n\tVISION FILTER\n", filter, "\n")

        name = self.model.local_data["qr"]["num_parte"] + "REV"
        name += self.model.local_data["qr"]["rev"] + "-"  + strftime("%d%b%Y-%H%M%S")
        if error == False:
            copy('C:/images/FUSES/TEMP.jpg', 'C:/images/FUSES/' + name + '-FAIL' + '.jpg')
            copy('C:/images/RELAYS/TEMP.jpg', 'C:/images/RELAYS/' + name + '-FAIL' + '.jpg')
            command = {
                "lbl_result" : {"text": "Vision OK", "color": "green"},
                "lbl_steps" : {"text": "Generando etiqueta", "color": "black"},
                "img_center" : "fusibles.jpg",
                }
            publish.single(self.model.pub_topics["gui"],json.dumps(command),hostname='127.0.0.1', qos = 2)
            Timer(1,self.ok.emit).start()
        else:
            copy('C:/images/FUSES/TEMP.jpg', 'C:/images/FUSES/' + name + '-PASS' + '.jpg')
            copy('C:/images/RELAYS/TEMP.jpg', 'C:/images/RELAYS/' + name + '-PASS' + '.jpg')
            command = {
                "lbl_result" : {"text": "Vision NOK", "color": "red"},
                "lbl_steps" : {"text": "Presiona el boton de reintento", "color": "black"},
                "img_center" : "fusibles.jpg",
                }
            publish.single(self.model.pub_topics["gui"],json.dumps(command),hostname='127.0.0.1', qos = 2)
            self.nok.emit()


class Receiver (QState):
    ok      = pyqtSignal()
    nok     = pyqtSignal()

    def __init__(self, module = "module1", model = None, parent = None):
        super().__init__(parent)
        self.model = model
        self.module = module
        self.pub_topic = self.model.pub_topics["vision"][self.module]
        self.epoches = self.model.vision_data[self.module]["epoches"]
        self.thresh = ceil(self.epoches/2)
        self.epoch_cnt = 0
        self.score = 0
        

    def onEntry(self, event):
        trigs_cnt = self.model.vision_data[self.module]["trigs_cnt"]
        temp = []
        ok = True
        for item in self.model.input_data["vision"]["result"]:
           temp.append(item)
           if item == False:
               ok = False
        self.model.vision_data[self.module]["results"][trigs_cnt].append(temp)  #Esto es para evitar mandar el valor como referencia y etonces se sobreescriba con la siguientre respuesta de vision
        self.epoch_cnt += 1
        if ok:
            self.score += 1
        if self.score == self.thresh or self.epoch_cnt == self.epoches:
            self.score = 0
            self.epoch_cnt = 0
            self.model.vision_data[self.module]["current_trig"] = None
            trigs_cnt += 1
            if trigs_cnt < len(self.model.vision_data[self.module]["trigs"]):
                self.model.vision_data[self.module]["results"].append([])
            if trigs_cnt == 1:
                copy('C:\images\LASTINSPECTION.jpg', 'C:/images/FUSES/TEMP.jpg')
            elif trigs_cnt== 2:
                copy('C:\images\LASTINSPECTION.jpg', 'C:/images/RELAYS/TEMP.jpg')
        self.model.vision_data[self.module]["trigs_cnt"] = trigs_cnt
        self.ok.emit()


class Error (QState):
    ok      = pyqtSignal()
    nok     = pyqtSignal()

    def __init__(self, module = "module1", model = None, parent = None):
        super().__init__(parent)
        self.model = model
        self.module = module

    def onEntry(self, event):
        #self.model.vision_data[self.module]["queue"] = []
        self.model.vision_data["module1"]["trigs_cnt"] = 0
        self.model.vision_data["module1"]["results"] = [[]]
        for item in self.model.vision_data[self.module]["trigs"]:
            self.model.vision_data[self.module]["queue"].append(item)

    def onExit(self, QEvent):
        self.model.vision_img = imread('imgs/workspace.jpg')
        command = {
            "lbl_result" : {"text": "Reintentando inspección por visión", "color": "green"},
            "lbl_steps" : {"text": "Espera el resultado", "color": "black"},
            }
        publish.single(self.model.pub_topics["gui"],json.dumps(command),hostname='127.0.0.1', qos = 2)


