include <gears.scad>;

//NB: I think of gears vertically, so width means height in this case.

// gear options
pressure_angle=20;
helix_angle=20;  // keeping small to avoid 3d printing overhang issues.
gear_module = 1.5;
gear_width = 4; // ie: height
drive_bore = 5; // hole for motors shaft
// gear size
drive_gear_teeth = 8;
ring_teeth = 60; // nb: effects size of ring

// gear layout
operating_distance = pitch_diameter(ring_teeth)/2 - pitch_diameter(drive_gear_teeth)/2;
echo(operating_distance);

// height of the lip above the drive gear
support_width=1.5;
guide_radius = 2;

brace_height = 7; 
under_brace = 1.5; 

// fit
outer_diameter = 106;
alignment_ring_size = 1; // total channel size (square)

// layout
assemble = true;
// place circuit to front of robot
circuit_pos = [0,-3.5,-5];
motor_pos = [0, operating_distance-8, -30]; // -8 to align shaft

specific_part = 0;



// gear calculation steps
function pitch_diameter(teeth) = gear_module * teeth;
function tip_clearance(teeth) = (teeth <3)? 0 : gear_module/6;
function root_diameter(teeth) =
    pitch_diameter(teeth) -
    (2*(gear_module + tip_clearance(teeth)));
function total_diameter(teeth) = 
    pitch_diameter(teeth) + 
    (pitch_diameter(teeth) - root_diameter(teeth));
    
// creates a tube of length h, centered in x/y, but not z.
module tube(h, inner_d, outer_d)
{
    translate([0,0,h/2])
        difference()
        {
            // outer cylinder
            cylinder(h=h, d=outer_d, center=true);
            if (inner_d > 0) 
                translate([0,0,-1])
                    // inner cylinder
                    cylinder(h=h+4, d=inner_d, center=true);
        }    
}

// render a Martix voice circuit board stand in
module circuit(for_cutting = false)
{
    // using http://www.farnell.com/datasheets/2608206.pdf?_ga=2.219371345.993533472.1539793131-901402398.1539269224
    circuit_diameter = 79.8;
    led_size = 5;
    num_leds = 18;
    if (for_cutting == false)
    {
        difference()
        {
            color("green")
            tube(1.6, 2, circuit_diameter);
            if (for_cutting == false)
                circuit_bolts();
        }
    
        for(i=[0:num_leds])
            rotate([0,0,i*(360/num_leds)+90])
            translate([-led_size/2, -led_size/2, 0.01])
                translate([30.6, 0, 0])
                cube([led_size, led_size, 4]);
    }
    else
    {
        tube(20, 2, circuit_diameter);
    }
}

module circuit_bolts(d=3)
{
    translate([27, 23.5, -50])
        tube(100, 0, d);
    translate([27, -25.5, -50])
        tube(100, 0, d);
}


module motor()
{
    color("grey")
    tube(19, 0, 28);
    
    translate([0,8,19]) {
        color("yellow"){
            tube(10, 0, 3); //shaft
            tube(5, 0, 5); // sharft wider
        }
        color("grey")
            tube(1.5, 0, 7); // base
    }
    
    color("grey"){
        difference(){
            union(){
            translate([35/2,0,18])
                tube(1, 3.5, 7);
            translate([-35/2,0,18])
                tube(1, 3.5, 7);
            translate([-35/2,-3.5,18])
                cube([35,7,1]);
            }
            motor_bolts();
        }
    }
}

module motor_bolts(d=3.5)
{
   translate([35/2,0,-50])
        tube(100, 0, d);
    translate([-35/2,0,-50])
        tube(100, 0, d);
}

// creates a shaft key for a cylinder of d by h, centered in x/y, but not z.
// union or difference it as needed.
module key(d, h, key_size)
{
    //key_size = log(d);
    translate([0, d/2, h/2])
        cylinder(h=h, d=key_size, center=true);
}

// robot surrounds, placed beneth thehorizontal plane
module robot_rim(w=10, h=7.5, d=90)
{
    translate([0, 0, -h])
        tube(h, d, d+w);
}

//----------------------------------------------------------------------------------
// show other parts of robot
if (assemble) {
    translate(circuit_pos)
    rotate([0,0,90])
    circuit();

    // place motor
    translate(motor_pos)
        motor();

    // stand in for relevent portion of robot
    %robot_rim();
}

//----------------------------------------------------------------------------------
// brace (for motor and circuit
if((specific_part==0)||(specific_part==1))
{
color("orange")
translate([assemble?0:45,
         0,
         assemble?0.01:-circuit_pos[2]+brace_height])
rotate([0,0,assemble?0:-90])
difference(){
    
        difference(){
            translate([-50, 10, circuit_pos[2]-brace_height]){
                difference(){
                    // big chunk of material to cut away
                    cube([100, 50, brace_height+under_brace]);
                    
                    // slice off at an angle for speaker plug under circuit
                    translate([60, -20, -1.5])
                        rotate([0,0,25])
                            cube([100, 20, brace_height+3]);
                }
            }
            
            // inner diameter to allow acess to hole under circuit
            translate([0, 0, -20])
                tube(50,0,40);
            
            // recess for circuit board
            translate([0,0,-brace_height+3])
            translate(circuit_pos)
                rotate([0,0,90])
                    circuit(for_cutting=true);
        }
    
    // outer round edge
        //translate([-50, 10, -brace_height]){
            robot_rim(w=199,h=brace_height+3);
        robot_rim(w=199,h=20,d=100);
        //}
    
    translate([0, motor_pos[1], -35])
    {
        translate([0, 8, 0])
        tube(50, 0, 9.5); // shaft hole
        motor_bolts(d=2.5); //2.5mm hole, so I can tap for 3mm bolts
    }
    
    translate(circuit_pos)
    rotate([0,0,90])
        circuit_bolts(d=2.5); //2.5mm hole, so I can tap for 3mm bolts
}
}

//----------------------------------------------------------------------------------
// ring gear
if((specific_part==0)||(specific_part==2))
{
//color("red")
difference()
    {
    union() {
        //padding to the ring gear, to make it hit the outer diameter
        rim_size = (outer_diameter - total_diameter(ring_teeth)) /2;
        //align the guide ring
        radius_to_guide = total_diameter(ring_teeth)+guide_radius*2;

        difference()
        {
            // guide ring
            translate([0,0,-0.1]) //nudge to make sure mesh is well formed
            tube(gear_width+support_width+0.1, 
                 radius_to_guide, 
                 outer_diameter);
            
            // alignment ring
            inset = rim_size - alignment_ring_size;
            translate([0,0,gear_width+support_width-alignment_ring_size])
            tube(alignment_ring_size+0.1, 
                 radius_to_guide+inset, 
                 radius_to_guide+rim_size*2-inset);
        }
        
        herringbone_ring_gear (
            modul=gear_module, 
            tooth_number=ring_teeth, 
            width=gear_width, 
            rim_width=rim_size, 
            pressure_angle=pressure_angle, 
            helix_angle=helix_angle);
    }
    
    // noth in front of ring gear lines up with robot
    translate([0,0,-0.5])
        rotate([0,0,180])
            key(outer_diameter, gear_width+support_width+1, 8); 
}
}

module motor_shaft(h, drive_bore, cut_size)
{
    difference(){
        tube(h, 0, drive_bore);
    
        // two beams to lock around the motor keys
        sw = 5;
        translate([1.6, -drive_bore/2, -0.1])
            cube([sw, drive_bore, h+0.4]);
        translate([-(1.6+sw), -drive_bore/2 ,-0.1])
            cube([sw, drive_bore, h+0.4]);
    }
}
//translate([0,20,0])
//    motor_shaft(30, drive_bore, 3);

//----------------------------------------------------------------------------------
// drive gear
if( (specific_part==0) || (specific_part==3) )
{
color("blue")
translate([0,
            assemble?operating_distance:0,
            assemble?0:(gear_width+support_width)])
rotate([0,assemble?0:180,0])
difference(){
    union() {
        // shaft (through the gear)
        drive_tube_len = gear_width+support_width*6;
        translate([0,0,-support_width*5])
        {         
            
            tube(drive_tube_len, 0, drive_bore+1.5);
        }
        //root_diameter(drive_gear_teeth));
        
        // guide rings
        translate([0,0,gear_width])
            tube(support_width,
                0,
                total_diameter(drive_gear_teeth)+guide_radius*2);
        
        herringbone_gear (
            modul=gear_module, 
            tooth_number=8, 
            width=gear_width, 
            bore=0,
            pressure_angle=pressure_angle, 
            helix_angle=helix_angle);
    }
    translate([0,0,-gear_width*5])
        motor_shaft(gear_width*10,
                     drive_bore,
                     3);
}
}