#include <pigpio.h>
#include <iostream>
#include <memory>
#include "Round_1_28.h"
#include "graphics/composer.h"
#include <thread>
#include <chrono>

#define RIGHT_BL_PIN 12
#define LEFT_BL_PIN 13

#define CANVAS_ITY_IMPLEMENTATION
#include "graphics/canvas_ity.hpp"

void generate_sprites() {
    // generate sprite library.
//    canvas_ity::canvas context(32, 32);

}

int main() {
    std::cout << "Eye Manager v1.0" << std::endl;




    // Initialize the library
    if (gpioInitialise() < 0) {
        std::cerr << "Failed to initialize GPIO\n";
        return 1;
    }

    // Set the pin to be an output
    gpioSetMode(RIGHT_BL_PIN, PI_OUTPUT);
    gpioSetMode(LEFT_BL_PIN, PI_OUTPUT);


    std::cout << "Setting up right display:" << std::endl;
    auto spi_interface = std::make_shared<SPIInterface>();
    auto right_eye = std::make_shared<Round_1_28>(spi_interface,
                                                  27,
                                                  RIGHT_BL_PIN);

    auto aux_spi_interface = std::make_shared<SPIInterface>(1, 0 , 26);
    auto left_eye = std::make_shared<Round_1_28>(aux_spi_interface,
                                                  6,
                                                  LEFT_BL_PIN);


    std::cout << "  - starting display" << std::endl;
    right_eye->open();
    left_eye->open();

    right_eye->composer()->clear_screen(255, 128, 0);
    right_eye->blit_next_frame();

    left_eye->composer()->clear_screen(255, 128, 255);
    left_eye->blit_next_frame();



    std::this_thread::sleep_for(std::chrono::seconds(20));

//    right_eye->clear()


    std::cout << "  - done." << std::endl;

    // Cleanup
//    spiClose(handle);
    right_eye->close();
    left_eye->close();

    gpioTerminate();
    std::cout << "Done." << std::endl;
    return 0;
}
