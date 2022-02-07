import re

img = re.search('[^0]*0+(\d+)$',"7840700").group(1)
print(img)
