#include "fdcan.h"
// 假设 CubeMX 已生成全局句柄：FDCAN_HandleTypeDef hfdcan1, hfdcan2;

void can_filter_init(void)
{
    FDCAN_FilterTypeDef can_filter_st;

    /*** 初始化并启动 FDCAN1 ***/
    /* 1. 配置 FDCAN1 的全局过滤器 */
    can_filter_st.IdType = FDCAN_STANDARD_ID; // 标准ID模式
    can_filter_st.FilterIndex = 0; // 过滤器索引，可以对应F4的FilterBank概念
    can_filter_st.FilterType = FDCAN_FILTER_MASK;
    can_filter_st.FilterConfig = FDCAN_FILTER_TO_RXFIFO0; // 指定发送到RX FIFO 0
    can_filter_st.FilterID1 = 0x0000;
    can_filter_st.FilterID2 = 0x0000;

    if (HAL_FDCAN_ConfigFilter(&hfdcan1, &can_filter_st) != HAL_OK)
    {
        Error_Handler();
    }
    HAL_FDCAN_ConfigGlobalFilter(&hfdcan1 , FDCAN_REJECT , FDCAN_REJECT ,FDCAN_REJECT , FDCAN_REJECT);
    /* 2. 启动FDCAN1（这将启用FDCAN模块，类似F4的HAL_CAN_Start） */
    HAL_FDCAN_ActivateNotification(&hfdcan1,FDCAN_IT_RX_FIFO0_NEW_MESSAGE,0);

    if (HAL_FDCAN_Start(&hfdcan1) != HAL_OK)
    {
        Error_Handler();
    }





    can_filter_st.IdType = FDCAN_STANDARD_ID; // 标准ID模式
    can_filter_st.FilterIndex = 128; // 过滤器索引，可以对应F4的FilterBank概念
    can_filter_st.FilterType = FDCAN_FILTER_MASK;
    can_filter_st.FilterConfig = FDCAN_FILTER_TO_RXFIFO0; // 指定发送到RX FIFO 0
    can_filter_st.FilterID1 = 0x0000;
    can_filter_st.FilterID2 = 0x0000;

    if (HAL_FDCAN_ConfigFilter(&hfdcan2, &can_filter_st) != HAL_OK)
    {
        Error_Handler();
    }
    HAL_FDCAN_ConfigGlobalFilter(&hfdcan2 , FDCAN_REJECT , FDCAN_REJECT ,FDCAN_REJECT , FDCAN_REJECT);
    /* 2. 启动FDCAN1（这将启用FDCAN模块，类似F4的HAL_CAN_Start） */
    HAL_FDCAN_ActivateNotification(&hfdcan2,FDCAN_IT_RX_FIFO0_NEW_MESSAGE,0);

    if (HAL_FDCAN_Start(&hfdcan2) != HAL_OK)
    {
        Error_Handler();
    }
}

void HAL_FDCAN_RxFifo0Callback(FDCAN_HandleTypeDef *hfdcan, uint32_t RxFifo0ITs) {
    FDCAN_RxHeaderTypeDef rx_header;
    uint8_t rx_data[8];
    HAL_FDCAN_GetRxMessage(hfdcan, FDCAN_RX_FIFO0, &rx_header, rx_data);
    int a=0;
}


