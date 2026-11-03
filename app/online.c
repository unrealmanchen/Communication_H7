#include "online.h"

#include "typedef.h"
#include "bsp_timer.h"
#include "cmsis_os.h"

#define PACK_MESSAGE(type, index) ((((uint16_t)(type)) << 8) | ((uint16_t)(index)))
#define GET_TYPE(msg)  ((uint8_t)((msg) >> 8))
#define GET_INDEX(msg) ((uint8_t)(msg))

#define MSG_TYPE_INCREMENT_ALL 1
#define MSG_TYPE_CLEAR_INDEX 0

osMessageQDef(statusQueue, 32, uint16_t);
osMessageQId statusQueueHandle;

osThreadDef(Online_Task_Def, OnlineTask, osPriorityLow, 0, 128);
osThreadId Online_Task_Hdl;


void online_init(){
    statusQueueHandle = osMessageCreate(osMessageQ(statusQueue), NULL);
    Online_Task_Hdl = osThreadCreate(osThread(Online_Task_Def), NULL);
}

void OnlineStatusUpdate(OnlineID type) {
    uint16_t message;

    if (type == -1) {
        message = PACK_MESSAGE(MSG_TYPE_INCREMENT_ALL, 0);
    } else {
        message = PACK_MESSAGE(MSG_TYPE_CLEAR_INDEX, (uint8_t)type);
    }

    if(osMessagePut(statusQueueHandle, message, 0)!= osOK) {
        //?
    }

}


void OnlineTask(void const *argument) {
    osEvent event;
    uint16_t msg;
    uint8_t msg_type, msg_index;
    

    for(;;) {
        event = osMessageGet(statusQueueHandle, 0);

        while (event.status == osEventMessage) {
            msg = (uint16_t)event.value.v;
            msg_type = GET_TYPE(msg);
            msg_index = GET_INDEX(msg);

            if (msg_type == MSG_TYPE_INCREMENT_ALL) {
                for(int i = 0; i < TIM7_10ms.Timer_num; i++) {
                    TIM7_10ms.Counter[i]++;
                }
            } else {
                if (msg_index < TIM7_10ms.Timer_num) {
                    TIM7_10ms.Counter[msg_index] = 0;
                }
            }
            event = osMessageGet(statusQueueHandle, 0);
        }

        for(int i = 0; i < TIM7_10ms.Timer_num; i++) {
            //if(TIM7_10ms.Counter[i]>500)

        }
        osDelay(5);
    }
}

