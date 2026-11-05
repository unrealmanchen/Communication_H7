#ifndef RING_BUFFER_C_H
#define RING_BUFFER_C_H

#include <stdint.h>
#include <stdbool.h>

typedef struct RingBufferC_u8_t_ RingBufferC_u8_t;

RingBufferC_u8_t *rb_c_create(uint32_t capacity);
void rb_c_destroy(RingBufferC_u8_t *rb);

/* 基本操作（对应 push / pop / size / capacity / empty / full / clear） */
bool rb_c_push(RingBufferC_u8_t *rb, uint8_t item);
bool rb_c_pop(RingBufferC_u8_t *rb, uint8_t *item);
uint32_t rb_c_size(RingBufferC_u8_t *rb);
uint32_t rb_c_capacity(RingBufferC_u8_t *rb);
bool rb_c_empty(RingBufferC_u8_t *rb);
bool rb_c_full(RingBufferC_u8_t *rb);
void rb_c_clear(RingBufferC_u8_t *rb);

#endif // RING_BUFFER_C_H
