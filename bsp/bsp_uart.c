#include "bsp_uart.h"

#include "main.h"
#include "usart.h"
#include <stdarg.h>
#include <stdio.h>
#include <string.h>
#include "terminal.h"
#include "cmsis_os.h"

#include "referee.h"
#include "command_rec.h"
#include "imu_interface.h"

#include "main_thread.h"
#include "ring_buffer_c.h"

/*
此new文件意义是将串口硬件初始化和串口应用的代码解耦，方便纠错以及理顺代码逻辑
堆屎山的时候稍微写点注释也好哇。（（（
2025-11-22 拆雷后感
*/

/*
一整天嗯读参考手册和数据手册
网上这种教程少得可怜，以下代码没参考任何教程（太tm混乱了）
加入双缓冲粘包处理
2026-1-26
*/

/*
成功驯服多线程转发
2026-2-19
*/

#define DMA_Instance(Handle) ((DMA_Stream_TypeDef *)Handle->Instance)
void UART_Mem0_Full(DMA_HandleTypeDef *hdma);
void UART_Mem1_Full(DMA_HandleTypeDef *hdma);
static void UART_TxTask(const void *arg);
static void UART_1_TxTask(const void *arg);
static void UART_2_TxTask(const void *arg);
static void UART_3_TxTask(const void *arg);
static void UART_4_TxTask(const void *arg);
static void UART_5_TxTask(const void *arg);
static void UART_6_TxTask(const void *arg);
static void UART_7_TxTask(const void *arg);
DMA_Stream_TypeDef *test;
int uart_init_flag = 0;
// 该函数线程不安全 不要不同线程调用
// 被舍弃
void uart_printf(UART_HandleTypeDef *huart, const char *fmt, ...)
{
    static uint8_t tx_buf[256] = {0};
    static va_list ap;
    static uint16_t len;
    va_start(ap, fmt);

    len = vsprintf((char *)tx_buf, fmt, ap);

    va_end(ap);

    HAL_UART_Transmit(huart, tx_buf, len, 100);
}

///////////////////////////////////////////////////////////
// osSemaphoreId UART_1_TX_READY_Hdl;
// osThreadId UART_1_TX_TASK_Hdl;
// osMailQId UART_1_TX_Mail_Hdl;

UART_STRUCT UART_1 = {
    .uart_id = 1,
    .huart = &huart1,
    .function = Transmit_data2Terminal,
    .init_Tx_thread = 1,
    .thread_name = "UART_1_TX",
    .thread_osPriority = osPriorityLow,
    .thread_stacksize = 128,
    .mail_buffer_size = 64

}; // 测试终端

UART_STRUCT UART_2 = {
    .uart_id = 2,
    .huart = &huart2,
    .function = imu_read_data,
    .init_Tx_thread = 1,
    .thread_name = "UART_2_TX",
    .thread_osPriority = osPriorityLow,
    .thread_stacksize = 128,
    .mail_buffer_size = 64}; // imu

UART_STRUCT UART_3 = {
    .uart_id = 3,
    .huart = &huart3,
    .function = upc_decode,
    .init_Tx_thread = 1,
    .thread_name = "UART_3_TX",
    .thread_osPriority = osPriorityLow,
    .thread_stacksize = 128,
    .mail_buffer_size = 64}; // 云台

UART_STRUCT UART_4 = {
    .uart_id = 4,
    .huart = &huart4,
    .function = NULL,
    .init_Tx_thread = 1,
    .thread_name = "UART_4_TX",
    .thread_osPriority = osPriorityLow,
    .thread_stacksize = 256,
    .mail_buffer_size = 64}; // 底盘

UART_STRUCT UART_5 = {
    .uart_id = 5,
    .huart = &huart5,
    .function = upc_decode,
    .init_Tx_thread = 1,
    .thread_name = "UART_5_TX",
    .thread_osPriority = osPriorityLow,
    .thread_stacksize = 128,
    .mail_buffer_size = 64}; // 上位机nuc

UART_STRUCT UART_6 = {
    .uart_id = 6,
    .huart = &huart6,
    .function = upc_decode,
    .init_Tx_thread = 1,
    .thread_name = "UART_6_TX",
    .thread_osPriority = osPriorityLow,
    .thread_stacksize = 128,
    .mail_buffer_size = 64}; // 裁判

UART_STRUCT UART_7 = {
    .uart_id = 7,
    .huart = &huart7,
    .function = upc_decode,
    .init_Tx_thread = 1,
    .thread_name = "UART_7_TX",
    .thread_osPriority = osPriorityLow,
    .thread_stacksize = 128,
    .mail_buffer_size = 64};

UART_STRUCT *Search_UART_ST(UART_HandleTypeDef *huart_in)
{

    if (huart_in == &huart1)
        return &UART_1;
    if (huart_in == &huart2)
        return &UART_2;
    if (huart_in == &huart3)
        return &UART_3;
    if (huart_in == &huart4)
        return &UART_4;
    if (huart_in == &huart5)
        return &UART_5;
    if (huart_in == &huart6)
        return &UART_6;
    if (huart_in == &huart7)
        return &UART_7;

    Error_Handler();
    return NULL;
}

void vApplicationStackOverflowHook(TaskHandle_t xTask, signed char *pcTaskName)
{
    BREAKPOINT; // 命中就说明是栈击穿
}

void UART_init(UART_STRUCT *uart)
{

    // test = DMA_Instance(uart->huart->hdmarx);
    uart->ring_ptr = rb_c_create(256);


    HAL_DMA_RegisterCallback(uart->huart->hdmarx, HAL_DMA_XFER_CPLT_CB_ID, UART_Mem0_Full);
    HAL_DMA_RegisterCallback(uart->huart->hdmarx, HAL_DMA_XFER_M1CPLT_CB_ID, UART_Mem1_Full);

    __HAL_UART_CLEAR_OREFLAG(uart->huart);
    __HAL_UART_CLEAR_IDLEFLAG(uart->huart);
    
    HAL_DMAEx_MultiBufferStart_IT(
        uart->huart->hdmarx,
        (uint32_t)&uart->huart->Instance->RDR,
        (uint32_t)&uart->Hd_Buffer[0][0],
        (uint32_t)&uart->Hd_Buffer[1][0],
        RX_BUFFER_SIZE); // 这个函数里会锁住dma 所以需要将回调函数注册放在该函数之前

    __HAL_DMA_DISABLE_IT(uart->huart->hdmarx, DMA_IT_HT);
    uart->huart->Instance->CR3 |= USART_CR3_DMAR;    // uart开启dma
    __HAL_UART_ENABLE_IT(uart->huart, UART_IT_IDLE); // 开启空闲中断

    if (uart->init_Tx_thread == 0)
        return;

    uart->sem_Tx_READY_t.controlblock = NULL;
    uart->sem_Tx_READY_t.dummy = 0;

    uart->thread_Tx_t.name = uart->thread_name;
    uart->thread_Tx_t.pthread = UART_TxTask;
    uart->thread_Tx_t.tpriority = uart->thread_osPriority;
    uart->thread_Tx_t.instances = 0;
    uart->thread_Tx_t.stacksize = uart->thread_stacksize;
    uart->thread_Tx_t.buffer = NULL;
    uart->thread_Tx_t.controlblock = NULL;

    uart->mail_Tx_t.queue_sz = 10;
    uart->mail_Tx_t.item_sz = sizeof(uint8_t) * (uart->mail_buffer_size + 2);
    uart->mail_Tx_t.cb = &(uart->mail_Tx_cb);

    uart->sem_Tx_READY_Hdl = osSemaphoreCreate(&uart->sem_Tx_READY_t, 1);
    uart->thread_Tx_Hdl = osThreadCreate(&uart->thread_Tx_t, uart);
    uart->mail_Tx_Hdl = osMailCreate(&uart->mail_Tx_t, NULL);
    
    if (uart->sem_Tx_READY_Hdl == NULL || 
        uart->thread_Tx_Hdl == NULL || 
        uart->mail_Tx_Hdl == NULL ||
        uart->ring_ptr == NULL)
        BREAKPOINT;

    rec_status_init(&uart->rev_status);
    uart->rev_status.father_node = (void *)uart;
    uart->last_copy_ptr = -1;
    uart->mail_sending = NULL;
}

void UART_init_list()
{

    UART_init(&UART_1);
    UART_init(&UART_2);
    UART_init(&UART_3);
    UART_init(&UART_4);
    UART_init(&UART_5);
    UART_init(&UART_6);
    UART_init(&UART_7);
}

void UART_Mem_Full_IT(UART_STRUCT *uart, int MEM_Loc)
{
    BaseType_t xHigherPriorityTaskWoken = pdFALSE;
    int length = RX_BUFFER_SIZE - (uart->last_copy_ptr + 1);
    for (int i = 0; i < length; i++)
    {
        if (rb_c_push(uart->ring_ptr, uart->Hd_Buffer[MEM_Loc][uart->last_copy_ptr + 1 + i]) == false)
        {
            uart->last_copy_ptr = -1;
            vTaskNotifyGiveFromISR(uart->thread_Tx_Hdl, &xHigherPriorityTaskWoken);
            BREAKPOINT;
            return;
        }
    }
    vTaskNotifyGiveFromISR(uart->thread_Tx_Hdl, &xHigherPriorityTaskWoken);
    uart->last_copy_ptr = -1;
}

void UART_Mem0_Full(DMA_HandleTypeDef *hdma)
{
    UART_STRUCT *temp = Search_UART_ST(hdma->Parent);
    UART_Mem_Full_IT(temp, 0);
}

void UART_Mem1_Full(DMA_HandleTypeDef *hdma)
{
    UART_STRUCT *temp = Search_UART_ST(hdma->Parent);
    UART_Mem_Full_IT(temp, 1);
}

void UART_IT_Handler(UART_HandleTypeDef *huart)
{
    BaseType_t xHigherPriorityTaskWoken = pdFALSE;
    UART_STRUCT *uart = Search_UART_ST(huart);

    if (__HAL_UART_GET_FLAG(uart->huart, UART_FLAG_IDLE))
    {
        __HAL_UART_CLEAR_IT(uart->huart, UART_CLEAR_IDLEF);

        int Mem_Loc = (DMA_Instance(uart->huart->hdmarx)->CR & DMA_SxCR_CT);
        if (Mem_Loc != 0)
            Mem_Loc = 1;

        int length = RX_BUFFER_SIZE - DMA_Instance(uart->huart->hdmarx)->NDTR - (uart->last_copy_ptr + 1);

        for (int i = 0; i < length; i++)
        {
            if (rb_c_push(uart->ring_ptr, uart->Hd_Buffer[Mem_Loc][i + uart->last_copy_ptr + 1]) == false)
            {
                uart->last_copy_ptr += i;
                vTaskNotifyGiveFromISR(uart->thread_Tx_Hdl, &xHigherPriorityTaskWoken);
                BREAKPOINT;
                return;
            }
        }
        uart->last_copy_ptr += length;
        vTaskNotifyGiveFromISR(uart->thread_Tx_Hdl, &xHigherPriorityTaskWoken);
    }
    else if (__HAL_UART_GET_FLAG(uart->huart, UART_IT_RXNE))
    {
        __HAL_UART_CLEAR_PEFLAG(uart->huart);
    }
}



void HAL_UART_TxCpltCallback(UART_HandleTypeDef *huart)
{
    UART_STRUCT *uart = Search_UART_ST(huart);
    if (uart->init_Tx_thread == 1)
    {
        

        int saved = taskENTER_CRITICAL_FROM_ISR();
        osMailFree(uart->mail_Tx_Hdl, uart->mail_sending);
        taskEXIT_CRITICAL_FROM_ISR(saved);

        osEvent evt = osMailGet(uart->mail_Tx_Hdl, 0);

        if (evt.status != osEventMail){
            osSemaphoreRelease(uart->sem_Tx_READY_Hdl);
            return;
        }
        
        uint8_t *block = (uint8_t *)evt.value.p;
        uart->mail_sending = block;
        uint16_t len = block[0] | (block[1] << 8);
        uint8_t *data = block + 2;

        HAL_StatusTypeDef status = HAL_UART_Transmit_DMA(uart->huart, data, len);
        if (status != HAL_OK)
            BREAKPOINT;
    }
}


int UART_Tx(UART_STRUCT *uart, void *data_in, int len)
{
    uint8_t *data = (uint8_t *)data_in;
    if (len == 0)
    {
        Error_Hdl(TX_send, uart->uart_id, 4);
        return 4;
    }

    if (len > uart->mail_buffer_size)
    {
        Error_Hdl(TX_send, uart->uart_id, 3);
        return 3;
    }

    

    uint8_t *msg_ptr = osMailAlloc(uart->mail_Tx_Hdl, 0);
    if (!msg_ptr)
    {
        Error_Hdl(TX_send, uart->uart_id, 2);
        return 2;
    }

    msg_ptr[0] = len & 0xFF;
    msg_ptr[1] = (len >> 8) & 0xFF;
    memcpy(msg_ptr + 2, data, len);

    if (osMailPut(uart->mail_Tx_Hdl, msg_ptr) != osOK)
    {
        osMailFree(uart->mail_Tx_Hdl, msg_ptr);
        Error_Hdl(TX_send, uart->uart_id, 1);
        return 1;
    }

    if (osSemaphoreWait(uart->sem_Tx_READY_Hdl, 0) == osOK)
    {
        // int saved = taskENTER_CRITICAL_FROM_ISR();
        // osMailFree(uart->mail_Tx_Hdl, uart->mail_sending);
        // taskEXIT_CRITICAL_FROM_ISR(saved);

        osEvent evt = osMailGet(uart->mail_Tx_Hdl, 0);

        if (evt.status != osEventMail){
            osSemaphoreRelease(uart->sem_Tx_READY_Hdl);
            return;
        }
        
        uint8_t *block = (uint8_t *)evt.value.p;
        uart->mail_sending = block;
        uint16_t len = block[0] | (block[1] << 8);
        uint8_t *data = block + 2;

        HAL_StatusTypeDef status = HAL_UART_Transmit_DMA(uart->huart, data, len);
        if (status != HAL_OK)
            BREAKPOINT;
        return 0;
    }
    return 0;
}

static void UART_TxTask(const void *arg)
{
    UART_STRUCT *uart = (UART_STRUCT *)arg;
    uint8_t data;
    while (1)
    {
        ulTaskNotifyTake(pdTRUE, portMAX_DELAY);
        
        while (!rb_c_empty(uart->ring_ptr))
        {
            rb_c_pop(uart->ring_ptr, &data);
            upc_decode(data, &uart->rev_status);
        }
    }
}



