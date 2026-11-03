
#include "imu_interface.h"
#include "bsp_timer.h"
#include "bsp_uart.h"
#include "crc.h"
#include "online.h"
#include "user_lib.h"
#include <stdint.h>
#include <string.h>



SensorDataPacket imu_data_raw;
// 解析函数
uint16_t templen;
uint8_t tempbuf[128];
int parse_sensor_data(char * data, int length) {
    if(length <82)
    return 0;
    for(int i=0;i<length;i++)
	{
		if(data[i]==0x5A&&data[i+1]==0xA5)
		{
			uint16_t payload_len = (uint16_t)data[i+3]<<8 | data[i+2];
			uint16_t crc;
			crc=0;
			templen = payload_len;
		

			crc16_update(&crc, &data[i], 4);
			crc16_update(&crc, &data[i] + 6, payload_len); 
			
			if(crc == ((uint16_t)data[i+5]<<8 | data[i+4])){
                memcpy(&imu_data_raw, &data[i], sizeof(SensorDataPacket));
				OnlineStatusUpdate(BIG_GIMBAL_IMU);
				break;
				
            }
				

		}
	}
    
    return 0; 
}

void imu_read_data(char * data, int size){
	parse_sensor_data(data,size);
	float dt = 0.002;
    float data123[4]={imu_data_raw.yaw,imu_data_raw.pitch,imu_data_raw.roll,imu_data_raw.yaw/dt};
	uint32_t * ptr = (uint32_t*)data123;
	uint8_t Tx_data[24]={0};
    Tx_data[3]  = (ptr[0] >> 24) & 0xFF;  // f1 字节3
    Tx_data[2]  = (ptr[0] >> 16) & 0xFF;  // f1 字节2
    Tx_data[1]  = (ptr[0] >> 8)  & 0xFF;  // f1 字节1
    Tx_data[0]  = ptr[0] & 0xFF;          // f1 字节0
    
    Tx_data[7]  = (ptr[1] >> 24) & 0xFF;  // f2 字节3
    Tx_data[6]  = (ptr[1] >> 16) & 0xFF;  // f2 字节2
    Tx_data[5]  = (ptr[1] >> 8)  & 0xFF;  // f2 字节1
    Tx_data[4]  = ptr[1] & 0xFF;          // f2 字节0

    Tx_data[11]  = (ptr[2] >> 24) & 0xFF;  // f3 字节3
    Tx_data[10]  = (ptr[2] >> 16) & 0xFF;  // f3 字节2
    Tx_data[9] = (ptr[2] >> 8)  & 0xFF;  // f3 字节1
    Tx_data[8] = ptr[2] & 0xFF;          // f3 字节0
    

    Tx_data[12] = 0;    

    char data1[23];
    CMD_PackPacket(Tx_data,13,0x102,data1);
	UART_Tx(&UART_Chassis,data1,sizeof(data1));
}
