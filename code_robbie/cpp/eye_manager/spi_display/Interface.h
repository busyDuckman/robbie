//
// Created by duckman on 14/06/2023.
//

#ifndef EYE_MANAGER_INTERFACE_H
#define EYE_MANAGER_INTERFACE_H

#include <cstdint>
#include <span>
#include <vector>

#define NOT_A_PORT 0xffff

class Interface
{
public:
    Interface() { };
    virtual ~Interface() = default;

    virtual bool open() = 0;
    virtual bool is_open() = 0;
    virtual void close() = 0;

    virtual void data(const std::span<const uint8_t> &data) {
        this->data(reinterpret_cast<const char*>(data.data()), data.size());
    }

    virtual void data(const char *data, unsigned len) = 0;
    virtual void data(uint8_t data) = 0;
    void data_chunked(const char* data, unsigned len, unsigned chunk_size, unsigned delay);

    virtual void command(uint8_t cmd) = 0;

    virtual void cmd_with_data(uint8_t cmd, const std::initializer_list<uint8_t> &data_list) {
        command(cmd);
        std::vector<uint8_t> data_vector(data_list);
        std::span<const uint8_t> data_span(data_vector);
        this->data(data_span);
    }


    /**
     * No purpose other than debugging.
     */
    virtual int get_handle() = 0;

    /**
    * No purpose other than debugging.
    */
    virtual int get_port() = 0;
};

class SPIInterface: public Interface
{
public:
    SPIInterface(unsigned int spi_channel = 0, unsigned int spi_device = 0, unsigned int dc_port = 25,
                 unsigned int spi_freq = 40000000);


    bool open() override;
    bool is_open() override;
    void close() override;

//    void data(const std::span<const uint8_t>& data) override;
    void data(const char *data, unsigned len) override;
    void data(uint8_t data) override;

    void command(uint8_t cmd) override;

    int get_handle() override { return spi_handle_; }
    int get_port() override { return spi_channel_; }

protected:
    unsigned spi_channel_, spi_device_, spi_freq_, dc_port_;
    int spi_handle_;
    bool in_data_mode_;
};


#endif //EYE_MANAGER_INTERFACE_H
