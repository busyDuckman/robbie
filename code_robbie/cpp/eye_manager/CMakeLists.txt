cmake_minimum_required(VERSION 3.19)  #3.22
project(eye_manager)

set(CMAKE_CXX_STANDARD 20)

include_directories(spi_display)

# the pi version
add_executable(eye_manager
        spi_display/Round_1_28.cpp
        spi_display/Round_1_28.h
        spi_display/Display.cpp
        spi_display/Display.h
        main.cpp
        spi_display/Interface.h spi_display/Interface.cpp
        graphics/composer.h graphics/composer.h
        graphics/composer.cpp graphics/canvas_ity.hpp)

find_library(PIGPIO_LIBRARY pigpio)
find_package(OpenCV REQUIRED)
include_directories(${OpenCV_INCLUDE_DIRS})

target_link_libraries(${PROJECT_NAME} ${PIGPIO_LIBRARY})
#target_link_libraries(${PROJECT_NAME} ${PIGPIO_LIBRARY} rt)

target_link_libraries(${PROJECT_NAME} ${OpenCV_LIBS})

