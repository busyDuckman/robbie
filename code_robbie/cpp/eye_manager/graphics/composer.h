#ifndef EYE_MANAGER_COMPOSER_H
#define EYE_MANAGER_COMPOSER_H

#include <opencv2/opencv.hpp>
#include <opencv2/core.hpp>
#include <string_view>
#include <vector>
#include <algorithm>
#include <cmath>
#include <tuple>

// This needs to be in the project properties c/c++ pre-processor definitions as well
// because pecompiled headers...
// It's a nonsense amount of work just to get M_PI
#define _USE_MATH_DEFINES
#include <cmath>

/**
 * This sprite class stores the rgb and alpha images separate.
 * It's a leftover from the code I got working in python.
 * I'd rather keep the mess than spend extra time to perfect this.
 */
class Sprite
{
    // Every time I use friend in c++ it was the wrong approach.
    // I leave this note, so I can come back and say I told me so.
    friend class Composer;

private:
    int width_;
    int height_;
    bool alpha_composite_;
    cv::Mat image_;
    cv::Mat alpha_image_;

public:
    /**
     * Creates a sprite.
     * @param src_img       Image
     * @param strip_alpha   keep the transparency or not.
     * @param rb_swap       Swap red and blue channel ordering.
     */
    Sprite(cv::Mat src_img, bool strip_alpha=false, bool rb_swap=false)
    {
        // strip the alpha channel in any case, cause that's the mess I am in.
        if (src_img.channels() == 4) {
            cv::cvtColor(src_img, image_, cv::COLOR_BGRA2BGR);
        } else {
            image_ = src_img.clone();
        }

        if (rb_swap) {
            cv::cvtColor(image_, image_, cv::COLOR_BGR2RGB);
        }

        alpha_composite_ = (src_img.channels() == 4) && !strip_alpha;

        if (alpha_composite_) {
            // apply alpha pre-multiplication
            cv::Mat alpha;
            cv::extractChannel(src_img, alpha, 3); // get alpha from the original image
            cv::multiply(image_, alpha, image_, 1.0 / 255.0);
            cv::subtract(cv::Scalar::all(1.0), alpha, alpha_image_, cv::noArray(), CV_32F);
        }
    }
};


class Composer
{
    friend void test_get_polar();

private:
    int width_;
    int height_;
    std::vector<cv::Mat> buffers_;
    int frame_;
    cv::Mat draw_buffer_;     // a member of buffers_
    cv::Mat render_buffer_;   // a member of buffers_
    //std::vector<uint32_t> rt_lut_;
    static const int max_polar_lut_dist = 256;
    static const std::vector<uint32_t> polar_lut_;  // polar_coord look up take

    /**
    * Uses a lut to quickly do cartesian to polar conversion.
    */
    void get_polar(int x, int y, uint16_t& dist_10, uint16_t& angle_100) {
        // polar_lut_ is defined for 0 to 45deg (x<y) and x and y are posivie.
        // we use the 8 way circle symmetry trick to do the rest.

        bool x_flip = x < 0;
        bool y_flip = y < 0;
        x = abs(x);
        y = abs(y);
        bool flip_45 = y > x;

        //auto idx = y * (max_polar_lut_dist - y) + x - y;
        if (flip_45) std::swap(x, y);
        auto idx = y * (y + 1) / 2 + x;  // Equivalent to y*(y+1)/2 + x to get index in 1D from 2D (0<=x<=y)

        uint32_t val = polar_lut_[idx];

        dist_10 = val >> 16;

        int a_100 = (uint16_t)(val & 0xffff);  // will be cast to angle_100 later
        if (y_flip)  a_100 = 18000 - a_100;
        if (x_flip)  a_100 = 36000 - a_100;
        if (flip_45) a_100 = 9000  - a_100;

        while (a_100 < 0) a_100 += 36000; // wasn't there a more effecient way to do this without a while loop?
        while (a_100 >= 36000) a_100 -= 36000;
        angle_100 = (uint16_t) a_100;

    }

public:
    Composer(int w, int h)
            : width_(w), height_(h), frame_(0)
    {
        buffers_.emplace_back(cv::Mat::zeros(h, w, CV_8UC3));
        buffers_.emplace_back(cv::Mat::zeros(h, w, CV_8UC3));
        next_frame();
    }

    Sprite get_native_sprite(const cv::Mat& source)
    {
        return Sprite(source);
    }

    bool next_frame()
    {
        frame_++;
        draw_buffer_ = buffers_[frame_ % 2];
        render_buffer_ = buffers_[(frame_ + 1) % 2];
        return !(frame_ % 2);
    }

    void clear_screen(uint8_t r, uint8_t g, uint8_t b)
    {
        draw_buffer_.setTo(cv::Scalar(r, g, b));
    }

    const cv::Mat& draw_buffer() const {
        return draw_buffer_;
    }

    cv::Mat& editable_draw_buffer() {
        return draw_buffer_;
    }

    void draw_sprite(Sprite& sprite, int x, int y)
    {
        cv::Mat roi = draw_buffer_(cv::Rect(x, y, sprite.width_, sprite.height_));

        if (sprite.alpha_composite_)
        {
            roi += sprite.image_ * sprite.alpha_image_;
        }
        else
        {
            sprite.image_.copyTo(roi);
        }
    }

    void draw_round_thing(int cx, int cy,
        int inner_r, int outer_r,
        int start_angle, int end_angle,
        uint32_t colour)
    {
        int d = outer_r * 2;
        int x1 = cx - outer_r;
        int y1 = cy - outer_r;
        int x2 = x1 + d;
        int y2 = y1 + d;

        uint16_t start_angle_100 = start_angle * 100;
        uint16_t end_angle_100 = end_angle * 100;
        uint16_t r1_10 = inner_r * 10;
        uint16_t r2_10 = outer_r * 10;

        bool normal_test = true;
        if (start_angle_100 > end_angle_100) {
            // 0 deg is inside the range of angles
            // we switch the start end, and revers the testing condition.
            normal_test = false;
            uint16_t temp = start_angle_100;
            start_angle_100 = end_angle_100;
            end_angle_100 = temp;
        }

        uint8_t blue = colour & 0xFF;
        uint8_t green = (colour >> 8) & 0xFF;
        uint8_t red = (colour >> 16) & 0xFF;
        auto render_pixel = cv::Vec3b(blue, green, red);

        // x, y iterate over the space 0 to d
        // that space needs to be clipped to not go off screen
        int x_start = 0, y_start = 0;
        if (x1 >= width_) return;      // entirely off screen
        if (x1 < 0) x_start += -x1;
        if (y1 >= height_) return;     // entirely off screen
        if (y1 < 0) y_start += -y1;

        int x_end = d, y_end = d;
        if (x2 < 0) return;
        if (x2 >= width_)  x_end -= (x2 - width_);
        if (y2 < 0) return;
        if (y2 >= height_) y_end -= (y2 - height_);

        // iteratre dwaring in pixels
        for (int y = y_start; y < y_end; y++) {
            int y_local = y - outer_r;
            for (int x = x_start; x < x_end; x++) {
                int x_local = x - outer_r;
                //float dist = (float)std::sqrt(x_local * x_local + y_local * y_local);
                //float angle = std::atan2(y_local, x_local) * 180.0 / M_PI;
                //if (angle < 0) angle += 360;

                //uint32_t dist_10 = (int)(dist * 10);
                //uint32_t angle_100 = (uint32_t)(angle * 100);

                uint16_t dist_10, angle_100;
                get_polar(x_local, y_local,     // in
                          dist_10, angle_100    // out
                         );
                
                if ((dist_10 < r1_10) || (dist_10 > r2_10)) {
                    continue;
                }

                
                /*
                bool angle_ok = (angle_100 >= start_angle_100) && (angle_100 <= end_angle_100);
                if (angle_ok != normal_test) {
                    continue;
                }
                */
                

                cv::Vec3b& pixel = draw_buffer_.at<cv::Vec3b>(y+y1, x+x1);
                pixel = render_pixel;

            }
        }

        //std::cout << std::endl << std::endl;

    }

    // Assumes that angles are given in degrees.
    std::tuple<double, double, double, double> find_bounds_rt(double radius, double la_start, double la_end)
    {
        // Calculate the points on the circle for the start and end angles
        double sin_start = sin(la_start * M_PI / 180.0);
        double cos_start = cos(la_start * M_PI / 180.0);
        double sin_end = sin(la_end * M_PI / 180.0);
        double cos_end = cos(la_end * M_PI / 180.0);

        int x1 = (int)(radius * cos_start);
        int y1 = (int)(radius * sin_start);
        int x2 = (int)(radius * cos_end);
        int y2 = (int)(radius * sin_end);

        // The center of the circle is also a point of interest
        std::vector<std::pair<double, double>> points = { {0, 0}, {x1, y1}, {x2, y2} };

        // Check if the angles cross the x or y axis and add the points at the extremities
        if ((la_start <= 0 && 0 <= la_end) || (la_start <= 180 && 180 <= la_end)) {
            points.push_back({ radius, 0 });
        }
        if ((la_start <= 90 && 90 <= la_end) || (la_start <= 270 && 270 <= la_end)) {
            points.push_back({ 0, radius });
        }
        if ((la_start <= 180 && 180 <= la_end) || (la_start <= 360 && 360 <= la_end)) {
            points.push_back({ -radius, 0 });
        }
        if ((la_start <= 270 && 270 <= la_end) || (la_start <= 90 && 90 <= la_end)) {
            points.push_back({ 0, -radius });
        }

        // Calculate the bounding box around the points
        double min_x = std::min_element(points.begin(), points.end(), [](const auto& lhs, const auto& rhs) {
            return lhs.first < rhs.first;
            })->first;

        double max_x = std::max_element(points.begin(), points.end(), [](const auto& lhs, const auto& rhs) {
            return lhs.first < rhs.first;
            })->first;

        double min_y = std::min_element(points.begin(), points.end(), [](const auto& lhs, const auto& rhs) {
            return lhs.second < rhs.second;
            })->second;

        double max_y = std::max_element(points.begin(), points.end(), [](const auto& lhs, const auto& rhs) {
            return lhs.second < rhs.second;
            })->second;

        return std::make_tuple(min_x, max_x, min_y, max_y);
    }



//    uint16_t * round_thing_lut(outer_r) {
//        // memoize a lut for outer_r
//        // make the memo available to all Compose classes running.
//        // use something simple like  an array indexed by outer_r
//    }
};



void test_get_polar();

#endif //EYE_MANAGER_COMPOSER_H
