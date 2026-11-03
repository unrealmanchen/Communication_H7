#ifndef TIMER
#define TIMER

#define TIMER_MAX_NUM 20

///////////////
#define TIMER_6_NUM 2
#define TIMER_7_NUM 6

#define IMU_COUNTER 0
#define PITCH_6020 1
///////////////
typedef struct TIMER__
{
  int Counter[TIMER_MAX_NUM];
  int lastUpdate[TIMER_MAX_NUM];
  int Timer_num;
}TIMER_STRUCT;

extern long long htim6_DEBUG_counter;
void Timer_Init(void);
float Timer_Cauculate_dT(TIMER_STRUCT * timer,int num);

extern TIMER_STRUCT TIM6_100us;
extern TIMER_STRUCT TIM7_10ms;
#endif
