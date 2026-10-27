/* J71s-only read-only UART status sampler for the disposable RAM boot.
 * The target addresses and RX/TX bit masks come from the Linux S5L driver.
 * Never reads the receive data register, and never writes device registers.
 */
typedef unsigned long u64;
typedef unsigned int u32;
struct timespec { long sec, nsec; };
static long call(long n, long a, long b, long c, long d, long e, long f) {
    register long x0 __asm__("x0") = a, x1 __asm__("x1") = b;
    register long x2 __asm__("x2") = c, x3 __asm__("x3") = d;
    register long x4 __asm__("x4") = e, x5 __asm__("x5") = f;
    register long x8 __asm__("x8") = n;
    __asm__ volatile("svc 0" : "+r"(x0) : "r"(x1), "r"(x2), "r"(x3),
                     "r"(x4), "r"(x5), "r"(x8) : "memory");
    return x0;
}
static void print(const char *s) { u64 n = 0; while (s[n]) n++; call(64, 1, (long)s, n, 0, 0, 0); }
static void number(u32 n) { char buf[11]; unsigned i=sizeof(buf); do { buf[--i]='0'+n%10; n/=10; } while(n); call(64,1,(long)(buf+i),sizeof(buf)-i,0,0,0); }
void _start(void) {
    char model[32]={0};
    const char expected[]="apple,j71s";
    long model_fd=call(56,-100,(long)"/proc/device-tree/compatible",0,0,0,0);
    if (model_fd < 0 || call(63,model_fd,(long)model,sizeof(model),0,0,0) < (long)sizeof(expected)) {
        print("Cannot read device identity\n"); call(93,1,0,0,0,0,0);
    }
    call(57,model_fd,0,0,0,0,0);
    for (u32 i=0;i<sizeof(expected);i++)
        if (model[i]!=expected[i]) { print("Wrong device tree\n"); call(93,1,0,0,0,0,0); }
    long driver=call(56,-100,(long)"/sys/bus/platform/devices/20a0d4000.serial/driver",0,0,0,0);
    if (driver < 0) { print("UART driver not bound\n"); call(93,1,0,0,0,0,0); }
    call(57,driver,0,0,0,0,0);
    long fd=call(56,-100,(long)"/dev/mem",0,0,0,0);
    if (fd < 0) { print("Cannot open /dev/mem\n"); call(93,1,0,0,0,0,0); }
    long base=call(222,0,0x4000,1,1,fd,0x20a0d4000UL);
    if (base < 0) { print("Cannot map UART status\n"); call(93,1,0,0,0,0,0); }
    volatile u32 *status=(volatile u32 *)(base+0x10), *fifo=(volatile u32 *)(base+0x18);
    struct timespec delay={0,100000};
    u32 ready=0,rx=0,tx=0;
    for (u32 i=0;i<6000;i++) {
        u32 s=*status, f=*fifo;
        ready += !!(s & 1); rx += !!(f & 0x10f); tx += !!(f & 0x2f0);
        call(101,(long)&delay,0,0,0,0,0);
    }
    print("samples=6000 rx_ready="); number(ready); print(" rx_fifo="); number(rx);
    print(" tx_fifo="); number(tx); print("\n");
    call(215,base,0x4000,0,0,0,0); call(57,fd,0,0,0,0,0); call(93,0,0,0,0,0,0);
    __builtin_unreachable();
}
