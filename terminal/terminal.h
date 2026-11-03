//
// Created by chenrc on 2026/2/12.
//

#ifndef COMMUNICATION_H7_TEMINAL_H
#define COMMUNICATION_H7_TEMINAL_H

#define TERMINAL_UART &huart1
#include "main.h"
#include "cmsis_os.h"


extern osThreadId Terminal_Task_hdle;
extern osMessageQId Terminal_RX_Queue_Hdle;
extern osPoolId Terminal_Pool_Hdle;


void Transmit_data2Terminal(char * data , int len);
void terminal_init(void);


#endif //COMMUNICATION_H7_TEMINAL_H