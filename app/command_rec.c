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



void rec_status_init(rec_status_t *rec)
{
    if (rec == NULL)
        return;

    rec->status          = header;   /* 初始期待的字段，一般传“期待帧头”那个枚举值 */
    rec->data_length     = 0;
    rec->cmd_id          = 0;
    rec->data_length_ptr = 0;
    memset(rec->data, 0, sizeof(rec->data));
}

int upc_decode(char data_, rec_status_t *cb)
{
    switch (cb->status)
    {
    case header:
        if (data_ == 0xA5)
            cb->status = length0;
        break;
    case length0:
        cb->data[1] = data_;
        cb->status = length1;

        break;
    case length1:
        cb->data_length = (uint8_t)data_ << 8 | cb->data[1];
        cb->status = stained;
        break;
    case stained:
        if (data_ != 0x00)
            cb->status = header;
        else
            cb->status = crc8;
        break;
    case crc8:
        cb->data[0] = 0xA5;
        cb->data[1] = cb->data_length & 0xff; 
        cb->data[2] = (cb->data_length >> 8) & 0xff;
        cb->data[3] = 0x00;
        cb->data[4] = data_;
        if (!Verify_CRC8_Check_Sum(cb->data, 5))
            cb->status = header;
        else
            cb->status = cmd_1;
        break;
    case cmd_1:
        cb->status = cmd_2;
        cb->data[5] = data_;
        break;
    case cmd_2:
        cb->status = data;
        cb->data[6] = data_;
        cb->cmd_id = cb->data[5] | cb->data[6] << 8;
        break;
    case data:
        cb->data[7 + cb->data_length_ptr] = data_;
        cb->data_length_ptr++;
        if (cb->data_length_ptr == cb->data_length)
        {
            cb->data_length_ptr = 0;
            cb->status = crc16_1;
        }

        break;
    case crc16_1:
        cb->data[7 + cb->data_length] = data_;
        cb->status = crc16_2;
        break;
    case crc16_2:
        cb->data[7 + cb->data_length + 1] = data_;
        if (Verify_CRC16_Check_Sum(cb->data, cb->data_length + 9))
        cmd_function(cb);
        cb->status = header;
    }
}

void cmd_function(rec_status_t *cb)
{
    uint8_t *data = &cb->data[7];
    char data_out[30];
    char data_buffer[30];
    memset(data_out, 0, 30);
    memset(data_buffer, 0, 30);
    CMD_PackPacket(data, 13, 0x103, data_buffer);
    UART_Tx((UART_STRUCT*)cb->father_node, data_buffer, 13+9);
    return;
    switch ((upc_cmd_t)cb->cmd_id)
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
        memcpy(&data_out[0], data + 4, 8);
        CMD_PackPacket(data_out, 13, 0x601, data_buffer);
        UART_Tx(&UART_Gimbal, data_buffer, sizeof(data_buffer));

        break;
    }
    case MSG_SHOOT_CMD_ID:
    {
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
    case 0x408:
    {
        memset(data_out, 0, 30);
        memcpy(&data_out[12], data, 1);
        CMD_PackPacket(data_out, 13, 0x105, data_buffer);
        UART_Tx(&UART_Chassis, data_buffer, sizeof(data_buffer));
        break;
    }
    case 0x0120:
    {
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
    case 0xfff:
    {
        memset(data_out, 0, 30);
        memcpy(&data_out[0], data + 4, 8);
        CMD_PackPacket(data_out, 13, 0x601, data_buffer);
        UART_Tx(&UART_Gimbal, data_buffer, sizeof(data_buffer));
        break;
    }
    default:
        break;
    }
}




// int upc_decode1(char *rx_data_input, int size)
// {

//     for (int i = 0; i < size; i++)
//     {

//         if (rx_data_input[i] == 0xA5 && i + 4 + 2 < size - 1)
//         {
//             char *rx_data = &rx_data_input[i];
//             if (!Verify_CRC8_Check_Sum(rx_data, 5))
//                 return 4;

//             uint16_t data_length = rx_data[1] | (rx_data[2] << 8);

//             if (i + 4 + 2 + data_length + 2 < size - 1)
//                 if (!Verify_CRC16_Check_Sum(rx_data, data_length + 9))
//                     return 5;

//             uint16_t cmd_id = (rx_data[6] << 8) | rx_data[5];
//             uint8_t *data = &rx_data[7];
//             switch ((upc_cmd_t)cmd_id)
//             {
//                 /////////////////////////////////////////////////////////////////////////////////////// NUC
//             case MSG_MOVE_CMD_ID:
//             {
//                 OnlineStatusUpdate(UPC);

//                 memset(data_out, 0, 30);
//                 CMD_PackPacket(data, 13, 0x103, data_buffer);
//                 UART_Tx(&UART_Chassis, data_buffer, sizeof(data_buffer));
//                 break;
//             }
//             case GIMBAL_ROTATION_ID:
//             {
//                 OnlineStatusUpdate(UPC);

//                 memset(data_out, 0, 30);
//                 memcpy(&data_out[4], data, 4);
//                 CMD_PackPacket(data_out, 13, 0x104, data_buffer);
//                 UART_Tx(&UART_Chassis, data_buffer, sizeof(data_buffer));

//                 memset(data_out, 0, 30);
//                 memcpy(&data_out[0], data + 4, 8);
//                 CMD_PackPacket(data_out, 13, 0x601, data_buffer);
//                 UART_Tx(&UART_Gimbal, data_buffer, sizeof(data_buffer));

//                 break;
//             }
//             case MSG_SHOOT_CMD_ID:
//             {
//                 memset(data_out, 0, 30);
//                 memcpy(&data_out[0], data, 1);
//                 CMD_PackPacket(data_out, 1, 0x604, data_buffer);
//                 UART_Tx(&UART_Gimbal, data_buffer, sizeof(data_buffer));
//                 break;
//             }

//             case MSG_SHOOT_EASY_CMD_ID:
//                 memset(data_out, 0, 30);
//                 memcpy(&data_out[0], data, 1);
//                 CMD_PackPacket(data_out, 1, 0x605, data_buffer);
//                 UART_Tx(&UART_Gimbal, data_buffer, sizeof(data_buffer));
//                 break;
//             case 0x409:
//                 memset(data_out, 0, 30);
//                 memcpy(&data_out[0], data, 1);
//                 CMD_PackPacket(data_out, 1, 0x109, data_buffer);
//                 UART_Tx(&UART_Chassis, data_buffer, sizeof(data_buffer));
//                 break;
//             case 0x408:
//             {
//                 memset(data_out, 0, 30);
//                 memcpy(&data_out[12], data, 1);
//                 CMD_PackPacket(data_out, 13, 0x105, data_buffer);
//                 UART_Tx(&UART_Chassis, data_buffer, sizeof(data_buffer));
//                 break;
//             }
//             case 0x0120:
//             {
//                 memset(data_out, 0, 30);
//                 memcpy(&data_out[0], data, 4);
//                 CMD_PackPacket(data_out, 4, 0x20D, data_buffer);
//                 UART_Tx(&UART_referee, data_buffer, sizeof(data_buffer));
//             }
//                 ////////////////////////////////////////////////////////////////////////////////////// 底盘
//             case Chassis_Status:
//             {
//                 OnlineStatusUpdate(CHASSIS_CB);

//                 if (GET_BIT(data[0], 0))
//                     OnlineStatusUpdate(CHASSIS_MOTOR_0);
//                 if (GET_BIT(data[0], 1))
//                     OnlineStatusUpdate(CHASSIS_MOTOR_1);
//                 if (GET_BIT(data[0], 2))
//                     OnlineStatusUpdate(CHASSIS_MOTOR_2);
//                 if (GET_BIT(data[0], 3))
//                     OnlineStatusUpdate(CHASSIS_MOTOR_3);
//                 if (GET_BIT(data[0], 4))
//                     OnlineStatusUpdate(CHASSIS_9025);
//                 break;
//             }
//             case Chassis_Start_Callback:
//             {
//                 OnlineStatusUpdate(CHASSIS_CB);

//                 if (data[0])
//                     osMessagePut(Main_Mailbox_Hdl, (uint32_t)Chassis_CB_Receive_OFF, 0);
//                 else
//                     osMessagePut(Main_Mailbox_Hdl, (uint32_t)Chassis_CB_Receive_ON, 0);
//             }
//             case Chassis_Online:
//             {
//                 OnlineStatusUpdate(CHASSIS_CB);
//             }
//             case Chassis_SuperCell:
//             {
//                 OnlineStatusUpdate(CHASSIS_CB);
//             }
//             case Chassis_Yaw_data:
//             {
//                 OnlineStatusUpdate(CHASSIS_CB);
//             }
//                 /////////////////////////////////////////////////////////////////////////////////////// 云台
//             case MSG_SMALL_GIMBAL_IMU_INFO_ID:
//             {
//                 memset(data_out, 0, 30);
//                 CMD_PackPacket(data, 13, 0x101, data_buffer);
//                 UART_Tx(&UART_NX, data_buffer, sizeof(data_buffer));
//                 break;
//             }

//             case MSG_BIG_GIMBAL_IMU_INFO_ID:
//                 // comm_cmd_big_gimbal_imu_handler(&rx_data[UPC_HEADER_LEN+2]);
//                 break;
//             case 0xfff:
//             {
//                 memset(data_out, 0, 30);
//                 memcpy(&data_out[0], data + 4, 8);
//                 CMD_PackPacket(data_out, 13, 0x601, data_buffer);
//                 UART_Tx(&UART_Gimbal, data_buffer, sizeof(data_buffer));
//                 break;
//             }
//             default:
//                 break;
//             }
//             i = i + 5 + 2 + data_length + 2 - 1 - 1;
//             if (i + 1 > size - 1)
//                 return;
//         }
//     }
// }
