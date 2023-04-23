# Robbie
Project Code and instructions for a reboot of a vintage 1980's Robie robot

__Warning__: 
Robbie is not a kids toy. If coarse language / alcohol / adult themes offend you, please move on.

## Status
  - __Mechanical:__,
    - Done:
      - Head rotation.
      - Front panel assembly, holding pi / camera and screen.
    - In progress
      - arms
      - drive system.
  - __Software:__
    - Done:
       - Robbie is able to tell jokes (from an internal database); mostly using the correct vocal intonations.
       - Robbie is able to give random (often silly) life advice.
       - Robbie is able to generate dares.
    - In progress:
       - Random (but sensible) cocktail recipe generation.
       - Pervasive mood.
       - Internal dialogue.
       - Others as ideas hit.
  - __Electrical__:  
       - Done:
         - 2.2" front display is working.
       - In progress:
         - Internal speaker is being re-investigated after some issues.
         - I have not yet ordered a "matrix voice unit" to fit that, and make robbie more interactive. 

__Shout outs__:
  - Brett Downing for hacking on the drive systems and display; as well as floating some awesome ideas.
  - ANU Maker-space for letting me use their 3D printers.

## Rational
I am unhappy with the "little helpers" of this world (Google, Siri, Elexa). 
They don't feel like the robotic helpers we envisioned in the sci-fi of the 1960's-90's.
They are too:
  - subservient
  - "product like"
  - politically correct
  - tied to services and apps
  - corporate
  
I want to create something more:
  - Emotive 
  - Self actuated
  - Fun to be around
  - Character driven
  - Independent
  
## Overview

The project is created buy opening up an old 'Robie Robot' and gutting it of all the old electronics, motors and lights.  

Then their are four major sections that need to be constructed:
1) Head
2) Front assembly
3) Rear assembly
4) Drive system and battery.

A Bill Of Materials (BOM) is provided and most ot the required mechanical components are 3D printable with relevant cad 
and .stl files provided.

After constructing and fitting the different sections, install the software to the pi and close up the unit. 

## Instructions, building the head
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



## Instructions, Front assembly
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
  
  

