#ifndef UART_NEW
#define UART_NEW
#include "usart.h"
#include "cmsis_os.h"
#include "ring_buffer_c.h"
#include "command_rec.h"
#define RX_BUFFER_SIZE 128


typedef struct {
    int uart_id;
    char Hd_Buffer[2][RX_BUFFER_SIZE];//硬件dma搬运位置
    int last_copy_ptr; //拷贝过的最后一个字符的地址

    UART_HandleTypeDef * huart;
    void (*function)(char * data ,int size);

    osSemaphoreDef_t sem_Tx_READY_t;
    osSemaphoreId sem_Tx_READY_Hdl;

    int init_Tx_thread;
    
    char thread_name[10];
    osPriority thread_osPriority;
    uint32_t   thread_stacksize;
    osThreadDef_t thread_Tx_t;
    osThreadId thread_Tx_Hdl;


    int mail_buffer_size;
    struct os_mailQ_cb *mail_Tx_cb; 
    osMailQDef_t mail_Tx_t; 
    osMailQId mail_Tx_Hdl;       
    uint8_t * mail_sending;//正在发送中的mail内容块 dma传输完毕前不能free

    rec_status_t rev_status;

    RingBufferC_u8_t * ring_ptr;
    
    
}UART_STRUCT;

extern UART_STRUCT UART_1;
extern UART_STRUCT UART_2;
extern UART_STRUCT UART_3;
extern UART_STRUCT UART_4;
extern UART_STRUCT UART_5;
extern UART_STRUCT UART_6;
extern UART_STRUCT UART_7;

#define UART_Terminal UART_1
#define UART_Gimbal UART_3
#define UART_imu UART_2
#define UART_Chassis UART_4
#define UART_NUC UART_5
#define UART_referee UART_6
#define UART_NX UART_7



extern int uart_init_flag;
void UART_init_list();

int UART_Tx(UART_STRUCT * uart,void * data,int len);
void UART_IT_Handler(UART_HandleTypeDef *huart);
void uart_printf(UART_HandleTypeDef *huart, const char *fmt,...);
#endif
