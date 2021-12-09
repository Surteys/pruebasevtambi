from cv2 import imread, imwrite, rectangle
from time import strftime
from pickle import load
import requests
import json

class Model (object):

    def __init__(self, parent = None):

        self.shutdown = False
        self.mainWindow = None
        self.transitions = None
        self.imgs_path = "data/imgs/"
        self.datetime = None
        self.imgs = {}
        self.server = "127.0.0.1:5000"
        self.serial = "EVTA-MBI-1"

        ###############################
        #3: cajas terminadas en ciclo, 2:cajas que requieren QR, 1:cajas que no requieren QR, 0:cajas que no solicita el ciclo
        self.cajas_habilitadas = {"PDC-P": 0,"PDC-D": 0,"MFB-P1": 0,"MFB-P2": 0,"PDC-R": 0,"PDC-RMID": 0,"BATTERY": 0,"BATTERY-2": 0,"MFB-S": 0,"MFB-E": 0}
        self.raffi = {"PDC-P": 0,"PDC-D": 0,"MFB-P1": 0,"MFB-P2": 0,"PDC-R": 0,"PDC-RMID": 0,"BATTERY": 0,"BATTERY-2": 0,"MFB-S": 0,"MFB-E": 0}
        self.reintento_torque = False
        self.largeflag = False
        self.mediumflag = False
        self.smallflag = False
        self.pdcr_serie = ""
        self.mfbp2_serie = ""
        self.herramienta_activa = "0"
        ###############################

        self.BB = {'MFB-P1': {'A41': [(533, 349), (575, 393)], 'A42': [(597, 389), (631, 421)], 'A43': [(479, 352), (513, 389)], 'A44': [(431, 354), (466, 386)], 'A45': [(391, 356), (420, 384)], 'A46': [(334, 349), (373, 384)], 'A47': [(266, 352), (310, 388)]}, 'MFB-P2': {'A20': [(527, 272), (576, 313)], 'A21': [(258, 463), (292, 497)], 'A22': [(312, 464), (343, 493)], 'A23': [(362, 464), (393, 493)], 'A24': [(409, 465), (442, 493)], 'A25': [(470, 466), (512, 509)], 'A26': [(538, 463), (572, 497)], 'A27': [(587, 464), (622, 498)], 'A28': [(638, 466), (674, 499)], 'A29': [(687, 464), (725, 496)], 'A30': [(403, 267), (449, 308)]}, 'MFB-S': {'A51': [(447, 265), (493, 311)], 'A52': [(315, 402), (357, 442)], 'A53': [(379, 410), (415, 444)], 'A54': [(430, 411), (464, 447)], 'A55': [(478, 410), (513, 443)], 'A56': [(528, 409), (564, 441)]}, 'MFB-E': {'E1': [(1700, 650), (2250, 1250)], 'A1': [(2600, 1700), (3150, 2300)], 'A2': [(750, 1700), (1300, 2300)]}, 'PDC-D': {'E1': [(358, 467), (396, 507)]}, 'PDC-P': {'E1': [(361, 460), (396, 495)]}, 'PDC-R': {'E1': [(408, 330), (443, 358)]}, 'PDC-RMID': {'E1': [(408, 330), (443, 358)]}, 'PDC-RS': {'E1': [(408, 330), (443, 358)]}, 'BATTERY': {'BT': [(169, 157), (231, 212)]}, 'BATTERY-2': {'BT': [(169, 157), (231, 212)]}}
        #with open("data/BB/BB", "rb") as f:
        #    self.BB= load(f)
             
        self.result = {
            "PDC-P": {
                "E1": None},
            "PDC-D": {
                "E1": None},
            "BATTERY": {
                "BT": None},
            "BATTERY-2": {
                "BT": None},
            "MFB-P1": {
                "A47": None,
                "A46": None,
                "A45": None,
                "A44": None,
                "A43": None,
                "A41": None, 
                "A42": None},
            "MFB-S": {
                "A51": None,
                "A52": None,
                "A53": None,
                "A54": None,
                "A55": None,
                "A56": None},
            "MFB-E": {
                "E1": None,
                "A1": None,
                "A2": None},
            "MFB-P2": {
                "A20": None,
                "A21": None,
                "A22": None,
                "A23": None,
                "A24": None,
                "A25": None,
                "A26": None, 
                "A27": None, 
                "A28": None, 
                "A29": None, 
                "A30": None},
            "PDC-R": {
                "E1": None},
            "PDC-RS": {
                "E1": None},
            "PDC-RMID": {
                "E1": None}
            }

        self.resultAngle = {
            "PDC-P": {
                "E1": None},
            "PDC-D": {
                "E1": None},
            "BATTERY": {
                "BT": None},
            "BATTERY-2": {
                "BT": None},
            "MFB-P1": {
                "A47": None,
                "A46": None,
                "A45": None,
                "A44": None,
                "A43": None,
                "A41": None, 
                "A42": None},
            "MFB-S": {
                "A51": None,
                "A52": None,
                "A53": None,
                "A54": None,
                "A55": None,
                "A56": None},
            "MFB-E": {
                "E1": None,
                "A1": None,
                "A2": None},
            "MFB-P2": {
                "A20": None,
                "A21": None,
                "A22": None,
                "A23": None,
                "A24": None,
                "A25": None,
                "A26": None, 
                "A27": None, 
                "A28": None, 
                "A29": None, 
                "A30": None},
            "PDC-R": {
                "E1": None},
            "PDC-RS": {
                "E1": None},
            "PDC-RMID": {
                "E1": None}
            }

        self.tries = {
            "PDC-P": {
                "E1": 0},
            "PDC-D": {
                "E1": 0},
            "BATTERY": {
                "BT": 0},
            "BATTERY-2": {
                "BT": 0},
            "MFB-P1": {
                "A47": 0,
                "A46": 0,
                "A45": 0,
                "A44": 0,
                "A43": 0,
                "A41": 0, 
                "A42": 0},
            "MFB-S": {
                "A51": 0,
                "A52": 0,
                "A53": 0,
                "A54": 0,
                "A55": 0,
                "A56": 0},
            "MFB-E": {
                "E1": 0,
                "A1": 0,
                "A2": 0},
            "MFB-P2": {
                "A20": 0,
                "A21": 0,
                "A22": 0,
                "A23": 0,
                "A24": 0,
                "A25": 0,
                "A26": 0, 
                "A27": 0, 
                "A28": 0, 
                "A29": 0, 
                "A30": 0},
            "PDC-R": {
                "E1": 0},
            "PDC-RS": {
                "E1": 0},
            "PDC-RMID": {
                "E1": 0}
            }

        self.qr_codes = {
            "FET": "--",
            "HM": "--",
            "REF": "--"
            }

        self.evento = ""
        #ciclos anteriores, ya no existen en el driver

        #self.torque_cycles = {
        #    "PDC-P": {
        #        "E1": ["tool1",3,"6mm Nut"]},
        #    "PDC-D": {
        #        "E1": ["tool1",2,"6mm Nut"]},
        #    "BATTERY": {
        #        "BT": ["tool1",6,"Battery Nut"]},
        #    "BATTERY-2": {
        #        "BT": ["tool1",11,"Battery Nut"]},
        #    "MFB-P1": {
        #        "A47": ["tool2",4,"8mm Nut"],
        #        "A46": ["tool2",4,"8mm Nut"],
        #        "A45": ["tool1",4,"6mm Nut"],
        #        "A44": ["tool1",4,"6mm Nut"],
        #        "A43": ["tool1",4,"6mm Nut"],
        #        "A41": ["tool2",4,"8mm Nut"], 
        #        "A42": ["tool1",4,"6mm Nut"]},
        #    "MFB-S": {
        #        "A51": ["tool2",5,"8mm Nut"],
        #        "A52": ["tool2",5,"8mm Nut"],
        #        "A53": ["tool3",4,"6mm Nut"],
        #        "A54": ["tool3",4,"6mm Nut"],
        #        "A55": ["tool3",4,"6mm Nut"],
        #        "A56": ["tool3",4,"6mm Nut"]},
        #    "MFB-E": {
        #        "E1": ["tool2",7,"8mm Nut"],
        #        "A1": ["tool2",7,"8mm Nut"],
        #        "A2": ["tool2",7,"8mm Nut"]},
        #    "MFB-P2": {
        #        "A20": ["tool2",2,"8mm Nut"],
        #        "A21": ["tool3",6,"6mm Nut"],
        #        "A22": ["tool3",6,"6mm Nut"],
        #        "A23": ["tool3",6,"6mm Nut"],
        #        "A24": ["tool3",6,"6mm Nut"],
        #        "A25": ["tool2",2,"8mm Nut"], 
        #        "A26": ["tool3",6,"6mm Nut"], 
        #        "A27": ["tool3",6,"6mm Nut"], 
        #        "A28": ["tool3",6,"6mm Nut"], 
        #        "A29": ["tool3",6,"6mm Nut"], 
        #        "A30": ["tool2",2,"8mm Nut"]},
        #    "PDC-R": {
        #        "E1": ["tool2",3,"8mm Nut"]},
        #    "PDC-RS": {
        #        "E1": ["tool2",3,"8mm Nut"]},
        #    "PDC-RMID": {
        #        "E1": ["tool2",3,"8mm Nut"]}
        #    }

        self.torque_cycles = {
            "PDC-P": {
                "E1": ["tool1",2,"6mm Nut"]},
            "PDC-D": {
                "E1": ["tool1",2,"6mm Nut"]},
            "BATTERY": {
                "BT": ["tool1",9,"Battery Nut"]},
            "BATTERY-2": {
                "BT": ["tool1",9,"Battery Nut"]},
            "MFB-P1": {
                "A47": ["tool2",10,"8mm Nut"],
                "A46": ["tool2",5,"8mm Nut"],
                "A45": ["tool1",3,"6mm Nut"],
                "A44": ["tool1",4,"6mm Nut"],
                "A43": ["tool1",6,"6mm Nut"],
                "A41": ["tool2",4,"8mm Nut"], 
                "A42": ["tool1",5,"6mm Nut"]},
            "MFB-S": {
                "A51": ["tool2",9,"8mm Nut"],
                "A52": ["tool2",2,"8mm Nut"],
                "A53": ["tool3",2,"6mm Nut"],
                "A54": ["tool3",11,"6mm Nut"],
                "A55": ["tool3",12,"6mm Nut"],
                "A56": ["tool3",3,"6mm Nut"]},
            "MFB-E": {
                "E1": ["tool2",13,"8mm Nut"],
                "A1": ["tool2",14,"8mm Nut"],
                "A2": ["tool2",15,"8mm Nut"]},
            "MFB-P2": {
                "A20": ["tool2",7,"8mm Nut"],
                "A21": ["tool3",8,"6mm Nut"],
                "A22": ["tool3",5,"6mm Nut"],
                "A23": ["tool3",4,"6mm Nut"],
                "A24": ["tool3",7,"6mm Nut"],
                "A25": ["tool2",3,"8mm Nut"], 
                "A26": ["tool3",6,"6mm Nut"], 
                "A27": ["tool3",10,"6mm Nut"], 
                "A28": ["tool3",10,"6mm Nut"], 
                "A29": ["tool3",9,"6mm Nut"], 
                "A30": ["tool2",8,"8mm Nut"]},
            "PDC-R": {
                "E1": ["tool2",11,"8mm Nut"]},
            "PDC-RS": {
                "E1": ["tool2",6,"8mm Nut"]},
            "PDC-RMID": {
                "E1": ["tool2",6,"8mm Nut"]}
            }

        self.sub_topics = {
                        "keyboard": "Keyboard/status",
                        "plc": "PLC/1/status",
                        #"torque_1": "torque/1/status",
                        #"torque_2": "torque/2/status",
                        #"torque_3": "torque/3/status",
                        "torque_1": "TorqueModbus/2/status",
                        "torque_2": "TorqueModbus/3/status",
                        "torque_3": "TorqueModbus/4/status",
                        "gui": "gui/status",
                        "gui_2": "gui_2/status",
                        "config": "config/status"
                        }

        self.pub_topics = {
                        "gui": "gui/set",
                        "gui_2": "gui_2/set",
                        "plc": "PLC/1",
                        "torque": {
                                   #"tool1": "torque/1/set",
                                   #"tool2": "torque/2/set",
                                   #"tool3": "torque/3/set"
                                   "tool1": "TorqueModbus/2",
                                   "tool2": "TorqueModbus/3",
                                   "tool3": "TorqueModbus/4"
                                   },
                        "printer": "printer/set",
                        "config": "config/set"
                        }

        self.config_data = {
            "encoder_feedback": {
                "tool1": True,
                "tool2": True,
                "tool3": True
            },
            "retry_btn_mode": {
                "tool1": False,
                "tool2": False,
                "tool3": False  
            },
            "constraints": {
                "tools": [["tool1", "tool3"]]
            },
            "untwist": False,
            "flexible_mode": False
        }

        self.local_data = {
                            "user": {"type":"", "pass":"", "name":""},
                            "lbl_info1_text": "",
                            "lbl_info1.2_text": "",
                            "lbl_info2_text": "",
                            "lbl_info3_text": "",
                            "lbl_info4_text": "",
                            "qr_rework" : False,
                            "nuts_scrap":{}
                            }

        self.input_data = {
            "database":{
                "modularity": {},
                "pedido": {},
                "qr_retrabajo": {}
                },
            "plc": {
                "emergency": True,
                "encoder_1": {"zone": "0"},# el valor de "zone" debe ser de la forma: '{"caja": "torque_name"}'
                "encoder_2": {"zone": "0"},
                "encoder_3": {"zone": "0"},
                "retry_btn": False,
                "clamps": ["PDC-P", "PDC-D", "BATTERY", "MFB-P1", "MFB-S", "MFB-P2", "PDC-R"]}, # Debe inicializarce vacío
            "torque":{
                "tool1": {},
                "tool2": {},
                "tool3": {}},
            "gui": {
                "request": "", 
                "ID": "", 
                "code": "", 
                "visible":{}}
            }

        self.torque_data = {
            "tool1" : {
                "stop_profile": 0,
                "backward_profile": 1, 
                "current_trq": None,   #["PDC-P", "E1", 3, "tuerca_x"]
                "queue": [], #[["PDC-P", "E1", 3, "tuerca_x"]]
                "rqst": False,
                "gui": self.pub_topics["gui_2"],
                "past_trq": None,
                "img": None,
                "error": False,
                "enable" : False,
                },
            "tool2" : {
                "stop_profile": 0,
                "backward_profile": 1, 
                "current_trq": None,
                "queue": [], #[["PDC-P", "E1", 3, "tuerca_x"]]
                "rqst": False,
                "gui": self.pub_topics["gui"],
                "past_trq": None,
                "img": None,
                "error": False,
                "enable" : False
                },
            "tool3" : {
                "stop_profile": 0,
                "backward_profile": 1, 
                "current_trq": None,
                "queue": [], #[["PDC-P", "E1", 3, "tuerca_x"]]
                "rqst": False,
                "gui": self.pub_topics["gui"],
                "past_trq": None,
                "img": None,
                "error": False,
                "enable" : False
                }
            }

    def reset (self):
        self.datetime = None
        for i in self.result:
            for j in self.result[i]:
                self.result[i][j] = None
        for i in self.tries:
            for j in self.tries[i]:
                self.tries[i][j] = 0
        for i in self.resultAngle:
            for j in self.resultAngle[i]:
                self.resultAngle[i][j] = None

        for i in list(self.BB):
            temp = self.imgs_path +"boxes/" + i + ".jpg"
            self.imgs[i] = imread(temp)
        
        self.qr_codes.clear()
        self.qr_codes["FET"]    = "--"
        self.qr_codes["HM"]     = "--"
        self.qr_codes["REF"]    = "--"

        self.local_data["lbl_info1_text"]   = ""
        self.local_data["lbl_info1.2_text"] = ""
        self.local_data["lbl_info2_text"]   = ""
        self.local_data["lbl_info3_text"]   = ""
        self.local_data["lbl_info4_text"]   = ""
        self.local_data["qr_rework"]        = False
        self.local_data["nuts_scrap"].clear()

        self.input_data["database"]["modularity"].clear()
        self.input_data["database"]["pedido"].clear()
        self.input_data["database"]["qr_retrabajo"].clear()
        self.input_data["plc"]["emergency"]         = True
        self.input_data["plc"]["encoder_1"]["zone"] = "0"
        self.input_data["plc"]["encoder_2"]["zone"] = "0"
        self.input_data["plc"]["encoder_3"]["zone"] = "0"
        self.input_data["plc"]["retry_btn"]         = False
        self.input_data["gui"]["request"]           = ""
        self.input_data["gui"]["ID"]                = ""
        self.input_data["gui"]["code"]              = ""
        self.input_data["plc"]["clamps"].clear()
        self.input_data["gui"]["visible"].clear()
        for i in self.input_data["torque"]: self.input_data["torque"][i].clear()
        
        for i in self.torque_data:
            self.torque_data[i]["current_trq"]  = None
            self.torque_data[i]["rqst"]         = False
            self.torque_data[i]["past_trq"]     = None
            self.torque_data[i]["img"]          = None
            self.torque_data[i]["error"]        = False
            self.torque_data[i]["enable"]       = False
            self.torque_data[i]["queue"].clear()

    def drawBB (self, img = None, BB = ["PDC-P", "E1"], color = (255,255,255)):
        #red     = (255, 0, 0)
        #orange  = (31, 186, 226)
        #green   = (0, 255, 0)
        #White   = (255, 255, 255)
        try:
            #print("BB-----------------------------",BB)
            #print("self.BB-----------------------------",self.BB)
            if type(BB[0]) == list:
                for i in BB:
                    pts = self.BB[i[0]][i[1]]
                    if "PDC-R" in pts[0]:
                        tickness = 1
                    else:
                        tickness = 3
                    rectangle(img, pts[0], pts[1], color, tickness)
            else:
                pts = self.BB[BB[0]][BB[1]]
                if "PDC-R" in pts[0]:
                    tickness = 1
                else:
                    tickness = 3
                rectangle(img, pts[0], pts[1], color, tickness)
        except Exception as ex:
            print("Model.drawBB exception: ", ex)
        return img

    def log(self, state):
        try:
            data = {
                "PEDIDO":self.qr_codes["HM"],
                "ESTADO": state,
                "DATETIME": strftime("%Y/%m/%d %H:%M:%S"),
                }
            endpoint = "http://{}/api/post/log".format(self.server)
            resp = requests.post(endpoint, data=json.dumps(data))
        except Exception as ex:
            print("Log request Exception: ", ex)
