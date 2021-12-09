# -*- coding: utf-8 -*-
"""
Created on Thu Dec 19 10:36:34 2019

@author: marco

"""

import paho.mqtt.client as mqtt
import json
from time import sleep
import random


def on_connect(client, userdata, flags, rc):
    print("Connected with result code {}".format(rc))
    client.subscribe("#")
    
def on_message(client, userdata, message):
    payload = message.payload.decode("utf-8")
    print (payload)
    
def publish (topic = None, message = None, qos = 2):
    global client
    if topic == None :
        topic = "plc/status"
    if message == None :
        message = {"boxest" : True}
    payload = json.dumps(message)
    client.publish(topic,payload, qos = qos)

def setup (host = "localhost", port = "1883"):
    global client
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(host)
    client.loop_start()
    
def stop ():
    global client
    sleep(0.5)
    client.loop_stop()
    client.disconnect()
    print("Good bye...")
    
if __name__ == "__main__":    
    
    encoder = True
    llave = True
    delay = 1

    #mode = ["untwist", "flex", "all_boxes"]
    mode = []

    #torques = {
    #    "PDC-P": {
    #        "E1": ["tool1",3,"tuerca_x"]},
    #    "PDC-D": {
    #        "E1": ["tool1",2,"tuerca_x"]},
    #    "BATTERY": {
    #        "BT": ["tool1",5,"tuerca_x"]},
    #    "BATTERY-2": {
    #        "BT": ["tool1",5,"tuerca_x"]},
    #    "MFB-P1": {
    #        "A47": ["tool2",4,"tuerca_x"],
    #        "A46": ["tool2",4,"tuerca_x"],
    #        "A45": ["tool1",4,"tuerca_x"],
    #        "A44": ["tool1",4,"tuerca_x"],
    #        "A43": ["tool1",4,"tuerca_x"],
    #        "A41": ["tool2",4,"tuerca_x"], 
    #        "A42": ["tool1",4,"tuerca_x"]},
    #    "MFB-S": {
    #        "A51": ["tool2",5,"tuerca_x"],
    #        "A52": ["tool2",5,"tuerca_x"],
    #        "A53": ["tool3",5,"tuerca_x"],
    #        "A54": ["tool3",5,"tuerca_x"],
    #        "A55": ["tool3",5,"tuerca_x"],
    #        "A56": ["tool3",5,"tuerca_x"]},
    #    "MFB-P2": {
    #        "A20": ["tool2",2,"tuerca_x"],
    #        "A21": ["tool3",2,"tuerca_x"],
    #        "A22": ["tool3",2,"tuerca_x"],
    #        "A23": ["tool3",2,"tuerca_x"],
    #        "A24": ["tool3",2,"tuerca_x"],
    #        "A25": ["tool2",2,"tuerca_x"], 
    #        "A26": ["tool3",2,"tuerca_x"], 
    #        "A27": ["tool3",2,"tuerca_x"], 
    #        "A28": ["tool3",2,"tuerca_x"], 
    #        "A29": ["tool3",2,"tuerca_x"], 
    #        "A30": ["tool2",2,"tuerca_x"]},
    #    "PDC-R": {
    #        "E1": ["tool2",3,"tuerca_x"]}
    #    }

    torques = {
        "PDC-R": {
            "E1": ["tool2",3,"tuerca_x"]},
        "MFB-P2": {
            "A20": ["tool2",2,"tuerca_x"],
            "A21": ["tool3",2,"tuerca_x"],
            "A22": ["tool3",2,"tuerca_x"],
            "A23": ["tool3",2,"tuerca_x"],
            "A24": ["tool3",2,"tuerca_x"],
            "A25": ["tool2",2,"tuerca_x"], 
            "A26": ["tool3",2,"tuerca_x"], 
            "A27": ["tool3",2,"tuerca_x"], 
            "A28": ["tool3",2,"tuerca_x"], 
            "A29": ["tool3",2,"tuerca_x"], 
            "A30": ["tool2",2,"tuerca_x"]}
        }
        
    setup()
    sleep(0.5)
    while True:
        try:        
            order = list(torques)
            order.sort()  
            cnt = 0   
            for i in order:
                if cnt == 0:
                    if not("untwist" in mode):
                        sleep(delay)
                        publish(topic = "plc/status", message = {"key": True})
                        sleep(4)
                    if "all_boxes" in mode:
                        for j in order:
                            clamp = "clamp_" + j
                            if j == "MFB-P2":
                                sleep(delay)
                                publish(topic = "gui/status", message = {"qr_box": "7"})
                            if j == "PDC-R":
                                sleep(delay)
                                publish(topic = "gui/status", message = {"qr_box": "8"})
                            if j == "PDC-RMID":
                                sleep(delay)
                                publish(topic = "gui/status", message = {"qr_box": "9"})
                            sleep(2)
                            publish(topic = "plc/status", message = {clamp: True})
                sleep(delay)
                clamp = "clamp_" + i
                if i == "MFB-P2":
                    sleep(delay)
                    publish(topic = "gui/status", message = {"qr_box": "7"})
                if i == "PDC-R":
                    sleep(delay)
                    publish(topic = "gui/status", message = {"qr_box": "8"})
                if i == "PDC-RMID":
                    sleep(delay)
                    publish(topic = "gui/status", message = {"qr_box": "9"})
                sleep(delay)
                publish(topic = "plc/status", message = {clamp: True})
                cnt += 1
                order1 = list(torques[i])
                order1.sort()
                if "flex" in mode:
                    order1.sort(reverse=True)
                for j in order1:
                    sleep(delay)
                    encoder = torques[i][j][0][4]
                    name = json.dumps({i:j})
                    publish(message = {"encoder":encoder, "name": name, "value": True})
                    sleep(delay)
                    topic = "torque/" + encoder + "/status"
                    #if not("untwist" in mode):
                    #    #for k in range(random.randrange(0,4,1)):
                    #        #sleep(delay)
                    #        #publish(topic = topic, message = {"result": 0, "revs":1000, "torque": 8.12345, "torquemin": "3", "torquemax": "5", "anglemin":"1000", "anglemax": "3000"})
                    #        #sleep(delay)
                    #        #publish(topic = "plc/status", message = {"key": True})
                    #        sleep(delay)
                    #        publish(topic = topic, message = {"result": 0, "revs":1000, "torque": 8.12345, "torquemin": "3", "torquemax": "5", "anglemin":"1000", "anglemax": "3000"})
                    #        sleep(delay)
                    publish(topic = topic, message = {"result": 1, "revs":1000, "torque": 8.12345, "torquemin": "3", "torquemax": "5", "anglemin":"1000", "anglemax": "3000"})
                    sleep(delay)
            opt = input("Retry?   y/n: \n")
            if opt == "y" or opt == "Y":
                pass
            else:
                stop()
                break
        except Exception as ex:
            print("\n Exception: ", ex, "\n")
            opt = input("Retry?   y/n: \n")
            if opt == "y" or opt == "Y":
                pass
            else:
                stop()
                break

    
    
