//
// Created by chenrc on 2026/1/30.
//

#include "referee.h"
#include "crc.h"
#include "string.h"
#include "bsp_uart.h"
#include "user_lib.h"
referee_data_t referee_data;
char data_temp[64];
int seq_last=0,lost_times=0,lost_times_percent_times=0;
float lost_times_percent=0;

char data_buffer_ref[40];
uint8_t Referee_data_decode(uint8_t *rx_data_input, int size)
{
    for (int i = 0; i < size; i++)
    {

        if (rx_data_input[i] == 0xA5 && i+4+2<size-1)
        {
            char *rx_data = &rx_data_input[i];
            if (!Verify_CRC8_Check_Sum(rx_data, 5))
                return 4;

            uint16_t data_length = rx_data[1] | (rx_data[2] << 8);
            if(rx_data[3] != seq_last +1 && rx_data > seq_last){
                lost_times++;
                lost_times_percent_times++;
            } 
            if(rx_data[3] < seq_last){
                lost_times_percent = (float)lost_times_percent_times/256.0f;
                lost_times_percent_times =0;

            }
            seq_last = rx_data[3];
            if(i -1 + 5 +2 +data_length +2 < size -1)
            if (!Verify_CRC16_Check_Sum(rx_data, data_length + 9))
                return 5;

            uint16_t cmd_id = (rx_data[6] << 8) | rx_data[5];

            switch (cmd_id)
            {
            case CMD_ID_GAME_STATUS:
                memcpy(&referee_data.game_status, &rx_data[7], sizeof(game_status_t));
                break;
            case CMD_ID_GAME_RESULT:
                memcpy(&referee_data.game_result, &rx_data[7], sizeof(game_result_t));
                break;
            case CMD_ID_GAME_ROBOT_HP:
                memcpy(&referee_data.game_robot_hp, &rx_data[7], sizeof(game_robot_HP_t));
                break;
            case CMD_ID_EVENT_DATA:
                memcpy(&referee_data.event_data, &rx_data[7], sizeof(event_data_t));
                break;
            case CMD_ID_REFEREE_WARNING:
                memcpy(&referee_data.referee_warning, &rx_data[7], sizeof(referee_warning_t));
                break;
            case CMD_ID_DART_INFO:
                memcpy(&referee_data.dart_info, &rx_data[7], sizeof(dart_info_t));
                break;
            case CMD_ID_ROBOT_PERFORMANCE:
                memcpy(&referee_data.robot_performance, &rx_data[7], sizeof(robot_performance_t));
                break;
            case CMD_ID_POWER_HEAT_DATA:
                memcpy(&referee_data.power_heat_data, &rx_data[7], sizeof(power_heat_data_t));
                memset(data_temp,0,4);
                pack_float_to_4bytes(referee_data.power_heat_data.buffer_energy,data_temp);
                CMD_Transmit(data_temp,4,0x108,&UART_Chassis);
                break;
            case CMD_ID_ROBOT_POS:
                memcpy(&referee_data.robot_pos, &rx_data[7], sizeof(robot_pos_t));
                break;
            case CMD_ID_BUFF_DATA:
                memcpy(&referee_data.buff_data, &rx_data[7], sizeof(buff_data_t));
                break;
            case CMD_ID_HURT_DATA:
                memcpy(&referee_data.hurt_data, &rx_data[7], sizeof(hurt_data_t));
                break;
            case CMD_ID_SHOOT_DATA:
                memcpy(&referee_data.shoot_data, &rx_data[7], sizeof(shoot_data_t));
                break;
            case CMD_ID_PROJECTILE_ALLOWANCE:
                memcpy(&referee_data.projectile_allowance, &rx_data[7], sizeof(projectile_allowance_t));
                break;
            case CMD_ID_RFID_STATUS:
                memcpy(&referee_data.rfid_status, &rx_data[7], sizeof(rfid_status_t));
                break;
            case CMD_ID_DART_CLIENT_CMD:
                memcpy(&referee_data.dart_client_cmd, &rx_data[7], sizeof(dart_client_cmd_t));
                break;
            case CMD_ID_ROBOT_POS_EXT:
                memcpy(&referee_data.robot_pos_ext, &rx_data[7], sizeof(robot_pos_ext_t));
                break;
            case CMD_ID_MARK_PROGRESS:
                memcpy(&referee_data.mark_progress, &rx_data[7], sizeof(mark_progress_t));
                break;
            case CMD_ID_SENTRY_INFO:
                memcpy(&referee_data.sentry_info, &rx_data[7], sizeof(sentry_info_t));
                

				CMD_PackPacket(&referee_data.sentry_info, 6, 0x20D, data_buffer_ref);
				UART_Tx(&UART_NUC, data_buffer_ref, sizeof(data_buffer_ref));
                UART_Tx(&UART_Chassis, data_buffer_ref, sizeof(data_buffer_ref));
                break;
                // case CMD_ID_RADAR_INFO :
                //     memcpy(&referee_data.radar_info, &rx_data[7], sizeof(radar_info_t));
                // break;
            default :
                break;
            }

            UART_Tx(&UART_NUC,rx_data,data_length + 5 + 2 + 2);
            i = i + 5 + 2 +data_length + 2 -1 -1;
            if (i + 1 > size - 1)
                return;
        }
    }
}