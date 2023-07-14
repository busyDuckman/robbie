//
// Created by duckman on 16/06/2023.
//
#include<vector>
#include <cmath>

#include "composer.h"

std::vector<uint32_t> init_lut(int max_size) {
	std::vector<uint32_t> lut;

	// We compute only a 45 deg segment of the circle to save memory,
	// then use the '8 way circle symetry trick' to infer other values.
	for (int x = 0; x < max_size; x++) {
		for (int y = 0; y <= x; y++) {
			float dist = (float)std::sqrt(x * x + y * y);
			float angle = 0;
			if (dist > 0) {
				angle = std::atan2(y, x) * 180.0 / M_PI;
			}
			
			if (angle < 0) angle += 360;

			uint32_t dist_10 = (uint32_t)(dist * 10);
			uint32_t angle_100 = (uint32_t)(angle * 100);
			uint32_t lut_value = (dist_10 << 16) | angle_100;

			lut.emplace_back(lut_value);
		}
	}

	return lut;
}

const std::vector<uint32_t> Composer::polar_lut_ = init_lut(Composer::max_polar_lut_dist);


void test_get_polar() {
	Composer composer(100, 100);

	uint16_t dist_10;
	uint16_t angle_100;

	composer.get_polar(3, 4, dist_10, angle_100);
	std::cout << dist_10 << std::endl;

	for (int y = 0; y < 5; y++) {
		for (int x = 0; x < 5; x++) {
			uint16_t a, d;
			composer.get_polar(x, y, d, a);
			std::cout << "x: " << x << " y: " << y << " angle: " << a << " dist: " << d << std::endl;
		}
	}

	//assert(dist_10 == 50);  // 5.0 * 10
	//assert(std::abs(angle_100 - 5314) <= 1);  // 53.13 * 100, allow error of 1 due to rounding
}



