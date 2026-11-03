/* #include "../app/can_in_boards.h"
#include "../app/can_in_motors.h"
#include "../app/motors.h"
#include "../app/typedef.h"
#include "can.h"
#include  "common_function.h"
#include "../app/gimbal_6020_control.h"
#include "../app/ammo_booster.h"
#include  "disconnect.h"
uint8_t rx_data[8];  

void HAL_CAN_RxFifo0MsgPendingCallback(CAN_HandleTypeDef *hcan)
{
    CAN_RxHeaderTypeDef rx_header;

    HAL_CAN_GetRxMessage(hcan, CAN_RX_FIFO0, &rx_header, rx_data);

    if (hcan->Instance == CAN1)
    {
        switch (rx_header.StdId)
        {
        case CAN_3508_M1_ID:
        case CAN_3508_M2_ID:
        case CAN_3508_M3_ID:
        case CAN_3508_M4_ID:
        {
            static uint8_t i = 0;
            // get motor id
            i = rx_header.StdId - CAN_3508_M1_ID;
            if (i==0)
                update_status(M3508_LEFT_ONLINE);
            else if (i==1)
                update_status(M3508_RIGHT_ONLINE);
            get_motor_3508_measure(&motors_3508_measure[i], rx_data);
            break;
        }
        case CAN_6020_M1_ID:
        case CAN_6020_M2_ID:

        {
            static uint8_t i = 0;
            // get motor id
            i = rx_header.StdId - CAN_6020_M1_ID;
            if (i==0)
                update_status(M6020_PITCH_ONLINE);
            else if (i==1)
                update_status(M6020_YAW_ONLINE);
            get_motor_6020_measure(&motors_6020_measure[i], rx_data);
            break;
        }

        case CAN_2006_M1_ID:
        case CAN_2006_M2_ID:
        {
            static uint8_t i = 0;
            // get motor id
            i = rx_header.StdId - CAN_2006_M1_ID;
            update_status(M6002_ONLINE);
            get_motor_2006_measure(&motors_2006_measure[i], rx_data);
            break;
        }

        default:
            break;
        }
    }
    else if (hcan->Instance == CAN2)
    {
        switch (rx_header.StdId)
        {
        case CHASSIS_C_BOARD:
        {
            update_status(CHASSIS_ONLINE);
            unpack_8bytes_to_2floats(rx_data, &yaw_offset, &pitch_offset);
            break;
        }

        case CHASSIS_C_BOARD + 1:
        {
            update_status(CHASSIS_ONLINE);
            change_fire_mode(rx_data[0],rx_data[1]);
            break;
        }

        default:
            break;
        }
    }
} */