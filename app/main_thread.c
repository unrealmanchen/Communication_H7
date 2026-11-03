#include "main_thread.h"

#include "cmsis_os.h"
#include "main.h"
#include "online.h"
#include "string.h"
#include "user_lib.h"   
#include "bsp_uart.h"

void Main_Task(const void *arg);
void main_init(void);
void check_Status(void);

osMessageQDef(Main_Mailbox, 32, uint16_t);
osMessageQId Main_Mailbox_Hdl;

osThreadDef(Main_Task_Def,Main_Task, osPriorityLow, 0, 128);
osThreadId Main_Task_Hdl;

Main_Status_t Status;

void main_init(){
    Main_Mailbox_Hdl = osMessageCreate(osMessageQ(Main_Mailbox), NULL);
    Main_Task_Hdl = osThreadCreate(osThread(Main_Task_Def),NULL);
}


int Error_Counter[20][20][20];
void Error_Hdl(Error_identify_ID ID,int num,int num2){
    Error_Counter[ID][num][num2]++;
}

void Power_ON_func(int id){
    Status = ON;
}

void Power_OFF_func(int id){
    Status = OFF;
}

void Main_Task(const void *arg){
    osEvent event;
    uint16_t msg;
    uint8_t msg_type, msg_index;
    while(1){
        event = osMessageGet(Main_Mailbox_Hdl, 0);

        while (event.status == osEventMessage) {
            msg = (uint16_t)event.value.v;

            switch (msg)
            {
            case 1:
                /* code */
                break;
            
            default:
                break;
            }
            
            event = osMessageGet(Main_Mailbox_Hdl, 0);
        }

        switch (Status)
        {
        case STBY:{
            check_Status();
            break;
        }
            
            
        
        default:
            break;
        }
        osDelay(100);
    }
    

}


void check_Status(){
    char data[10];
    char input = 0;
    memset(data,0,10);
    CMD_PackPacket(&input,1,0x107,data);
    UART_Tx(&UART_Chassis,data,10);
    memset(input,0,10);
    CMD_PackPacket(&input,1,0x607,data);
    UART_Tx(&UART_Gimbal,data,10);
}
