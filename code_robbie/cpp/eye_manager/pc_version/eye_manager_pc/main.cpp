#include <opencv2/opencv.hpp>
#include "../../graphics/composer.h"
#include "../../graphics/clap_graphics.h"

int main() {
    int width = 513;
    int height = 512;
    auto composer = std::make_shared<Composer>(width, height);
    auto claper = std::make_shared<ClapGraphics>();

    test_get_polar();
    //return 0;

    composer->clear_screen(0, 128, 255);

    //cv::Mat img(600, 800, CV_8UC3, cv::Scalar(0, 0, 0));

    int q = 0;
    int direction = 1;  // 1 means increase, -1 means decrease
    int max_q = 360;  // width / 2 - 10; // std::min(img.cols, img.rows) / 2 - 10;

    int idx = 0;
    while (true) {
        // img = cv::Scalar(0, 0, 0);
        // cv::circle(img, cv::Point(img.cols / 2, img.rows / 2), radius, cv::Scalar(0, 255, 0), 2);

        composer->clear_screen(0, (uint8_t)(64 + idx % 64), 255);

        //claper->filled_circle(composer->editable_draw_buffer(), 256, 256, 32, 0xffffff);

        int q2 = (int)(idx/2) % 360;

        composer->draw_round_thing(256, 256, 64, 196, q2, q, 0xff00ff);
        composer->draw_round_thing(256, 256, 96, 128, q, q2, 0x00ffff);

        // Show image
        cv::imshow("Circle", composer->draw_buffer());

        // Break if escape key is pressed
        if (cv::waitKey(10) == 27) {
            break;
        }

        // Update radius
        q += direction;
        if (q >= max_q || q <= 0) {
            direction = -direction;
        }

        idx++;
    }

    return 0;
}

