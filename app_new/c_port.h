#ifndef RING_BUFFER_C_H
#define RING_BUFFER_C_H

#include <stdint.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

// 定义一个不透明的句柄（C 语言中看不到内部结构）
typedef struct RingBufferC_t RingBufferC_t;

// ----- 以下是给 C 语言调用的接口 -----

// 创建一个指定容量的缓冲区（内部会 new 一个 C++ 的 RingBuffer 对象）
RingBufferC_t* rb_c_create(uint32_t capacity);

// 写入一个字节（成功返回 true，满返回 false）
bool rb_c_push(RingBufferC_t* rb, uint8_t data);

// 读出一个字节（成功返回 true，空返回 false）
bool rb_c_pop(RingBufferC_t* rb, uint8_t* data);

// 获取当前数据量
uint32_t rb_c_size(RingBufferC_t* rb);

// 销毁缓冲区（内部 delete 掉 C++ 对象）
void rb_c_destroy(RingBufferC_t* rb);

#ifdef __cplusplus
}
#endif

#endif // RING_BUFFER_C_H