//
// Created by chenrc on 2026/2/18.
//

#include "INIT.h"
#include "cmsis_os.h"
#include "hdware_init.h"
#include "task_list.h"
#include "terminal.h"
osThreadId LED_Task_hdle;
osThreadId Online_Task_hdle;
void INIT() {
    
    // osThreadDef(Online_Task, OnlineTask, osPriorityLow, 0, 128);
    // Online_Task_hdle = osThreadCreate(osThread(Online_Task), NULL);
    terminal_init();
    Hardware_Init();
    osThreadDef(LED_Task, StartledTask, osPriorityLow, 0, 128);
    LED_Task_hdle = osThreadCreate(osThread(LED_Task), NULL);
    online_init();
}