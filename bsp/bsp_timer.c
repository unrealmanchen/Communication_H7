#include "tim.h"
#include "bsp_timer.h"
#include "string.h"
#include "online.h"
TIMER_STRUCT TIM6_100us;
TIMER_STRUCT TIM7_10ms;
long long htim6_DEBUG_counter =0;
void Timer_Init()
{
  // HAL_TIM_Base_Start_IT(&htim5);
  // TIM5_100us.Timer_num = TIMER_5_NUM;

  HAL_TIM_Base_Start_IT(&htim6);
  // TIM6_100us.Timer_num = TIMER_6_NUM;
  //
  HAL_TIM_Base_Start_IT(&htim7);
  TIM7_10ms.Timer_num = TIMER_7_NUM;
}


float Timer_Cauculate_dT(TIMER_STRUCT *timer, int num)
{
  float dT;

  if (timer->Counter[num] < timer->lastUpdate[num])
  {
      dT = ((float)(timer->Counter[num] + (0xffff - timer->lastUpdate[num])) / 10000.0f);
  }
  else
  {
    dT = ((float)(timer->Counter[num] - timer->lastUpdate[num]) / 10000.0f);
  }

  timer->lastUpdate[num] = timer->Counter[num];

  return dT;
}

void HAL_TIM_PeriodElapsedCallback(TIM_HandleTypeDef *htim)
{
  if(htim->Instance == TIM7){

  }

}