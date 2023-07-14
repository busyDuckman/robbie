#include "Display.h"
#include <unistd.h>
#include <pigpio.h>
#include <iostream>


Display::Display(std::shared_ptr<Interface> spi_interface,
                 unsigned width, unsigned height,
                 unsigned rst_port,
                 unsigned bl_port,
                 unsigned bl_freq) :
                 interface_(spi_interface), rst_port_(rst_port), bl_port_(bl_port), bl_freq_(bl_freq)
{
    width_ = width;
    height_ = height;
    composer_ = std::make_shared<Composer>(width_, height_);
    first_loop_ = true;

    // enough memory for any screen blit in most pixel color depths.
    blit_buffer_ = new uint8_t[width*height*4];
}

Display::~Display() {
    close();
    delete[] blit_buffer_;
}

bool Display::open() {
    std::cout << "  - gpio init." << std::endl;
    int ver = gpioInitialise();
    if (ver == PI_INIT_FAILED) {
        std::cout << "  - error: gpio init failed." << std::endl;
        return false;
    }
    std::cout << "  - using pigpio ver " << ver << std::endl;

    if (!interface_->is_open()) {
        std::cout << "  - opening spi port." << std::endl;
        interface_->open();
        std::cout << "  - spi_handle: " << interface_->get_handle()
                  << std::endl;
    }

    if (rst_port_ != NOT_A_PORT) {
        std::cout << "  - init reset port." << std::endl;
        gpioSetMode(rst_port_, PI_OUTPUT);
    }
    if (bl_port_ != NOT_A_PORT) {
        std::cout << "  - init backlight port." << std::endl;
        gpioSetMode(bl_port_, PI_OUTPUT);
        gpioWrite(bl_port_, PI_HIGH);
    }

    return true;
}

bool Display::is_open() {
    return interface_->is_open();
}

void Display::close() {
    if (is_open()) {
        std::cout << "Display shutdown:" << std::endl;
        interface_->close();
        if (rst_port_ != NOT_A_PORT) {
            std::cout << "  - finalising reset port" << std::endl;
            gpioWrite(rst_port_, PI_HIGH);
        }
        if (bl_port_ != NOT_A_PORT) {
            std::cout << "  - finalising backlight port" << std::endl;
            gpioWrite(bl_port_, PI_LOW);
        }
    }

}



//void SpiDisplay::digital_write(unsigned pin, unsigned level) {
//    gpioWrite(pin, level);
//}
//
//unsigned SpiDisplay::digital_read(unsigned pin) {
//    return gpioRead(pin);
//}

void Display::delay_ms(unsigned delay_time) {
    usleep(delay_time * 1000);
}


void Display::bl_frequency(unsigned freq) {
    bl_freq_ = freq;
}

void Display::blit_window(cv::Mat img, std::array<int, 4> box) {
    int x = std::max(0, box[0]);
    int y = std::max(0, box[1]);
    int x2 = std::min(width_, static_cast<unsigned>(box[2]));
    int y2 = std::min(height_, static_cast<unsigned>(box[3]));

    int blit_len = 0;
    for (int j = y; j <y2; j++) {
        for (int i = x; i <x2; i++) {
            cv::Vec3b &pixel = img.at<cv::Vec3b>(j, i);
            uint8_t msb = (pixel[0] & 0xF8) | (pixel[1] >> 5);
            uint8_t lsb = ((pixel[1] << 3) & 0xE0) | (pixel[2] >> 3);
            blit_buffer_[blit_len++] = msb;
            blit_buffer_[blit_len++] = lsb;
        }
    }

    set_window(x, y, x2, y2);
    interface_->data_chunked((char *)blit_buffer_, blit_len, 65536, 0);
}



