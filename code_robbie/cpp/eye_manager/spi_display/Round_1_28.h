#ifndef EYE_MANAGER_ROUND_1_28_H
#define EYE_MANAGER_ROUND_1_28_H

#include "Display.h"

class Round_1_28 : public Display {
public:
    using Display::Display;

    Round_1_28(std::shared_ptr<Interface> interface,
               unsigned rst_port,
               unsigned bl_port,
               unsigned bl_freq = 1000);

    bool open() override;
    void close() override;

    void reset() override;

    void set_window(u_int x1, u_int y1, u_int x2, u_int y2) override;

};


#endif //EYE_MANAGER_ROUND_1_28_H
