#ifndef IMU_INTER
#define IMU_INTER

#include "typedef.h"


#pragma pack(push, 1)  // 按字节对齐，确保结构体与协议一致
typedef struct { //Hl91格式
    uint8_t header[6];
    uint8_t tag;           // 数据包标签：0x91
    uint16_t main_status;  // 状态字
    int8_t temperature;    // 模块平均温度 °C
    float air_pressure;    // 气压 Pa
    uint32_t system_time;  // 系统时间 ms
    float acc_b[3];        // 校准后的加速度 XYZ G
    float gyr_b[3];        // 校准后的角速度 XYZ deg/s
    float mag_b[3];        // 磁强度 XYZ μT
    float roll;           // 横滚角 deg
    float pitch;          // 俯仰角 deg
    float yaw;            // 航向角 deg
    float quat[4];        // 四元数 WXYZ
} SensorDataPacket;
#pragma pack(pop)


extern SensorDataPacket imu_data_raw;


void imu_read_data(char * data, int size);
uint8_t imu_init(void);

#endif


