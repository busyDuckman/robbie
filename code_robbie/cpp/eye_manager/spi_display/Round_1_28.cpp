// Round_1_28.cpp
#include "Round_1_28.h"
#include <pigpio.h>

Round_1_28::Round_1_28(std::shared_ptr<Interface> interface,
                       unsigned rst_port,
                       unsigned bl_port,
                       unsigned bl_freq)
        : Display(interface, 240, 240, rst_port, bl_port, bl_freq)
{
}


bool Round_1_28::open() {
    if (!Display::open()) {
        return false;
    }
    
    this->reset();

    interface_->command(0xEF);
    interface_->cmd_with_data(0xEB, {0x14});
    interface_->command(0xFE);
    interface_->command(0xEF);
    interface_->cmd_with_data(0xEB, {0x14});
    interface_->cmd_with_data(0x84, {0x40});
    interface_->cmd_with_data(0x85, {0xFF});
    interface_->cmd_with_data(0x86, {0xFF});
    interface_->cmd_with_data(0x87, {0xFF});
    interface_->cmd_with_data(0x88, {0x0A});
    interface_->cmd_with_data(0x89, {0x21});
    interface_->cmd_with_data(0x8A, {0x00});
    interface_->cmd_with_data(0x8B, {0x80});
    interface_->cmd_with_data(0x8C, {0x01});
    interface_->cmd_with_data(0x8D, {0x01});
    interface_->cmd_with_data(0x8E, {0xFF});
    interface_->cmd_with_data(0x8F, {0xFF});
    interface_->cmd_with_data(0xB6, {0x00, 0x20});
    interface_->cmd_with_data(0x36, {0x08});
    interface_->cmd_with_data(0x3A, {0x05});
    interface_->cmd_with_data(0x90, {0x08, 0x08, 0x08, 0x08});

    interface_->cmd_with_data(0xBD, {0x06});
    interface_->cmd_with_data(0xBC, {0x00});
    interface_->cmd_with_data(0xFF, {0x60, 0x01, 0x04});
    interface_->cmd_with_data(0xC3, {0x13});
    interface_->cmd_with_data(0xC4, {0x13});
    interface_->cmd_with_data(0xC9, {0x22});
    interface_->cmd_with_data(0xBE, {0x11});
    interface_->cmd_with_data(0xE1, {0x10, 0x0E});
    interface_->cmd_with_data(0xDF, {0x21, 0x0c, 0x02});
    interface_->cmd_with_data(0xF0, {0x45, 0x09, 0x08, 0x08, 0x26, 0x2A});
    interface_->cmd_with_data(0xF1, {0x43, 0x70, 0x72, 0x36, 0x37, 0x6F});
    interface_->cmd_with_data(0xF2, {0x45, 0x09, 0x08, 0x08, 0x26, 0x2A});
    interface_->cmd_with_data(0xF3, {0x43, 0x70, 0x72, 0x36, 0x37, 0x6F});
    interface_->cmd_with_data(0xED, {0x1B, 0x0B});
    interface_->cmd_with_data(0xAE, {0x77});
    interface_->cmd_with_data(0xCD, {0x63});

    interface_->cmd_with_data(0x70, {0x07, 0x07, 0x04, 0x0E, 0x0F, 0x09, 0x07, 0x08, 0x03});
    interface_->cmd_with_data(0xE8, {0x34});
    interface_->cmd_with_data(0x62, {0x18, 0x0D, 0x71, 0xED, 0x70, 0x70, 0x18, 0x0F, 0x71, 0xEF, 0x70, 0x70});
    interface_->cmd_with_data(0x63, {0x18, 0x11, 0x71, 0xF1, 0x70, 0x70, 0x18, 0x13, 0x71, 0xF3, 0x70, 0x70});
    interface_->cmd_with_data(0x64, {0x28, 0x29, 0xF1, 0x01, 0xF1, 0x00, 0x07});
    interface_->cmd_with_data(0x66, {0x3C, 0x00, 0xCD, 0x67, 0x45, 0x45, 0x10, 0x00, 0x00, 0x00});
    interface_->cmd_with_data(0x67, {0x00, 0x3C, 0x00, 0x00, 0x00, 0x01, 0x54, 0x10, 0x32, 0x98});
    interface_->cmd_with_data(0x74, {0x10, 0x85, 0x80, 0x00, 0x00, 0x4E, 0x00});
    interface_->cmd_with_data(0x98, {0x3e, 0x07});
    interface_->command(0x35);
    interface_->command(0x21);
    interface_->command(0x11);
    usleep(120000);  // 120ms
    interface_->command(0x29);
    usleep(20000);  //20ms

    return true;
}

void Round_1_28::close() {
    Display::close();
}

void Round_1_28::reset() {
    gpioWrite(rst_port_, PI_HIGH);
    usleep(10000); // Sleep for 10ms
    gpioWrite(rst_port_, PI_LOW);
    usleep(10000);
    gpioWrite(rst_port_, PI_HIGH);
    usleep(10000);
}

void Round_1_28::set_window(u_int x1, u_int y1, u_int x2, u_int y2) {
    interface_->command(0x2A);     // set x bounds
    interface_->data(0x00);        // high octet
    interface_->data(x1);          // low octet
    interface_->data(0x00);        // high octet
    interface_->data(x2 - 1);      // low octet
    
    interface_->command(0x2B);     // set y bounds
    interface_->data(0x00);
    interface_->data(y1);
    interface_->data(0x00);
    interface_->data(y2 - 1);

    interface_->command(0x2C);     // done
}
