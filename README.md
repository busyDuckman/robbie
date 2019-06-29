# Robbie
Upgrade and reboot of a vintage Robie robot

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
__BM-01__ 2.2 inch 2.2" SPI TFT LCD Display module 240x320 [ILI9341](https://www.aliexpress.com/item/32666423452.html) 
  - Spec sheet, [Footprint](doco/spec_sheets/ILI9341.webp?raw=true) (NB: The 2nd decimal place of accuracy does not tally with my measurements.)
  - Spec sheet, [controller](doco/spec_sheets/ILI9341.pdf?raw=true)
  - Spec sheet, [break out board](doco/spec_sheets/2.2inch_SPI_Module_MSP2202_User_Manual_EN.pdf?raw=true)
  - Spec sheet, [LCD](doco/spec_sheets/QDTFT2001_specification_v1.1.pdf?raw=true)
  
__BM-02__ Generic Page magnifier using Fresnel lens (2-dollar shop) or [link](https://www.amazon.com/Premium-Page-Magnifier-Fresnel-Reading/dp/B015NR7XGS)
  
__BM-03__ Raspberry Pi 3, Model B+
  - Or similar...  
  
__BM-04__ 28byj-48 stepper motor with ULN2003 Darlington Transistor Array breakout board. [link](https://www.jaycar.com.au/arduino-compatible-5v-stepper-motor-with-controller/p/XC4458)
  - Spec sheet, [UL?200? series](doco/spec_sheets/uln2003a.pdf?raw=true) NB: Simplified Block Diagram is not the 2003, which has 2k7 resistors on base for TTL operation.
  - Spec Sheet, [28byj-48 dimensions](doco/spec_sheets/28BYJ-48-dimensions.png?raw=true)
  - Spec sheet, [28byj-48 electrical](doco/spec_sheets/28BYJ-48.pdf?raw=true)
  
__BM-05__ 1970's Robie Robot
  - aka "Tandy Robie", "Radio Shack Robie", "Robie the Robot", "Talking Robie", "RS 4061", "Robocom 1000", "Robie Parlant", "Robocom Robot (Super)" 
  - info at [theoldrobots.com](http://www.theoldrobots.com/talkrobie2.html)
  - find on e-bay, gumtree, vintage store. 
