#ifndef RING_BUFFER_HPP
#define RING_BUFFER_HPP

#include <vector>
#include <cstddef>
#include <stdexcept>

template <typename T>
class RingBuffer {
public:
    explicit RingBuffer(size_t capacity);
    bool push(const T& item);
    bool pop(T& item);
    size_t size() const;
    size_t capacity() const;
    bool empty() const;
    bool full() const;
    void clear();

    class iterator {
    public:
        iterator(RingBuffer<T>& rb, size_t pos);
        T& operator*();
        iterator& operator++();
        bool operator!=(const iterator& other) const;
    private:
        RingBuffer<T>& rb_;
        size_t pos_;
    };

    iterator begin();
    iterator end();

private:
    std::vector<T> buffer_;
    size_t head_; // 写指针
    size_t tail_; // 读指针
};


#ifdef __cplusplus
extern "C" {
#endif

// ----- 以下全是纯 C 接口 -----

// 初始化 C++ 对象的函数
void my_cpp_init(void);

// 调用 C++ 逻辑的函数
int my_cpp_process(int input_data);

// 释放 C++ 对象的函数
void my_cpp_deinit(void);

#ifdef __cplusplus
}
#endif

// 包含实现文件（模板类常用的拆分方法）
#include "ring_buffer.cpp" 

#endif // RING_BUFFER_HPP