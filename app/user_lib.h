#ifndef _USER_LIB_H
#define _USER_LIB_H
#include "typedef.h"
#include "cmsis_os.h"
#include "bsp_uart.h"
#ifndef user_malloc
#ifdef _CMSIS_OS_H
#define user_malloc pvPortMalloc
#else
#define user_malloc malloc
#endif
#endif

/* boolean type definitions */
#ifndef TRUE
#define TRUE 1 /**< boolean true  */
#endif

#ifndef FALSE
#define FALSE 0 /**< boolean fails */
#endif

/* math relevant */
/* radian coefficient */
#ifndef RADIAN_COEF
#define RADIAN_COEF 57.295779513f
#endif

/* circumference ratio */
#ifndef PI
#define PI 3.14159265354f
#endif

#define VAL_LIMIT(val, min, max) \
    do                           \
    {                            \
        if ((val) <= (min))      \
        {                        \
            (val) = (min);       \
        }                        \
        else if ((val) >= (max)) \
        {                        \
            (val) = (max);       \
        }                        \
    } while (0)

#define ANGLE_LIMIT_360(val, angle)     \
    do                                  \
    {                                   \
        (val) = (angle) - (int)(angle); \
        (val) += (int)(angle) % 360;    \
    } while (0)

#define ANGLE_LIMIT_360_TO_180(val) \
    do                              \
    {                               \
        if ((val) > 180)            \
            (val) -= 360;           \
    } while (0)

#define VAL_MIN(a, b) ((a) < (b) ? (a) : (b))
#define VAL_MAX(a, b) ((a) > (b) ? (a) : (b))

// 设置变量的第n位（n从0开始，0是最低位）
#define SET_BIT(x, n)       ((x) |=  (1U << (n)))

// 清除变量的第n位
#define CLEAR_BIT(x, n)     ((x) &= ~(1U << (n)))

// 翻转变量的第n位
#define TOGGLE_BIT(x, n)    ((x) ^=  (1U << (n)))

// 获取变量的第n位值（返回0或1）
#define GET_BIT(x, n)       (((x) >> (n)) & 1U)

// 检查变量的第n位是否为1
#define IS_BIT_SET(x, n)    (((x) >> (n)) & 1U)

// 检查变量的第n位是否为0
#define IS_BIT_CLEAR(x, n)  (!(((x) >> (n)) & 1U))

// 设置变量的第n位为指定值（val必须为0或1）
#define ASSIGN_BIT(x, n, val) do { \
    (x) = ((x) & ~(1U << (n))) | (((val) & 1U) << (n)); \
} while(0)
typedef struct
{
    float input;        //输入值
    float out;          //输出值
    float min_value;    //输出最小值
    float max_value;    //输出最大值
    float frame_period; //时间周期
} ramp_function_source_t;

typedef __packed struct
{
    uint16_t Order;
    uint32_t Count;

    float *x;
    float *y;

    float k;
    float b;

    float StandardDeviation;

    float t[4];
} Ordinary_Least_Squares_t;

typedef __packed struct
{
    fp32 input;        //输入数据
    fp32 out;          //滤波输出的数据
    fp32 num[1];       //滤波参数
    fp32 frame_period; //滤波的时间间隔 单位 s
} first_order_filter_type_t;

float q_sqrt(float x);

void ramp_init(ramp_function_source_t *ramp_source_type, float frame_period, float max, float min);
float ramp_calc(ramp_function_source_t *ramp_source_type, float input);

float abs_limit(float num, float Limit);
float sign(float value);
float float_deadband(float Value, float minValue, float maxValue);
int16_t int16_deadband(int16_t Value, int16_t minValue, int16_t maxValue);
void float_constrain(float* Value, float minValue, float maxValue);
void int16_constrain(int16_t* Value, int16_t minValue, int16_t maxValue);
float loop_float_constrain(float Input, float minValue, float maxValue);
int loop_int_constrain(int Input, int minValue, int maxValue);
float radian_format(float Rad);
float theta_format(float Ang);
int float_rounding(float raw);

#define rad_format(Ang) loop_float_constrain((Ang), -PI, PI)

void first_order_filter_init(first_order_filter_type_t *first_order_filter_type, fp32 frame_period, const fp32 num[1]);
void first_order_filter_cali(first_order_filter_type_t *first_order_filter_type, fp32 input);

void OLS_Init(Ordinary_Least_Squares_t *OLS, uint16_t order);
void OLS_Update(Ordinary_Least_Squares_t *OLS, float deltax, float y);
float OLS_Derivative(Ordinary_Least_Squares_t *OLS, float deltax, float y);
float OLS_Smooth(Ordinary_Least_Squares_t *OLS, float deltax, float y);
float Get_OLS_Derivative(Ordinary_Least_Squares_t *OLS);
float Get_OLS_Smooth(Ordinary_Least_Squares_t *OLS);

void unpack_4bytes_to_floats(const uint8_t data[4], float* f1);
void pack_float_to_4bytes(float f1, uint8_t data[4]);

void CMD_PackPacket(char *data_in, uint16_t data_len, uint16_t cmd_id, uint8_t *data_out);
void CMD_Transmit(char *data_in, uint16_t data_len, uint16_t cmd_id, UART_STRUCT *uart);
#endif
