from pickle import load, dump
from cv2 import imread, imshow, waitKey, destroyAllWindows, rectangle
from threading import Timer
from time import sleep

#with open("BB_0", "rb") as f:
#            BB= load(f)

#BB["PDC-RMID"] = BB["PDC-R"]
#BB["BATTERY"] = BB["BATERRY"]
#BB["BATTERY-2"] = BB["BATERRY"]
#BB.pop("BATERRY")

#for i in BB:
#    for j in BB[i]:
#        for k in range(len(BB[i][j])):
#            BB[i][j][k] = tuple(BB[i][j][k])

#with open("BB", "wb") as f:
#    dump(BB, f, protocol=3)


with open("BB", "rb") as f:
    BB= load(f)

for i in BB:
    print("\n", i, BB[i])
imgs = {}
path = "../imgs/boxes/"
for i in list(BB):
    temp = path + i + ".jpg"
    img = imread(temp)
    for j in BB[i]:
        rectangle(img, BB[i][j][0], BB[i][j][1], (31,186,226), 3)
    imshow(i, img)
    k = waitKey(0)   
destroyAllWindows()