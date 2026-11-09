#include "hdware_init.h"
#include "bsp_led.h"
#include "bsp_can.h"

#include "bsp_timer.h"
#include "bsp_uart.h"

void Hardware_Init(void){
    can_filter_init();
    Timer_Init();

    
    UART_init_list();
    //UART_6_INIT();
    uart_init_flag =1;
}
