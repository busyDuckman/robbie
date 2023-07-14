#ifndef SPIDISPLAY_H
#define SPIDISPLAY_H

#include <cstdint>
#include <span>
#include <memory>
#include "Interface.h"
#include "../graphics/composer.h"
#include <opencv2/opencv.hpp>
#include <opencv2/core.hpp>

#define NOT_A_PORT 0xffff

/**
 * Base class for SPI display interface.
 *
 * PI-3 spi GPIO ports are as per:
 *                     MISO  MOSI  SCLK  CE0  CE1  CE2
 *      Main SPI (0)   9     10    11    8    7    -
 *      Aux SPI  (1)   19    20    21    18   17   16
 *
 * Throughout this code I use the term _port to be mindful that
 * it's a gpio port, not a physical pin number.
 */
class Display {
public:
//    The left eye, on SPI-0, is wired as per:
//    - DIN:   ->  Pin 19, GPIO 10    SPI_0 MOSI (Master Out Slave In)
//    - CLK:   ->  Pin 23, GPIO 11    SPI_0 clock line
//    -  CS:   ->  Pin 24, GPIO 8     SPI_0 CE0 (Chip Enable)
//
//    -  BL:   ->  Pin 32, GPIO 12    Backlight control with PWM0
    /**
     * Sets up a new display, but dose not set ports or connect.
     *
     *  Use open() and close() to connect / disconnect.
     *  The destructor will call close if you have not.
     *
     * @param rst_port        RST:   ->  Pin 13, GPIO 27    Reset line for the display
     * @param dc_port          DS:   ->  Pin 22, GPIO 25    Data or Command selection
     * @param bl_port          BL:   ->  Pin 12, GPIO 18    Backlight control with PWM0
     * @param bl_freq         TODO
     * @param spi_channel     The spi channel to use (0 or 1)
     * @param spi_device      The spi_device, 0=CE0 etc.
     * @param spi_freq        spi freq
     */
    Display(std::shared_ptr<Interface> interface,
            unsigned width, unsigned height,
            unsigned rst_port = 27,
            unsigned bl_port  = 18,
            unsigned bl_freq  = 1000);


    ~Display();
    void delay_ms(unsigned delay_time);
    void bl_frequency(unsigned freq);

    virtual bool open();
    virtual bool is_open();
    virtual void close();
    virtual void reset()=0;

    virtual void set_window(u_int x1, u_int y1, u_int x2, u_int y2) = 0;

    void set_full_screen() {
        set_window(0, 0, width_, height_);
    }

    void blit_window(cv::Mat img, std::array<int, 4> box);

    std::shared_ptr<Composer> composer() const {
        return composer_;
    }

    void blit_next_frame() {
//        auto buffer = composer_->draw_buffer();
        //TODO: render buffer
        blit_window(composer_->draw_buffer(), {0, 0, (int)width_, (int)height_});
    }

protected:
    unsigned rst_port_, dc_port_, bl_port_,
             bl_freq_, spi_device_;

    std::shared_ptr<Interface> interface_;
    std::shared_ptr<Composer> composer_;
    unsigned width_, height_;
    bool first_loop_;

    uint8_t *blit_buffer_;
};

#endif // SPIDISPLAY_H
