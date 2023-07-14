#include "Interface.h"
#include <pigpio.h>
#include <iostream>
#include <unistd.h>

SPIInterface::SPIInterface(unsigned int spi_channel, unsigned int spi_device, unsigned int dc_port,
                           unsigned int spi_freq) :
        spi_channel_(spi_channel),
        spi_device_(spi_device),
        spi_freq_(spi_freq),
        dc_port_(dc_port)
{
    spi_handle_ = -1;
}

void SPIInterface::command(uint8_t cmd) {
//    if (in_data_mode_ && (dc_port_ != NOT_A_PORT)) {
//        gpioWrite(dc_port_, PI_HIGH);
//        in_data_mode_ = false;
//    }
    gpioWrite(dc_port_, PI_LOW);
    char tempCmd = static_cast<char>(cmd);
    spiWrite(spi_handle_, &tempCmd, 1);
}

//void SPIInterface::data(const std::span<const uint8_t> &data) {
//    if (!in_data_mode_ && (dc_port_ != NOT_A_PORT)) {
//        gpioWrite(dc_port_, PI_LOW);
//        in_data_mode_ = true;
//    }
////    spiWrite(spi_handle_, (char *) data, len);
//    spiWrite(spi_handle_, const_cast<char*>(reinterpret_cast<const char*>(data.data())), data.size());
//}

void SPIInterface::data(const char *data, unsigned len) {
//    if (!in_data_mode_ && (dc_port_ != NOT_A_PORT)) {
//        gpioWrite(dc_port_, PI_LOW);
//        in_data_mode_ = true;
//    }
    gpioWrite(dc_port_, PI_HIGH);
    spiWrite(spi_handle_, (char *) data, len);
}

void SPIInterface::data(uint8_t data) {
//    if (!in_data_mode_ && (dc_port_ != NOT_A_PORT)) {
//        gpioWrite(dc_port_, PI_LOW);
//        in_data_mode_ = true;
//    }
    gpioWrite(dc_port_, PI_HIGH);
    spiWrite(spi_handle_, (char *) &data, 1);
}

bool SPIInterface::open() {
    std::cout << "  - SPI init: spi_" << spi_channel_
              << " ce_" << spi_device_ << std::endl;
    if (!is_open()) {
        gpioInitialise();
        if (dc_port_ != NOT_A_PORT) {
            gpioSetMode(dc_port_, PI_OUTPUT);
            gpioWrite(dc_port_, PI_LOW);
            in_data_mode_ = true;
        }
//        gpioHardwarePWM(bl_port_, bl_freq_, 500000); //50% duty cycle
        int flags = 0;
        switch (spi_channel_) {
            case 0: break;
            case 1:
                // flag using the aux spi
                flags |= 0b100000000;
                break;
            default:
                std::cout << "  - unknown/unsupported spi channel " << spi_channel_ << std::endl;
                return false;
        }
        spi_handle_ = spiOpen(spi_device_, spi_freq_, flags);
        if (spi_handle_ < 0) {
            std::cout << "  - spiOpen returned error code " << spi_handle_ << std::endl;
            return false;
        }
    }
    else {
        std::cout << "  - display already initialised" << std::endl;
    }
    return true;
}

bool SPIInterface::is_open() {
    return spi_handle_ >= 0;
}

void SPIInterface::close() {
    if (is_open()) {
        std::cout << "  - closing spi handle: " << spi_handle_ << std::endl;
        spiClose(spi_handle_);
        spi_handle_ = -1;

        if (dc_port_ != NOT_A_PORT) {
            std::cout << "  - finalising data/command (dc) port" << spi_handle_ << std::endl;
            gpioWrite(dc_port_, PI_LOW);
        }
    }
}


void Interface::data_chunked(const char *data, unsigned int len, unsigned int chunk_size, unsigned int delay) {
    for (unsigned i = 0; i < len; i += chunk_size) {
        unsigned end = std::min(len, i + chunk_size);
        unsigned this_chunk_len = end - i;

        // Send the chunk
        this->data(data+i, this_chunk_len);

        // Wait if there's more data to send
        if ((end < len) && (delay > 0))
            usleep(delay);
    }

}
