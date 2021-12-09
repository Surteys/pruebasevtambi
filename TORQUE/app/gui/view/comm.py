
# -*- coding: utf-8 -*-
"""
@authors: MSc. Marco Rutiaga Quezada
          MSc. Aarón Castillo Tobías
          Ing. Rogelio García
"""

from PyQt5.QtCore import pyqtSignal, pyqtSlot, QTimer
from PyQt5.QtCore import QObject

from paho.mqtt.client import Client
import json

class MqttClient (QObject):
    subscribe = pyqtSignal(dict)

    def __init__(self, model = None, parent = None):
        super().__init__(parent)
        self.model = model
        self.client = Client()
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        QTimer.singleShot(5000, self.setup)
        
    def setup(self):
        try:
            self.client.connect(host = "127.0.0.1", port = 1883, keepalive = 60)
            self.client.loop_start()
        except Exception as ex:
            print("GUI MQTT client connection fail. Exception:\n", ex.args)
            self.subscribe.emit(
                    {
                        "popOut": "GUI MQTT connection fail",
                        "lbl_result" : {"text": "GUI MQTT connection fail", "color": "red"}, 
                        "lbl_steps" : {"text": "Check broker and restart", "color": "black"}
                    })
            QTimer.singleShot(2000, self.closePopout)

    def on_connect(self, client, userdata, flags, rc):
        try:
            client.subscribe(self.model.setTopic)
            if rc == 0:
                print("GUI MQTT client connected with code [{}]".format(rc))
            else:
                print("GUI MQTT client connection fail, code [{}]".format(rc))
                self.subscribe.emit(
                    {
                        "popOut": "GUI MQTT connection fail",
                        "lbl_result" : {"text": "GUI MQTT connection fail", "color": "red"}, 
                        "lbl_steps" : {"text": "Check broker and restart", "color": "black"}
                    }) 
        except Exception as ex:
            print("GUI MQTT client connection fail. Exception: ", ex.args())
            self.subscribe.emit(
                    {
                        "popOut": "GUI MQTT connection fail",
                        "lbl_result" : {"text": "GUI MQTT connection fail", "color": "red"}, 
                        "lbl_steps" : {"text": "Check broker and restart", "color": "black"}
                    })
            QTimer.singleShot(2000, self.closePopout)

    def on_message(self, client, userdata, message):
        try:
            payload = json.loads(message.payload)
            #print ("   " + message.topic + " ", payload)
            self.subscribe.emit(payload)
        except Exeption as ex:
            print(ex.args)

    @pyqtSlot(dict)
    def publish (self, message):
        try:
            self.client.publish(self.model.statusTopic,json.dumps(message), qos = 2)
            #print("GUI piublish:", message, "in topic: ", self.model.statusTopic)
        except Exception as ex:
            print (ex.args)

    def closePopout (self):
        try:
            self.subscribe.emit({"popOut": "close"})
        except Exception as ex:
            print (ex.args)
