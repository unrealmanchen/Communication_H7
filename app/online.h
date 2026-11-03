#ifndef DISCONNECT_H
#define DISCONNECT_H




void OnlineTask(void const *argument);

typedef enum{
    ONLINE_TIMER = -1,
    UPC = 0 ,
    BIG_GIMBAL_IMU,
    CHASSIS_CB,
    GIMBAL_CB,
    REFEREE, //
    SMALL_GIMBAL_IMU,
    CHASSIS_MOTOR_0,
    CHASSIS_MOTOR_1,
    CHASSIS_MOTOR_2,
    CHASSIS_MOTOR_3,
    CHASSIS_9025,
    GIMBAL_MOTOR_1,
    GIMBAL_MOTOR_2,
    GIMBAL_6020_1,
    GIMBAL_6020_2
    
} OnlineID;
void OnlineStatusUpdate(OnlineID type) ;
void online_init(void);
#endif
