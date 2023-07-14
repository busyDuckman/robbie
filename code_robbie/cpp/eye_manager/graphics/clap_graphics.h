#ifndef CLAP_GRAPHICS_H
#define CLAP_GRAPHICS_H

#include <string>
#include <mutex>
#include <tuple>
#include <unordered_map>
#include <variant>
#include <opencv2/opencv.hpp>

const int FILLED_CIRCLE_ID = 1;

// Define parameters for each shape function
typedef std::tuple<int> CircleParams; // r for circle
// ... add other shape parameters here

// Define type for ShapeFuncID and ShapeParams
typedef std::pair<int, std::variant<CircleParams>> ShapeKey;

// Define custom hash function for ShapeKey
/*
struct KeyHash {
    std::size_t operator()(const ShapeKey& key) const {
        return std::hash<int>()(key.first) ^ std::visit([](auto&& arg) { return std::hash<int>()(arg); }, key.second);
    }
};*/
// Define custom hash function for ShapeKey
struct KeyHash {
    std::size_t operator()(const ShapeKey& key) const {
        auto hasher = [](const auto& arg) {
            return std::hash<int>()(std::get<0>(arg));
        };
        return std::hash<int>()(key.first) ^ std::visit(hasher, key.second);
    }
};

/**
* Cached pixel opacities for complex shapes.
*/
class CompiledLocalAntialiasedPixel {
public:
    cv::Mat pixel_data;
    int x_off = 0;
    int y_off = 0;

    CompiledLocalAntialiasedPixel(int width, int height) : pixel_data(width, height, CV_8UC1, cv::Scalar(0)) {}

    void set_pixel(int x, int y, uint8_t opacity) {
        pixel_data.at<uchar>(y, x) = opacity;
    }

    void compress() {
        cv::Rect bbox = cv::boundingRect(pixel_data);
        x_off = bbox.x;
        y_off = bbox.y;
        pixel_data = pixel_data(bbox);
    }

    /*
    void render(cv::Mat& img, int x, int y, cv::Scalar color) {
        cv::Mat color_mat(pixel_data.size(), CV_8UC4, color);
        cv::Mat alpha_mask = pixel_data.clone();
        cv::cvtColor(alpha_mask, alpha_mask, cv::COLOR_GRAY2BGR);
        cv::merge(std::vector<cv::Mat>{color_mat, alpha_mask}, color_mat);
        color_mat.copyTo(img(cv::Rect(x + x_off, y + y_off, color_mat.cols, color_mat.rows)), pixel_data);
    }*/

    
    void render(cv::Mat& img, int x, int y, uint32_t rgb) {
        //std::cout << "rendering";
        int blue = (rgb >> 16) & 0xFF;
        int green = (rgb >> 8) & 0xFF;
        int red = rgb & 0xFF;
        cv::Vec3b color(blue, green, red);

        cv::Mat color_mat(pixel_data.size(), CV_8UC3, color);
        std::vector<cv::Mat> rgba;
        cv::split(color_mat, rgba);
        rgba.push_back(pixel_data);
        cv::merge(rgba, color_mat);

        cv::Rect roi(cv::Point(x + x_off, y + y_off), color_mat.size());
        cv::Mat destinationROI = img(roi);
        color_mat.copyTo(destinationROI, pixel_data);
    }

};

class ClapGraphics {
private:
    // Memo pad
    std::unordered_map<ShapeKey, std::shared_ptr<CompiledLocalAntialiasedPixel>, KeyHash> memo_pad_;

    // Lock for memo_pad_
    std::mutex mtx_;

public:
    void filled_circle(cv::Mat& img, int x, int y, int r, uint32_t color) {
        ShapeKey key = std::make_pair(FILLED_CIRCLE_ID, CircleParams(r));

        // do we know this already
        auto search = memo_pad_.find(key);
        if (search != memo_pad_.end()) {
            search->second->render(img, x, y, color);
            //std::cout << "existing circle";
            auto circle_params = std::get<CircleParams>(search->first.second);
            //std::cout << "circle details: r=" << std::get<0>(circle_params) << "\n";
            return;
        }
        std::cout << "-------------------new circle-----------------------------";

        // write lock
        std::lock_guard<std::mutex> lock(mtx_);

        // was it added in the mean time
        auto search_2 = memo_pad_.find(key);
        if (search_2 != memo_pad_.end()) {
            std::cout << "other thread made new circle";
            search_2->second->render(img, x, y, color);
            return;
        }


        // memoise
        std::cout << "making new circle";
        int d = r * 2;
        std::shared_ptr<CompiledLocalAntialiasedPixel> clap = std::make_shared<CompiledLocalAntialiasedPixel>(d, d);

        for (int clap_y = 0; clap_y < d; clap_y++) {
            int y_local = clap_y - r;
            for (int clap_x = 0; clap_x < d; clap_x++) {
                int x_local = clap_x - r;
                float dist = (float)std::sqrt(x_local * x_local + y_local * y_local);
                
                float q = dist - r;
                int alpha = 0;
                if (q < 0) {
                    alpha = 255;
                }
                else if (q < 1) {
                    alpha = (int)(255 * q);
                }
                clap->set_pixel(clap_x, clap_y, alpha);
                //float angle = std::atan2(y_local, x_local) * 180.0 / M_PI;
                //if (angle < 0) angle += 360;
            }
        }
        

        clap->compress();
        memo_pad_[key] = clap;

        // render
        clap->render(img, x, y, color);
    }


};

#endif // CLAP
