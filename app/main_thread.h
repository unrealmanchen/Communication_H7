#ifndef MAIN_THREAD
#define MAIN_THREAD
#include "cmsis_os.h"

typedef enum{
    OFF =0,
    ON,
    STBY,

}Main_Status_t;

typedef enum
{
    Chassis_CB_Receive_ON = 0,
    Chassis_CB_Receive_OFF,

    Power_ON,
    Power_OFF,

} Main_MailBox_ID;


typedef enum
{
    TX_queue =0,
    TX_send

} Error_identify_ID;

extern Main_Status_t Status;

extern osMessageQId Main_Mailbox_Hdl;
void main_init(void);
void Error_Hdl(Error_identify_ID ID,int num,int num2);
#endif
