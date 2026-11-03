//
// Created by chenrc on 2026/2/12.
//
#include "terminal.h"

#include <stdlib.h>

#include "string.h"
#include "stdio.h"
#include "cmsis_os.h"
#include "main.h"
#include "usart.h"
#include "bsp_uart.h"
int help(char *a);
int debug(char *a);
int exit_a(char *a);

void terminal_process_char(uint8_t ch);
static void terminal_redraw_line(void);
static void terminal_insert_char(char ch);
static void terminal_backspace(void);
static void terminal_move_left(void);
static void terminal_move_right(void);
static void terminal_execute_command(void);

static void TerminalTask(void *argument);

typedef struct __COMMAND
{
    char name[20];
    int (*function)(char *);
    char description[50];
} Struct_command;

Struct_command command_list[20] = {
    "help", help, "help - show command list",
    "debug", debug, "debug - show rtos-debug info",
    "exit", exit_a, "exit - exit rtos-debug info"};
const int command_list_length = 3;

int debug(char *a)
{
    int len = -100;
    uint8_t *msg_ptr = osPoolCAlloc(Terminal_Pool_Hdle);
    if (!msg_ptr)
        return;

    msg_ptr[0] = len & 0xFF;
    msg_ptr[1] = (len >> 8) & 0xFF;

    if (osMessagePut(Terminal_RX_Queue_Hdle, (uint32_t)msg_ptr, 0) != osOK)
    {
        osPoolFree(Terminal_Pool_Hdle, msg_ptr);
        return;
    }
    else
    {
        UART_Tx(&UART_1, (uint8_t *)"\033[2J\033[H", 7);
    }

    return;
}

int exit_a(char *a)
{
    int len = -200;
    uint8_t *msg_ptr = osPoolCAlloc(Terminal_Pool_Hdle);
    if (!msg_ptr)
        return;

    msg_ptr[0] = len & 0xFF;
    msg_ptr[1] = (len >> 8) & 0xFF;

    if (osMessagePut(Terminal_RX_Queue_Hdle, (uint32_t)msg_ptr, 0) != osOK)
    {
        osPoolFree(Terminal_Pool_Hdle, msg_ptr);
        return;
    }

    return;
}

int help(char *a)
{
    char buffer[55];
    sprintf(buffer, "\r\nAvailable Command : \n\n\r");
    UART_Tx(&UART_1, buffer, strlen(buffer));
    for (int i = 0; i < command_list_length; i++)
    {
        sprintf(buffer, "%s\n\r", command_list[i].description);
        UART_Tx(&UART_1, buffer, strlen(buffer));
    }
}

int led(char *arg1)
{
    int times = 0;
    char *arg[4] = {arg1, 0, 0, 0};
    int argint[3] = {0, 0, 0};
    arg[1] = strtok(NULL, " ");
    arg[2] = strtok(NULL, " ");
    if (strtok(NULL, " ") != NULL)
    {
        HAL_UART_Transmit(&huart1, "\n\rError: too many arg", strlen("\r\nError: too many arg"), 0xff);
        return 1;
    }
    for (int i = 0; i < 3; i++)
    {
        if (arg[i] == NULL)
        {
            HAL_UART_Transmit(&huart1, "\n\rError: missing arg", strlen("\r\nError: missing arg"), 0xff);
            return 1;
        }
        sscanf(arg[i], "%d", &argint[i]);
        if (argint[i] != 1 && argint[i] != 0)
        {
            HAL_UART_Transmit(&huart1, "\n\rError: wrong arg, it should be 0 or 1", strlen("\n\rError: wrong arg, it should be 0 or 1"), 0xff);
            return 1;
        }
    }
    // sendcommand(argint[1],argint[0],argint[2]);
    HAL_UART_Transmit(&huart1, "\r\nFinishi!", strlen("\r\nFinishi!"), 0xff);
}

void operation(char *buffercommand)
{
    char buffer[50];
    if (strlen(buffercommand) == 0)
    {
        return;
    }
    char *command = strtok(buffercommand, " ");
    char *arg = strtok(NULL, " ");
    int find_ = 0;
    for (int i = 0; i < command_list_length; i++)
    {
        if (strcmp(command_list[i].name, command) == 0)
        {
            find_ = 1;
            command_list[i].function(arg);
        }
    }
    if (find_ != 1)
    {
        sprintf(buffer, "\"%s\" Command not find\r\n", command);
        UART_Tx(&UART_1, buffer, strlen(buffer));
    }
}

//
// Created by chenrc on 2026/2/12.
//

// 终端配置
#define TERMINAL_BUFFER_SIZE 128
#define TERMINAL_PROMPT "[RM Sentry] $ "
#define TERMINAL_PROMPT_LEN (sizeof(TERMINAL_PROMPT) - 1)

#define TERMINAL_STARTUP "Sentry Communication System Ready\r\n"
#define STARTUP_PROMPT_LEN (sizeof(TERMINAL_STARTUP) - 1)

// ANSI光标控制序列
#define ANSI_CURSOR_HIDE "\033[?25l"  // 隐藏光标
#define ANSI_CURSOR_SHOW "\033[?25h"  // 显示光标
#define ANSI_CURSOR_SAVE "\033[s"     // 保存光标位置
#define ANSI_CURSOR_RESTORE "\033[u"  // 恢复光标位置
#define ANSI_CLEAR_LINE "\033[K"      // 清除行尾
#define ANSI_CURSOR_SET "\033[%d;%dH" // 设置光标位置

typedef enum
{
    CURSOR_ON,
    CURSOR_OFF
} cursor_state_t;

// 终端状态机
typedef enum
{
    TERM_STATE_NORMAL,
    TERM_STATE_ESC,
    TERM_STATE_BRACKET,
} terminal_state_t;

char terminal_buffer[TERMINAL_BUFFER_SIZE];
uint8_t buffer_len = 0;
uint8_t cursor_pos = 0;
terminal_state_t term_state = TERM_STATE_NORMAL;
static cursor_state_t cursor_state = CURSOR_ON;
static uint8_t cursor_blink_enabled = 1;

osThreadId Terminal_Task_hdle;
osMessageQId Terminal_RX_Queue_Hdle;
osPoolId Terminal_Pool_Hdle;
#define UART_RX_QUEUE_SIZE 64

// 函数声明

static void TerminalTask(void *argument);
void terminal_init(void)
{
    buffer_len = 0;
    cursor_pos = 0;
    term_state = TERM_STATE_NORMAL;
    cursor_state = CURSOR_ON;
    terminal_buffer[0] = '\0';

    osThreadDef(Terminal_Task, TerminalTask, osPriorityLow, 0, 128);
    Terminal_Task_hdle = osThreadCreate(osThread(Terminal_Task), NULL);

    osMessageQDef(Terminal_Q, 6, uint32_t);
    Terminal_RX_Queue_Hdle = osMessageCreate(osMessageQ(Terminal_Q), NULL);

    osPoolDef(VarPool, 6, uint8_t[32]);
    Terminal_Pool_Hdle = osPoolCreate(osPool(VarPool));
}

/**
 * @brief 终端处理主任务
 */
static char CPU_RunInfo[256];
static void TerminalTask(void *argument)
{
    osEvent evt;
    UART_Tx(&UART_1, (uint8_t *)"\033[2J\033[H", 7);
    UART_Tx(&UART_1, (uint8_t *)ANSI_CURSOR_SHOW, strlen(ANSI_CURSOR_SHOW));
    UART_Tx(&UART_1, (uint8_t *)"\r\n", 2);
    UART_Tx(&UART_1, (uint8_t *)TERMINAL_STARTUP, STARTUP_PROMPT_LEN);
    UART_Tx(&UART_1, (uint8_t *)TERMINAL_PROMPT, TERMINAL_PROMPT_LEN);

    for (;;)
    { // 非持续显示模式
    TER_NORMAL:
        evt = osMessageGet(Terminal_RX_Queue_Hdle, osWaitForever);
        if (evt.status != osEventMessage)
            continue;

        uint8_t *block = (uint8_t *)evt.value.p;
        int16_t len = block[0] | (block[1] << 8);
        uint8_t *data = block + 2;

        if (len == -100 || len == -200)
        {
            osPoolFree(Terminal_Pool_Hdle, block);
            if (len == -100)
                goto TER_SCREEN;
        }
        // 处理数据
        int i = -1;
        while (++i < len)
        {
            terminal_process_char(data[i]);
        }

        osPoolFree(Terminal_Pool_Hdle, block);
    }
    for (;;)
    { // 持续显示模式
    TER_SCREEN:

        evt = osMessageGet(Terminal_RX_Queue_Hdle, 0);
        if (evt.status == osEventMessage)
        {
            uint8_t *block = (uint8_t *)evt.value.p;
            int16_t len = block[0] | (block[1] << 8);
            uint8_t *data = block + 2;

            if (len == -200)
            {
                osPoolFree(Terminal_Pool_Hdle, block);
                UART_Tx(&UART_1, (uint8_t *)"\033[D", 3);
                terminal_redraw_line();
                goto TER_NORMAL;
            }
            if(len == 1){
                if(*data == 3){
                    UART_Tx(&UART_1, (uint8_t *)"\033[2J\033[H", 7);
                    terminal_redraw_line();
                    goto TER_NORMAL;
                }
            }
            osPoolFree(Terminal_Pool_Hdle, block);
        }
        UART_Tx(&UART_1, (uint8_t *)"\033[2J\033[H", 7);
        memset(CPU_RunInfo, 0, 512);
        vTaskList((char *)&CPU_RunInfo);

        UART_Tx(&UART_1, "---------------------------------------------\r\n",
                strlen("---------------------------------------------\r\n")); // 获取任务运行时间信息

        UART_Tx(&UART_1, "任务名       任务状态     优先级     剩余栈     任务序号\r\n",
                strlen("任务名       任务状态     优先级     剩余栈     任务序号\r\n"));

        UART_Tx(&UART_1, CPU_RunInfo, strlen(CPU_RunInfo));

        memset(CPU_RunInfo, 0, 512);
        vTaskGetRunTimeStats((char *)&CPU_RunInfo);
        UART_Tx(&UART_1, "任务名         运行计数     使用率 \r\n",
                strlen("任务名         运行计数     使用率 \r\n"));

        UART_Tx(&UART_1, CPU_RunInfo, strlen(CPU_RunInfo));
        osDelay(400);
    }
}

void Transmit_data2Terminal(char *data, int len)
{

    uint8_t *msg_ptr = osPoolCAlloc(Terminal_Pool_Hdle);
    if (!msg_ptr)
        return;

    msg_ptr[0] = len & 0xFF;
    msg_ptr[1] = (len >> 8) & 0xFF;
    memcpy(msg_ptr + 2, data, len);

    if (osMessagePut(Terminal_RX_Queue_Hdle, (uint32_t)msg_ptr, 0) != osOK)
    {
        osPoolFree(Terminal_Pool_Hdle, msg_ptr);
        return;
    }

    return;
}

#define MAX_DISPLAY_SIZE 128
uint8_t display_buffer[MAX_DISPLAY_SIZE];
uint16_t buffer_index = 0;

static void terminal_redraw_line(void)
{

    buffer_index = 0;

    // 光标保存命令
    memcpy(&display_buffer[buffer_index], ANSI_CURSOR_SAVE, strlen(ANSI_CURSOR_SAVE));
    buffer_index += strlen(ANSI_CURSOR_SAVE);

    // 回车
    display_buffer[buffer_index++] = '\r';

    memcpy(&display_buffer[buffer_index], TERMINAL_PROMPT, TERMINAL_PROMPT_LEN);
    buffer_index += TERMINAL_PROMPT_LEN;

    // 缓冲区
    if (buffer_len > 0)
    {
        memcpy(&display_buffer[buffer_index], terminal_buffer, buffer_len);
        buffer_index += buffer_len;
    }

    // 清行命令
    memcpy(&display_buffer[buffer_index], ANSI_CLEAR_LINE, strlen(ANSI_CLEAR_LINE));
    buffer_index += strlen(ANSI_CLEAR_LINE);

    // 光标恢复命令
    memcpy(&display_buffer[buffer_index], ANSI_CURSOR_RESTORE, strlen(ANSI_CURSOR_RESTORE));
    buffer_index += strlen(ANSI_CURSOR_RESTORE);

    UART_Tx(&UART_1, display_buffer, buffer_index);
}

static void terminal_insert_char(char ch)
{
    if (buffer_len < TERMINAL_BUFFER_SIZE - 1)
    {
        // 将光标后的字符后移
        for (int i = buffer_len; i > cursor_pos; i--)
        {
            terminal_buffer[i] = terminal_buffer[i - 1];
        }

        terminal_buffer[cursor_pos] = ch;
        buffer_len++;
        cursor_pos++;

        UART_Tx(&UART_1, (uint8_t *)"\033[C", 3);
        terminal_redraw_line();
    }
}

static void terminal_backspace(void)
{
    if (cursor_pos > 0)
    {
        // 将光标后的字符前移
        for (int i = cursor_pos - 1; i < buffer_len - 1; i++)
        {
            terminal_buffer[i] = terminal_buffer[i + 1];
        }

        buffer_len--;
        cursor_pos--;
        terminal_buffer[buffer_len] = '\0';

        // 重新绘制整行
        UART_Tx(&UART_1, (uint8_t *)"\033[D", 3);
        terminal_redraw_line();
    }
}

static void terminal_move_left(void)
{
    if (cursor_pos > 0)
    {
        cursor_pos--;
        UART_Tx(&UART_1, (uint8_t *)"\033[D", 3);
    }
}

static void terminal_move_right(void)
{
    if (cursor_pos < buffer_len)
    {
        cursor_pos++;
        UART_Tx(&UART_1, (uint8_t *)"\033[C", 3);
    }
}

/**
 * @brief 执行命令
 */
static void terminal_execute_command(void)
{
    terminal_buffer[buffer_len] = '\0';
    UART_Tx(&UART_1, (uint8_t *)"\r\n", 2);

    operation(terminal_buffer);

    buffer_len = 0;
    cursor_pos = 0;
    terminal_buffer[0] = '\0';

    UART_Tx(&UART_1, (uint8_t *)TERMINAL_PROMPT,
            TERMINAL_PROMPT_LEN);
}

void terminal_process_char(uint8_t ch)
{
    switch (term_state)
    {
    case TERM_STATE_NORMAL:
        if (ch == 3){
            exit_a(0);//??????
        }
        if (ch == 0x1B)
        {
            term_state = TERM_STATE_ESC;
            return;
        }
        else if (ch == '\r' || ch == '\n')
        {
            terminal_execute_command();
        }
        else if (ch == 0x7F || ch == 0x08)
        {
            terminal_backspace();
        }
        else if (ch >= 0x20 && ch <= 0x7E)
        {
            terminal_insert_char((char)ch);
        }
        break;

    case TERM_STATE_ESC:
        if (ch == '[')
        {
            term_state = TERM_STATE_BRACKET;
        }
        else
        {
            term_state = TERM_STATE_NORMAL;
        }
        break;

    case TERM_STATE_BRACKET:
        switch (ch)
        {
        case 'C': // 右方向键
            terminal_move_right();
            break;
        case 'D': // 左方向键
            terminal_move_left();
            break;
        case 'A': // 上方向键
        case 'B': // 下方向键
            break;
        }
        term_state = TERM_STATE_NORMAL;
        break;
    }
}

void terminal_clear_screen(void)
{
    UART_Tx(&UART_1, (uint8_t *)"\033[2J\033[H", 7);
    UART_Tx(&UART_1, (uint8_t *)TERMINAL_PROMPT,
            TERMINAL_PROMPT_LEN);
}
