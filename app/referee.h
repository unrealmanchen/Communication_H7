//
// Created by chenrc on 2026/1/30.
//

#ifndef COMMUNICATION_H7_REFEREE_H
#define COMMUNICATION_H7_REFEREE_H


#ifndef ROBOMASTER_2026_PROTOCOL_H
#define ROBOMASTER_2026_PROTOCOL_H



#include <stdint.h>
#include <stdbool.h>
#include "main.h"
uint8_t Referee_data_decode(uint8_t* rx_data,int size);
// ==================== 通用帧结构 ====================
typedef __packed struct {
    uint8_t sof;          // 0xA5
    uint16_t data_length;
    uint8_t seq;
    uint8_t crc8;
} frame_header_t;

// ==================== 命令码枚举 ====================
typedef enum {
    // 常规链路命令码
    CMD_ID_GAME_STATUS            = 0x0001,
    CMD_ID_GAME_RESULT            = 0x0002,
    CMD_ID_GAME_ROBOT_HP          = 0x0003,
    CMD_ID_EVENT_DATA             = 0x0101,
    CMD_ID_REFEREE_WARNING        = 0x0104,
    CMD_ID_DART_INFO              = 0x0105,
    CMD_ID_ROBOT_PERFORMANCE      = 0x0201,
    CMD_ID_POWER_HEAT_DATA        = 0x0202,
    CMD_ID_ROBOT_POS              = 0x0203,
    CMD_ID_BUFF_DATA              = 0x0204,
    CMD_ID_HURT_DATA              = 0x0206,
    CMD_ID_SHOOT_DATA             = 0x0207,
    CMD_ID_PROJECTILE_ALLOWANCE   = 0x0208,
    CMD_ID_RFID_STATUS            = 0x0209,
    CMD_ID_DART_CLIENT_CMD        = 0x020A,
    CMD_ID_ROBOT_POS_EXT          = 0x020B,
    CMD_ID_MARK_PROGRESS          = 0x020C,
    CMD_ID_SENTRY_INFO            = 0x020D,
    CMD_ID_RADAR_INFO             = 0x020E,//?

    // 小地图交互相关
    CMD_ID_ROBOT_INTERACTION      = 0x0301,
    CMD_ID_CUSTOM_ROBOT_DATA      = 0x0302,//图传
    CMD_ID_MAP_COMMAND            = 0x0303,
    CMD_ID_REMOTE_CONTROL         = 0x0304,//图传
    CMD_ID_MAP_ROBOT_DATA         = 0x0305,
    CMD_ID_CUSTOM_CONTROLLER      = 0x0306,//？哨兵大概率用不到
    CMD_ID_MAP_DATA               = 0x0307,
    CMD_ID_CUSTOM_INFO            = 0x0308,
    CMD_ID_ROBOT_CUSTOM_DATA      = 0x0309,//图传
    CMD_ID_ROBOT_CUSTOM_DATA_2    = 0x0310,

    // 图传链路
    CMD_ID_SET_CHANNEL            = 0x0F01,//图传
    CMD_ID_QUERY_CHANNEL          = 0x0F02,//图传

} cmd_id_t;

// ==================== 数据结构体定义 ====================

// 1. 比赛状态数据 (0x0001)
typedef __packed struct {
    uint8_t game_type : 4;
    uint8_t game_progress : 4;
    uint16_t stage_remain_time;
    uint64_t SyncTimeStamp;
} game_status_t;

// 2. 比赛结果数据 (0x0002)
typedef __packed struct {
    uint8_t winner;
} game_result_t;

// 3. 机器人血量数据 (0x0003)
typedef __packed struct {
    uint16_t ally_1_robot_HP;
    uint16_t ally_2_robot_HP;
    uint16_t ally_3_robot_HP;
    uint16_t ally_4_robot_HP;
    uint16_t reserved;
    uint16_t ally_7_robot_HP;
    uint16_t ally_outpost_HP;
    uint16_t ally_base_HP;
} game_robot_HP_t;

// 4. 场地事件数据 (0x0101)
typedef __packed struct {
    uint32_t event_data;
} event_data_t;

// 5. 裁判警告数据 (0x0104)
typedef __packed struct {
    uint8_t level;
    uint8_t offending_robot_id;
    uint8_t count;
} referee_warning_t;

// 6. 飞镖发射数据 (0x0105)
typedef __packed struct {
    uint8_t dart_remaining_time;
    uint16_t dart_info;
} dart_info_t;

// 7. 机器人性能体系数据 (0x0201)
typedef __packed struct {
    uint8_t robot_id;
    uint8_t robot_level;
    uint16_t current_HP;
    uint16_t maximum_HP;
    uint16_t shooter_cooling_rate;
    uint16_t shooter_heat_limit;
    uint16_t chassis_power_limit;
    uint8_t power_management_gimbal_output : 1;
    uint8_t power_management_chassis_output : 1;
    uint8_t power_management_shooter_output : 1;
} robot_performance_t;

// 8. 实时底盘缓冲能量和射击热量数据 (0x0202)
typedef __packed struct {
    uint16_t reserved1;
    uint16_t reserved2;
    float reserved3;
    uint16_t buffer_energy;
    uint16_t shooter_17mm_1_barrel_heat;
    uint16_t shooter_42mm_barrel_heat;
} power_heat_data_t;

// 9. 机器人位置数据 (0x0203)
typedef __packed struct {
    float x;
    float y;
    float angle;
} robot_pos_t;

// 10. 增益和底盘能量数据 (0x0204)
typedef __packed struct {
    uint8_t hp_recovery_gain;
    uint16_t cooling_gain;
    uint8_t defense_gain;
    uint8_t negative_defense_gain;
    uint16_t attack_gain;
    uint8_t energy_feedback;
} buff_data_t;

// 11. 伤害状态数据 (0x0206)
typedef __packed struct {
    uint8_t armor_id : 4;
    uint8_t HP_deduction_reason : 4;
} hurt_data_t;

// 12. 弹丸发射数据 (0x0207)
typedef __packed struct {
    uint8_t bullet_type;
    uint8_t shooter_number;
    uint8_t launching_frequency;
    float initial_speed;
} shoot_data_t;

// 13. 弹丸允许发弹量数据 (0x0208)
typedef __packed struct {
    uint16_t projectile_allowance_17mm;
    uint16_t projectile_allowance_42mm;
    uint16_t remaining_gold;
    uint16_t fortress_projectile_allowance_17mm;
} projectile_allowance_t;

// 14. RFID状态数据 (0x0209)
typedef __packed struct {
    uint32_t rfid_status;
    uint8_t rfid_status_2;
} rfid_status_t;

// 15. 飞镖客户端指令数据 (0x020A)
typedef __packed struct {
    uint8_t dartlaunch_opening_status;
    uint8_t reserved;
    uint16_t target_change_time;
    uint16_t latestlaunch_cmd_time;
} dart_client_cmd_t;

// 16. 机器人位置扩展数据 (0x020B)
typedef __packed struct {
    float hero_x;
    float hero_y;
    float engineer_x;
    float engineer_y;
    float standard_3_x;
    float standard_3_y;
    float standard_4_x;
    float standard_4_y;
    float reserved1;
    float reserved2;
} robot_pos_ext_t;

// 17. 标记进度数据 (0x020C)
typedef __packed struct {
    uint16_t mark_info;
} mark_progress_t;

// 18. 哨兵信息数据 (0x020D)
typedef __packed struct {
    uint32_t sentry_info;
    uint16_t sentry_info_2;
} sentry_info_t;


// 20. 机器人交互数据头 (0x0301)
typedef __packed struct {
    uint16_t data_cmd_id;
    uint16_t sender_id;
    uint16_t receiver_id;
    uint8_t user_data[];
} robot_interaction_data_t;

// 21. 删除图层指令 (子内容ID: 0x0100)
typedef __packed struct {
    uint8_t delete_type;
    uint8_t layer;
} interaction_layer_delete_t;

// 22. 图形绘制指令 (子内容ID: 0x0101)
typedef __packed struct {
    uint8_t figure_name[3];
    uint32_t operate_type : 3;
    uint32_t figure_type : 3;
    uint32_t layer : 4;
    uint32_t color : 4;
    uint32_t details_a : 9;
    uint32_t details_b : 9;
    uint32_t width : 10;
    uint32_t start_x : 11;
    uint32_t start_y : 11;
    uint32_t details_c : 10;
    uint32_t details_d : 11;
    uint32_t details_e : 11;
} interaction_figure_t;

// 23. 多个图形绘制结构体
typedef __packed struct {
    interaction_figure_t figure1;
    interaction_figure_t figure2;
} interaction_figure_2_t;

typedef __packed struct {
    interaction_figure_t figure[5];
} interaction_figure_3_t;

typedef __packed struct {
    interaction_figure_t figure[7];
} interaction_figure_4_t;

// 24. 自定义字符图形 (子内容ID: 0x0110)
typedef __packed struct {
    interaction_figure_t graphic_data_struct;
    uint8_t data[30];
} ext_client_custom_character_t;

// 25. 哨兵自主决策指令 (子内容ID: 0x0120)
typedef __packed struct {
    uint32_t sentry_cmd;
} sentry_cmd_t;

// 26. 雷达自主决策指令 (子内容ID: 0x0121)
typedef __packed struct {
    uint8_t radar_trigger;
    uint8_t key[7];
} radar_cmd_t;

// 27. 小地图指令数据 (0x0303)
typedef __packed struct {
    float target_position_x;
    float target_position_y;
    uint8_t cmd_keyboard;
    uint8_t target_robot_id;
    uint16_t cmd_source;
} map_command_t;

// 28. 小地图机器人位置数据 (0x0305)
typedef __packed struct {
    uint16_t hero_position_x;
    uint16_t hero_position_y;
    uint16_t engineer_position_x;
    uint16_t engineer_position_y;
    uint16_t infantry_3_position_x;
    uint16_t infantry_3_position_y;
    uint16_t infantry_4_position_x;
    uint16_t infantry_4_position_y;
    uint16_t infantry_5_position_x;
    uint16_t infantry_5_position_y;
    uint16_t sentry_position_x;
    uint16_t sentry_position_y;
} map_robot_data_t;

// 29. 路径规划数据 (0x0307)
typedef __packed struct {
    uint8_t intention;
    uint16_t start_position_x;
    uint16_t start_position_y;
    int8_t delta_x[49];
    int8_t delta_y[49];
    uint16_t sender_id;
} map_data_t;

// 30. 自定义消息数据 (0x0308)
typedef __packed struct {
    uint16_t sender_id;
    uint16_t receiver_id;
    uint8_t user_data[30];
} custom_info_t;

// 31. 自定义控制器数据 (0x0302, 0x0309, 0x0310)
typedef __packed struct {
    uint8_t data[30];
} custom_robot_data_t;

typedef __packed struct {
    uint8_t data[30];
} robot_custom_data_t;

typedef __packed struct {
    uint8_t data[150];
} robot_custom_data_2_t;

// 32. 键鼠遥控数据 (0x0304)
typedef __packed struct {
    int16_t mouse_x;
    int16_t mouse_y;
    int16_t mouse_z;
    uint8_t left_button_down;
    uint8_t right_button_down;
    uint16_t keyboard_value;
    uint16_t reserved;
} remote_control_t;

// 33. 自定义控制器模拟键鼠数据 (0x0306)
typedef __packed struct {
    uint16_t key_value;
    uint16_t x_position : 12;
    uint16_t mouse_left : 4;
    uint16_t y_position : 12;
    uint16_t mouse_right : 4;
    uint16_t reserved;
} custom_controller_data_t;


// 35. 图传信道设置 (0x0F01, 0x0F02)
typedef __packed struct {
    uint8_t channel;
} channel_setting_t;


typedef struct{
    game_status_t game_status;
    game_result_t game_result;
    game_robot_HP_t game_robot_hp;
    event_data_t event_data;
    referee_warning_t referee_warning;
    dart_info_t dart_info;
    robot_performance_t robot_performance;
    power_heat_data_t power_heat_data;
    robot_pos_t robot_pos;
    buff_data_t buff_data;
    hurt_data_t hurt_data;
    shoot_data_t shoot_data;
    projectile_allowance_t projectile_allowance;
    rfid_status_t rfid_status;
    dart_client_cmd_t dart_client_cmd;
    robot_pos_ext_t robot_pos_ext;
    mark_progress_t mark_progress;
    sentry_info_t sentry_info;

}referee_data_t;
#endif // ROBOMASTER_2026_PROTOCOL_H
#endif //COMMUNICATION_H7_REFEREE_H