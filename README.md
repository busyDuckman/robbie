# Robbie
Upgrade and reboot of a vintage Tandy robot

## Overview

## Building the head
The head can be upgraded to rotate via a stepper motor (BOM-04).
I created a mechanical assembly in OpenSCAD to do this and hold a matrix voice module.

__Design__  
![Upper view](doco/pics/head_gears_upper.png?raw=true "Upper view")
![Lower view](doco/pics/head_gears_lower.png?raw=true "Lower view")

__CAD Files__    

    CAD/head_rotary_assembly
Contains .scad and 3D printable .stl files/

__Assembly__  
![Printed parts](doco/pics/P6185662.JPG?raw=true "Printed parts")
The ring gear fits on the inside of the robots head. The notch on the outside of the ring gear aligns with a key in the robots plastic.  

![Printed parts](doco/pics/P6185667_close_up.jpg?raw=true "Printed parts")
The brace aligns with the rim under the robots head.  

![Printed parts](doco/pics/P6185672.JPG?raw=true "Printed parts")
Not the gear only fits one way round.

__Result__  
Video of the motion of the head in action.  

[![IMAGE ALT TEXT HERE](https://img.youtube.com/vi/sQd-v5fpN5s/0.jpg)](https://youtu.be/sQd-v5fpN5s)



## Front assembly
The front assembly contains a raspberry pi 3 b+ (BOM-03), a pi-cam and 2.2" TFT Display (BOM-01), 
facing through the robots front port.


_Assembly__
Build Notes:
  - This is deliberately a tight fit, rou may need to adjust some bits.

__Design__  
![Upper view](doco/pics/front_asm_render.jpg?raw=true "Upper view")

__CAD Files__    

    CAD/front_assembly
Contains 3D printable .stl files/
  
  

# Bill of materials
NB: item 1 = BM-01 

01) __BM-01__ 2.2 inch 2.2" SPI TFT LCD Display module 240x320 [ILI9341](https://www.aliexpress.com/item/32666423452.html) 
02) __BM-02__ Generic Page magnifier using Fresnel lens (2-dollar shop) or [link](https://www.amazon.com/Premium-Page-Magnifier-Fresnel-Reading/dp/B015NR7XGS)
03) __BM-03__ Raspberry Pi 3, Model B+
04) __BM-04__ 28byj-48 stepper motor with ULN2003 Driver Board [link](https://www.jaycar.com.au/arduino-compatible-5v-stepper-motor-with-controller/p/XC4458)
 