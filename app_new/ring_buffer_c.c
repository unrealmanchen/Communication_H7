#include "ring_buffer_c.h"
#include "FreeRTOS.h" 
#include <stddef.h>

struct RingBufferC_u8_t_
{
    uint8_t *buffer;
    uint32_t buffer_size;
    uint32_t head;
    uint32_t tail; 
};

RingBufferC_u8_t *rb_c_create(uint32_t capacity)
{
    uint32_t cap1 = capacity + 1;

    if (capacity == 0)
        return NULL;

    RingBufferC_u8_t *rb = (RingBufferC_u8_t *)pvPortMalloc(sizeof(RingBufferC_u8_t));
    if (!rb)
        return NULL;

    rb->buffer = (uint8_t *)pvPortMalloc(sizeof(uint8_t) * cap1);
    if (!rb->buffer)
    {
        vPortFree(rb);
        return NULL;
    }

    rb->buffer_size = cap1;
    rb->head = 0;
    rb->tail = 0;
    return rb;
}

void rb_c_destroy(RingBufferC_u8_t *rb)
{
    if (!rb)
        return;
    vPortFree(rb->buffer);
    vPortFree(rb);
}


bool rb_c_push(RingBufferC_u8_t *rb, uint8_t item)
{
    if (!rb)
        return false;

    uint32_t next_head = (rb->head + 1) % rb->buffer_size;
    if (next_head == rb->tail)
        return false;


    rb->buffer[rb->head] = item;
    rb->head = next_head;
    return true;
}


bool rb_c_pop(RingBufferC_u8_t *rb, uint8_t *item)
{
    if (!rb || !item)
        return false;


    if (rb->head == rb->tail)
    {
        return false;
    }

    *item = rb->buffer[rb->tail];
    rb->tail = (rb->tail + 1) % rb->buffer_size;
    return true;
}


uint32_t rb_c_size(RingBufferC_u8_t *rb)
{
    if (!rb)
        return 0;

    if (rb->head >= rb->tail)
    {
        return rb->head - rb->tail;
    }
    else
    {
        return rb->buffer_size - rb->tail + rb->head;
    }
}


uint32_t rb_c_capacity(RingBufferC_u8_t *rb)
{
    if (!rb)
        return 0;
    return rb->buffer_size - 1;
}


bool rb_c_empty(RingBufferC_u8_t *rb)
{
    if (!rb)
        return true;
    return rb->head == rb->tail;
}


bool rb_c_full(RingBufferC_u8_t *rb)
{
    if (!rb)
        return false;
    return (rb->head + 1) % rb->buffer_size == rb->tail;
}


void rb_c_clear(RingBufferC_u8_t *rb)
{
    if (!rb)
        return false;
    rb->head = 0;
    rb->tail = 0;
}

