#include <stdio.h>

struct A {
    char a1;
    char a2;
};

struct B {
    char b1;
    struct A a;
} __attribute__((packed));

int main() {
    struct B b;

    printf("%x\n%x\n%x\n", &b, &b.a, &b.a.a2);
    return 0;
}
