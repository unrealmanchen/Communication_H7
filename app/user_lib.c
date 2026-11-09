/**
 * @file user_lib.c
 * @brief 数学函数模块
 * 常见数学函数。
 * @version 1.0
 * @date 2026-01-17
 */

#include "stdlib.h"
#include "string.h"
#include "user_lib.h"
#include "math.h"
#include "main.h"
#include "crc.h"
#include "bsp_uart.h"
#include <stdint.h>
#include <string.h>

// 假设这两个函数已在其他地方实现

#define SOF_VALUE       0xA5
#define FRAME_HEADER_LEN  5
#define CMD_ID_LEN        2
#define CRC16_LEN         2
#define CRC8_INIT         0xFF  // 假设值，请根据实际调整
#define CRC16_INIT        0xFFFF // 假设值，请根据实际调整

/**
 * @brief 组串口协议包
 * @param data_in 输入数据指针
 * @param data_len 输入数据长度
 * @param cmd_id 命令ID
 * @param data_out 输出缓冲区指针（调用者提供，需保证足够空间）
 */
void CMD_PackPacket(char *data_in, uint16_t data_len, uint16_t cmd_id, uint8_t *data_out)
{
    uint32_t offset = 0;
    uint16_t total_len;
    uint8_t crc8;
    uint16_t crc16;
    
    data_out[offset++] = SOF_VALUE;                    // SOF
    
    data_out[offset++] = data_len & 0xFF;              // 低字节
    data_out[offset++] = (data_len >> 8) & 0xFF;       // 高字节
    
    data_out[offset++] = 0;                           // seq
    
    data_out[offset++] = 0;                             // CRC8占位
    
    data_out[offset++] = cmd_id & 0xFF;                 // 低字节
    data_out[offset++] = (cmd_id >> 8) & 0xFF;          // 高字节
    
    if (data_in != NULL && data_len > 0) {
        memcpy(&data_out[offset], data_in, data_len);
        offset += data_len;
    }
    
    crc8 = Get_CRC8_Check_Sum(data_out, FRAME_HEADER_LEN - 1, CRC8_INIT);
    data_out[4] = crc8;  // 帧头第5字节是CRC8
    
    total_len = FRAME_HEADER_LEN + CMD_ID_LEN + data_len;
    crc16 = Get_CRC16_Check_Sum(data_out, total_len, CRC16_INIT);
    
    data_out[total_len] = (uint8_t)(crc16 & 0xFF);        // 低字节
    data_out[total_len + 1] = (uint8_t)((crc16 >> 8) & 0xFF); // 高字节
}
char CMD_Tx_data_temp[256];
void CMD_Transmit(char *data_in, uint16_t data_len, uint16_t cmd_id, UART_STRUCT *uart){
    memset(CMD_Tx_data_temp,0,256);
    CMD_PackPacket(data_in,data_len,cmd_id,CMD_Tx_data_temp);
    UART_Tx(uart,CMD_Tx_data_temp,data_len+5+2+2);
}
    /*---------------------------------------数据转换--------------------------------------- */
    /**
     * @brief          将4位uint8_t转换为1个float
     * @param[in]      4个uint8_t
     * @retval         1个float
     */
    void unpack_4bytes_to_floats(const uint8_t data[4], float *f1)
{
    uint32_t u1;
    
    // 小端序
    u1 = (uint32_t)data[0] | 
         ((uint32_t)data[1] << 8) | 
         ((uint32_t)data[2] << 16) | 
         ((uint32_t)data[3] << 24);
    
    memcpy(f1, &u1, sizeof(float));
}

/**
 * @brief          将1个float转换为4位uint8_t
 * @param[in]      1个float
 * @retval         4个uint8_t
 */
void pack_float_to_4bytes(float f1, uint8_t data[4]) {

    uint32_t u1 = *((uint32_t*)&f1);
    
    data[3] = (uint8_t)((u1 >> 24) & 0xFF); 
    data[2] = (uint8_t)((u1 >> 16) & 0xFF);
    data[1] = (uint8_t)((u1 >> 8)  & 0xFF);
    data[0] = (uint8_t)(u1 & 0xFF);    
}
/*------------------------------------------------------------------------------------- */

/*-------------------------------------常用数学函数------------------------------------- */
// 快速开方
float q_sqrt(float x)
{
    float y;
    float delta;
    float maxError;

    if (x <= 0)
    {
        return 0;
    }

    // initial guess
    y = x / 2;

    // refine
    maxError = x * 0.001f;

    do
    {
        delta = (y * y) - x;
        y -= delta / (2 * y);
    } while (delta > maxError || delta < -maxError);

    return y;
}

// 快速平方倒数
float invSqrt(float num)
{
    float halfnum = 0.5f * num;
    float y = num;
    long i = *(long *)&y;
    i = 0x5f375a86- (i >> 1);
    y = *(float *)&i;
    y = y * (1.5f - (halfnum * y * y));
    return y;
}

// 绝对值限制
float abs_limit(float num, float Limit)
{
    if (num > Limit)
    {
        num = Limit;
    }
    else if (num < -Limit)
    {
        num = -Limit;
    }
    return num;
}
    
// 判符函数 
float sign(float value)
{
    if (value >= 0.0f)
    {
        return 1.0f;
    }
    else
    {
        return -1.0f;
    }
}

//float死区
float float_deadband(float Value, float minValue, float maxValue)
{
    if (Value < maxValue && Value > minValue)
    {
        Value = 0.0f;
    }
    return Value;
}

//int16死区
int16_t int16_deadband(int16_t Value, int16_t minValue, int16_t maxValue)
{
    if (Value < maxValue && Value > minValue)
    {
        Value = 0;
    }
    return Value;
}

//float限幅
void float_constrain(float* Value, float minValue, float maxValue)
{
    if (*Value < minValue)
        *Value = minValue;
    else if (*Value > maxValue)
        *Value = maxValue;
}

//int16限幅
void int16_constrain(int16_t* Value, int16_t minValue, int16_t maxValue)
{
    if (*Value < minValue)
        *Value = minValue;
    else if (*Value > maxValue)
        *Value = maxValue;
}

//float循环限幅
float loop_float_constrain(float Input, float minValue, float maxValue)
{
    if (maxValue < minValue)
    {
        return Input;
    }

    if (Input > maxValue)
    {
        float len = maxValue - minValue;
        while (Input > maxValue)
        {
            Input -= len;
        }
    }
    else if (Input < minValue)
    {
        float len = maxValue - minValue;
        while (Input < minValue)
        {
            Input += len;
        }
    }
    return Input;
}

//int循环限幅
int loop_int_constrain(int Input, int minValue, int maxValue)
{
    if (maxValue < minValue)
    {
        return Input;
    }

    if (Input > maxValue)
    {
        float len = maxValue - minValue;
        while (Input > maxValue)
        {
            Input -= len;
        }
    }
    else if (Input < minValue)
    {
        float len = maxValue - minValue;
        while (Input < minValue)
        {
            Input += len;
        }
    }
    return Input;
}

//弧度归一 -PI~PI
float radian_format(float Rad)
{
		return loop_float_constrain(Rad, -PI, PI);
}
//角度归一 -180~180
float theta_format(float Ang)
{
    return loop_float_constrain(Ang, -180.0f, 180.0f);
}

int float_rounding(float raw)
{
    static int integer;
    static float decimal;
    integer = (int)raw;
    decimal = raw - integer;
    if (decimal > 0.5f)
        integer++;
    return integer;
}
/*------------------------------------------------------------------------------------- */

/*---------------------------------------一阶滤波--------------------------------------- */
/**
  * @brief          一阶低通滤波初始化
  * @author         RM
  * @param[in]      一阶低通滤波结构体
  * @param[in]      间隔的时间，单位 s
  * @param[in]      滤波参数
  * @retval         返回空
  */
void first_order_filter_init(first_order_filter_type_t *first_order_filter_type, fp32 frame_period, const fp32 num[1])
{
    first_order_filter_type->frame_period = frame_period;
    first_order_filter_type->num[0] = num[0];
    first_order_filter_type->input = 0.0f;
    first_order_filter_type->out = 0.0f;
}

/**
  * @brief          一阶低通滤波计算
  * @author         RM
  * @param[in]      一阶低通滤波结构体
  * @param[in]      间隔的时间，单位 s
  * @retval         返回空
  */
void first_order_filter_cali(first_order_filter_type_t *first_order_filter_type, fp32 input)
{
    first_order_filter_type->input = input;
    first_order_filter_type->out =
        first_order_filter_type->num[0] / (first_order_filter_type->num[0] + first_order_filter_type->frame_period) * first_order_filter_type->out + first_order_filter_type->frame_period / (first_order_filter_type->num[0] + first_order_filter_type->frame_period) * first_order_filter_type->input;
}
/*------------------------------------------------------------------------------------- */

/*---------------------------------------斜波函数--------------------------------------- */
/**
  * @brief          斜波函数初始化
  * @author         RM
  * @param[in]      ramp_source_type  斜波函数结构体指针
  * @param[in]      frame_period      帧周期，单位 s
  * @param[in]      max               最大值
  * @param[in]      min               最小值
  * @retval         空
  */
void ramp_init(ramp_function_source_t *ramp_source_type, float frame_period, float max, float min)
{
    ramp_source_type->frame_period = frame_period;
    ramp_source_type->max_value = max;
    ramp_source_type->min_value = min;
    ramp_source_type->input = 0.0f;
    ramp_source_type->out = 0.0f;
}

/**
  * @brief          斜波函数计算，输入值在最小值和最大值之间变化，输出值在最小值和最大值之间变化
  * @author         RM
  * @param[in]      ramp_source_type  斜波函数结构体指针
  * @param[in]      input             输入值
  * @retval         输出值
  */
float ramp_calc(ramp_function_source_t *ramp_source_type, float input)
{
    ramp_source_type->input = input;
    ramp_source_type->out += ramp_source_type->input * ramp_source_type->frame_period;
    if (ramp_source_type->out > ramp_source_type->max_value)
    {
        ramp_source_type->out = ramp_source_type->max_value;
    }
    else if (ramp_source_type->out < ramp_source_type->min_value)
    {
        ramp_source_type->out = ramp_source_type->min_value;
    }
    return ramp_source_type->out;
}
/*------------------------------------------------------------------------------------- */

/*--------------------------------------最小二乘法-------------------------------------- */
/**
  * @brief          获取最小二乘法的初始化
  * @param[in]      最小二乘法结构体
  * @param[in]      阶数
  * @retval         无
  */
void OLS_Init(Ordinary_Least_Squares_t *OLS, uint16_t order)
{
    OLS->Order = order;
    OLS->Count = 0;
    OLS->x = (float *)user_malloc(sizeof(float) * order);
    OLS->y = (float *)user_malloc(sizeof(float) * order);
    OLS->k = 0;
    OLS->b = 0;
    memset((void *)OLS->x, 0, sizeof(float) * order);
    memset((void *)OLS->y, 0, sizeof(float) * order);
    memset((void *)OLS->t, 0, sizeof(float) * 4);
}

/**
  * @brief          获取最小二乘法的导数
  * @param[in]      最小二乘法结构体
  * @param[in]      输入时间增量
  * @param[in]      输入值
  */
void OLS_Update(Ordinary_Least_Squares_t *OLS, float deltax, float y)
{
    static float temp = 0;
    temp = OLS->x[1];
    for (uint16_t i = 0; i < OLS->Order - 1; ++i)
    {
        OLS->x[i] = OLS->x[i + 1] - temp;
        OLS->y[i] = OLS->y[i + 1];
    }
    OLS->x[OLS->Order - 1] = OLS->x[OLS->Order - 2] + deltax;
    OLS->y[OLS->Order - 1] = y;

    if (OLS->Count < OLS->Order)
    {
        OLS->Count++;
    }
    memset((void *)OLS->t, 0, sizeof(float) * 4);
    for (uint16_t i = OLS->Order - OLS->Count; i < OLS->Order; ++i)
    {
        OLS->t[0] += OLS->x[i] * OLS->x[i];
        OLS->t[1] += OLS->x[i];
        OLS->t[2] += OLS->x[i] * OLS->y[i];
        OLS->t[3] += OLS->y[i];
    }

    OLS->k = (OLS->t[2] * OLS->Order - OLS->t[1] * OLS->t[3]) / (OLS->t[0] * OLS->Order - OLS->t[1] * OLS->t[1]);
    OLS->b = (OLS->t[0] * OLS->t[3] - OLS->t[1] * OLS->t[2]) / (OLS->t[0] * OLS->Order - OLS->t[1] * OLS->t[1]);

    OLS->StandardDeviation = 0;
    for (uint16_t i = OLS->Order - OLS->Count; i < OLS->Order; ++i)
    {
        OLS->StandardDeviation += fabsf(OLS->k * OLS->x[i] + OLS->b - OLS->y[i]);
    }
    OLS->StandardDeviation /= OLS->Order;
}

/**
  * @brief          获取最小二乘法的导数
  * @param[in]      最小二乘法结构体
  * @param[in]      输入时间增量
  * @param[in]      输入值
  * @retval         斜率k
  */
float OLS_Derivative(Ordinary_Least_Squares_t *OLS, float deltax, float y)
{
    static float temp = 0;
    temp = OLS->x[1];
    for (uint16_t i = 0; i < OLS->Order - 1; ++i)
    {
        OLS->x[i] = OLS->x[i + 1] - temp;
        OLS->y[i] = OLS->y[i + 1];
    }
    OLS->x[OLS->Order - 1] = OLS->x[OLS->Order - 2] + deltax;
    OLS->y[OLS->Order - 1] = y;

    if (OLS->Count < OLS->Order)
    {
        OLS->Count++;
    }

    memset((void *)OLS->t, 0, sizeof(float) * 4);
    for (uint16_t i = OLS->Order - OLS->Count; i < OLS->Order; ++i)
    {
        OLS->t[0] += OLS->x[i] * OLS->x[i];
        OLS->t[1] += OLS->x[i];
        OLS->t[2] += OLS->x[i] * OLS->y[i];
        OLS->t[3] += OLS->y[i];
    }

    OLS->k = (OLS->t[2] * OLS->Order - OLS->t[1] * OLS->t[3]) / (OLS->t[0] * OLS->Order - OLS->t[1] * OLS->t[1]);

    OLS->StandardDeviation = 0;
    for (uint16_t i = OLS->Order - OLS->Count; i < OLS->Order; ++i)
    {
        OLS->StandardDeviation += fabsf(OLS->k * OLS->x[i] + OLS->b - OLS->y[i]);
    }
    OLS->StandardDeviation /= OLS->Order;

    return OLS->k;
}

/**
  * @brief          获取最小二乘法的导数
  * @param[in]      最小二乘法结构体
  * @retval         斜率k
  */
float Get_OLS_Derivative(Ordinary_Least_Squares_t *OLS)
{
    return OLS->k;
}

/**
  * @brief          获取最小二乘法平滑后的值
  * @param[in]      最小二乘法结构体
  * @param[in]      输入时间增量
  * @param[in]      输入值
  * @retval         平滑后的值
  */
float OLS_Smooth(Ordinary_Least_Squares_t *OLS, float deltax, float y)
{
    static float temp = 0;
    temp = OLS->x[1];
    for (uint16_t i = 0; i < OLS->Order - 1; ++i)
    {
        OLS->x[i] = OLS->x[i + 1] - temp;
        OLS->y[i] = OLS->y[i + 1];
    }
    OLS->x[OLS->Order - 1] = OLS->x[OLS->Order - 2] + deltax;
    OLS->y[OLS->Order - 1] = y;

    if (OLS->Count < OLS->Order)
    {
        OLS->Count++;
    }

    memset((void *)OLS->t, 0, sizeof(float) * 4);
    for (uint16_t i = OLS->Order - OLS->Count; i < OLS->Order; ++i)
    {
        OLS->t[0] += OLS->x[i] * OLS->x[i];
        OLS->t[1] += OLS->x[i];
        OLS->t[2] += OLS->x[i] * OLS->y[i];
        OLS->t[3] += OLS->y[i];
    }

    OLS->k = (OLS->t[2] * OLS->Order - OLS->t[1] * OLS->t[3]) / (OLS->t[0] * OLS->Order - OLS->t[1] * OLS->t[1]);
    OLS->b = (OLS->t[0] * OLS->t[3] - OLS->t[1] * OLS->t[2]) / (OLS->t[0] * OLS->Order - OLS->t[1] * OLS->t[1]);

    OLS->StandardDeviation = 0;
    for (uint16_t i = OLS->Order - OLS->Count; i < OLS->Order; ++i)
    {
        OLS->StandardDeviation += fabsf(OLS->k * OLS->x[i] + OLS->b - OLS->y[i]);
    }
    OLS->StandardDeviation /= OLS->Order;

    return OLS->k * OLS->x[OLS->Order - 1] + OLS->b;
}

/**
  * @brief          获取最小二乘法平滑后的值
  * @param[in]      最小二乘法结构体
  * @retval         平滑后的值
  */
float Get_OLS_Smooth(Ordinary_Least_Squares_t *OLS)
{
    return OLS->k * OLS->x[OLS->Order - 1] + OLS->b;
}
