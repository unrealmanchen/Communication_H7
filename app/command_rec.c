/**
 * @file COMM_rec.c
 * @brief 与通信板串口通信模块
 * 用于处理通信板发到串口usart1的数据，并将其解析到相应的数据结构中。
 * 具体见通信协议。
 * @version 1.0
 * @date 2026-01-17
 */

#include "usart.h"
#include "bsp_uart.h"
#include "command_rec.h"
#include "crc.h"
#include "user_lib.h"
#include "string.h"
#include "online.h"
#include "main_thread.h"

char data_out[30];
char data_buffer[30];
int i11 = 0;

int upc_decode(char *rx_data_input, int size)
{

	for (int i = 0; i < size; i++)
	{

		if (rx_data_input[i] == 0xA5 && i + 4 + 2 < size - 1)
		{
			char *rx_data = &rx_data_input[i];
			if (!Verify_CRC8_Check_Sum(rx_data, 5))
				return 4;

			uint16_t data_length = rx_data[1] | (rx_data[2] << 8);

			if (i + 4 + 2 + data_length + 2 < size - 1)
				if (!Verify_CRC16_Check_Sum(rx_data, data_length + 9))
					return 5;

			uint16_t cmd_id = (rx_data[6] << 8) | rx_data[5];
			uint8_t *data = &rx_data[7];
			switch ((upc_cmd_t)cmd_id)
			{
/////////////////////////////////////////////////////////////////////////////////////// NUC
				case MSG_MOVE_CMD_ID:
				{
					OnlineStatusUpdate(UPC);

					memset(data_out, 0, 30);
					CMD_PackPacket(data, 13, 0x103, data_buffer);
					UART_Tx(&UART_Chassis, data_buffer, sizeof(data_buffer));
					break;
				}
				case GIMBAL_ROTATION_ID:
				{
					OnlineStatusUpdate(UPC);

					memset(data_out, 0, 30);
					memcpy(&data_out[4], data, 4);
					CMD_PackPacket(data_out, 13, 0x104, data_buffer);
					UART_Tx(&UART_Chassis, data_buffer, sizeof(data_buffer));

					memset(data_out, 0, 30);
					memcpy(&data_out[0], data+4, 8);
					CMD_PackPacket(data_out, 13, 0x601, data_buffer);
					UART_Tx(&UART_Gimbal, data_buffer, sizeof(data_buffer));

					break;
				}
				case MSG_SHOOT_CMD_ID:{
					memset(data_out, 0, 30);
					memcpy(&data_out[0], data, 1);
					CMD_PackPacket(data_out, 1, 0x604, data_buffer);
					UART_Tx(&UART_Gimbal, data_buffer, sizeof(data_buffer));
					break;
				}
					
				case MSG_SHOOT_EASY_CMD_ID:
					memset(data_out, 0, 30);
					memcpy(&data_out[0], data, 1);
					CMD_PackPacket(data_out, 1, 0x605, data_buffer);
					UART_Tx(&UART_Gimbal, data_buffer, sizeof(data_buffer));
					break;
				case 0x409:
					memset(data_out, 0, 30);
					memcpy(&data_out[0], data, 1);
					CMD_PackPacket(data_out, 1, 0x109, data_buffer);
					UART_Tx(&UART_Chassis, data_buffer, sizeof(data_buffer));
					break;
				case 0x408:{
					memset(data_out, 0, 30);
					memcpy(&data_out[12], data, 1);
					CMD_PackPacket(data_out, 13, 0x105, data_buffer);
					UART_Tx(&UART_Chassis, data_buffer, sizeof(data_buffer));
					break;
				}
				case 0x0120:{
					memset(data_out, 0, 30);
					memcpy(&data_out[0], data, 4);
					CMD_PackPacket(data_out, 4, 0x20D, data_buffer);
					UART_Tx(&UART_referee, data_buffer, sizeof(data_buffer));
				}
////////////////////////////////////////////////////////////////////////////////////// 底盘
				case Chassis_Status:
				{
					OnlineStatusUpdate(CHASSIS_CB);

					if (GET_BIT(data[0], 0))
						OnlineStatusUpdate(CHASSIS_MOTOR_0);
					if (GET_BIT(data[0], 1))
						OnlineStatusUpdate(CHASSIS_MOTOR_1);
					if (GET_BIT(data[0], 2))
						OnlineStatusUpdate(CHASSIS_MOTOR_2);
					if (GET_BIT(data[0], 3))
						OnlineStatusUpdate(CHASSIS_MOTOR_3);
					if (GET_BIT(data[0], 4))
						OnlineStatusUpdate(CHASSIS_9025);
					break;
				}
				case Chassis_Start_Callback:
				{
					OnlineStatusUpdate(CHASSIS_CB);

					if (data[0])
						osMessagePut(Main_Mailbox_Hdl, (uint32_t)Chassis_CB_Receive_OFF, 0);
					else
						osMessagePut(Main_Mailbox_Hdl, (uint32_t)Chassis_CB_Receive_ON, 0);
				}
				case Chassis_Online:
				{
					OnlineStatusUpdate(CHASSIS_CB);
				}
				case Chassis_SuperCell:
				{
					OnlineStatusUpdate(CHASSIS_CB);
				}
				case Chassis_Yaw_data:
				{
					OnlineStatusUpdate(CHASSIS_CB);
				}
/////////////////////////////////////////////////////////////////////////////////////// 云台
				case MSG_SMALL_GIMBAL_IMU_INFO_ID:
				{
					memset(data_out, 0, 30);
					CMD_PackPacket(data, 13, 0x101, data_buffer);
					UART_Tx(&UART_NX, data_buffer, sizeof(data_buffer));
					break;
				}

				case MSG_BIG_GIMBAL_IMU_INFO_ID:
					// comm_cmd_big_gimbal_imu_handler(&rx_data[UPC_HEADER_LEN+2]);
					break;
				case 0xfff:{
					memset(data_out, 0, 30);
					memcpy(&data_out[0], data+4, 8);
					CMD_PackPacket(data_out, 13, 0x601, data_buffer);
					UART_Tx(&UART_Gimbal, data_buffer, sizeof(data_buffer));
					break;
				}
				default:
					break;
				
			}
			i = i + 5 + 2 + data_length + 2 - 1 - 1;
			if (i + 1 > size - 1)
				return;
		}
	}
}

