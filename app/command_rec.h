#ifndef UPC_COMMUNICATE_H
#define UPC_COMMUNICATE_H
#include "typedef.h"

#define UPC_HEADER 0xA5
#define UPC_HEADER_LEN 5
#define UPC_DATA_LEN 0x0D
#define UPC_TOTAL_LEN (UPC_DATA_LEN + 9) 
// typedef struct
// {
// 	uint8_t start_upc_flag;
// 	uint8_t mode;
// 	uint8_t shoot;

// 	float vx, vy, vw;
// 	float gimbal_yaw, chassis_yaw;
// 	float small_gimbal_yaw, small_gimbal_pitch;
// 	float x, y, z;

// 	fp32 last_online;

// } upc_t;

// typedef struct
// {
// 	uint8_t start_upc_flag;
// 	uint8_t mode;
// 	uint8_t shoot;

// 	float vx, vy, vw;
// 	float gimbal_yaw, chassis_yaw;
// 	float small_gimbal_yaw, small_gimbal_pitch;
// 	float x, y, z;

// 	fp32 last_online;

// } Std_t;

typedef enum
{
    Chassis_Yaw_data = 0x201,
    Chassis_Status = 0x202,
    Chassis_Start_Callback = 0x203,
    Chassis_Online = 0x207,
    Chassis_SuperCell = 0x208,


		SNED_DEBUG_ID = 0x300,
		SEND_ATTITUDE_ID = 0x301,
		SNED_REFEREE_ID = 0x302,
	
    MSG_DEBUG_ID = 0x0400, // Debug message
    MSG_IMU_INFO_ID = 0x0401,
    MSG_MOVE_CMD_ID = 0x0402, // Move command
    GIMBAL_ROTATION_ID = 0x0403, // Gimbal rotation command
	MSG_SHOOT_CMD_ID = 0x0404, 
	MSG_SHOOT_EASY_CMD_ID = 0x405,

    MSG_SMALL_GIMBAL_IMU_INFO_ID = 0x501,
    MSG_BIG_GIMBAL_IMU_INFO_ID = 0x102
} upc_cmd_t;


int upc_decode(char* rx_data,int size);
// void temp_imu_handler(uint8_t* data);

#endif
