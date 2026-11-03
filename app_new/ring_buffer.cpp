#include "ring_buffer.hpp"
#include "main.h"

template <typename T>
RingBuffer<T>::RingBuffer(size_t capacity) 
    : buffer_(capacity + 1), head_(0), tail_(0) {
    // +1 是为了在 head 和 tail 之间留一个空位，以便区分“队空”和“队满”
    if (capacity == 0) {
        __breakpoint();

    }
}

// 写入数据
template <typename T>
bool RingBuffer<T>::push(const T& item) {
    size_t next_head = (head_ + 1) % buffer_.size();
    
    // 溢出异常判断：如果下一个位置等于读指针，说明已满
    if (next_head == tail_) {
        return false; 
    }
    
    buffer_[head_] = item;
    head_ = next_head;
    return true;
}

// 读出数据
template <typename T>
bool RingBuffer<T>::pop(T& item) {
    // 异常判断：读写指针相等说明缓冲区为空
    if (head_ == tail_) {
        return false; 
    }
    
    item = buffer_[tail_];
    tail_ = (tail_ + 1) % buffer_.size();
    return true;
}

template <typename T>
size_t RingBuffer<T>::size() const {
    if (head_ >= tail_) {
        return head_ - tail_;
    } else {
        return buffer_.size() - tail_ + head_;
    }
}


template <typename T>
size_t RingBuffer<T>::capacity() const { 
    return buffer_.size() - 1; 
}


template <typename T>
bool RingBuffer<T>::empty() const { 
    return head_ == tail_; 
}

// 判断是否已满
template <typename T>
bool RingBuffer<T>::full() const { 
    return (head_ + 1) % buffer_.size() == tail_; 
}

// 清空缓冲区
template <typename T>
void RingBuffer<T>::clear() { 
    head_ = 0; 
    tail_ = 0; 
}

// ================= 迭代器实现 =================

template <typename T>
RingBuffer<T>::iterator::iterator(RingBuffer<T>& rb, size_t pos) 
    : rb_(rb), pos_(pos) {}

template <typename T>
T& RingBuffer<T>::iterator::operator*() { 
    return rb_.buffer_[pos_]; 
}

template <typename T>
typename RingBuffer<T>::iterator& RingBuffer<T>::iterator::operator++() {
    pos_ = (pos_ + 1) % rb_.buffer_.size();
    return *this;
}

template <typename T>
bool RingBuffer<T>::iterator::operator!=(const iterator& other) const { 
    return pos_ != other.pos_; 
}

template <typename T>
typename RingBuffer<T>::iterator RingBuffer<T>::begin() { 
    return iterator(*this, tail_); 
}

template <typename T>
typename RingBuffer<T>::iterator RingBuffer<T>::end() { 
    return iterator(*this, head_); 
}

#include "c_port.h"
#include "ring_buffer.hpp"

// 在这里，把 C 里的不透明句柄实际定义为一个包含 C++ 对象的包装结构
struct RingBufferC_t {
    RingBuffer<uint8_t> buffer;
    RingBufferC_t(uint32_t capacity) : buffer(capacity) {}
};

// 实现 C 接口：创建对象
extern "C" RingBufferC_t* rb_c_create(uint32_t capacity) {
    return new RingBufferC_t(capacity);
}

// 实现 C 接口：写入
extern "C" bool rb_c_push(RingBufferC_t* rb, uint8_t data) {
    if (!rb) return false;
    return rb->buffer.push(data);
}

// 实现 C 接口：读出
extern "C" bool rb_c_pop(RingBufferC_t* rb, uint8_t* data) {
    if (!rb || !data) return false;
    return rb->buffer.pop(*data);
}

// 实现 C 接口：获取大小
extern "C" uint32_t rb_c_size(RingBufferC_t* rb) {
    if (!rb) return 0;
    return rb->buffer.size();
}

// 实现 C 接口：销毁对象
extern "C" void rb_c_destroy(RingBufferC_t* rb) {
    delete rb;
}




