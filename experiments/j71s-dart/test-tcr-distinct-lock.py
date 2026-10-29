#!/usr/bin/env python3
"""Test the actual S5L TCR function when the general DART lock is held."""
from pathlib import Path
import argparse, subprocess, tempfile

parser = argparse.ArgumentParser()
parser.add_argument('kernel', type=Path)
args = parser.parse_args()
src = (args.kernel / 'drivers/iommu/apple-dart.c').read_text()
start = src.index('static void apple_dart_s5l8960x_write_tcr(')
end = src.index('\nstatic u32 apple_dart_t8020_read_tcr', start)
func = src[start:end]
program = r'''
#include <stdint.h>
#include <stdlib.h>
#include <pthread.h>
#include <sched.h>
typedef uint32_t u32;
#define DART_S5L8960X_TCR_BITS_PER_STREAM 8
#define DART_S5L8960X_MAX_STREAMS 4
#define WARN_ON(x) (x)
struct hw {u32 tcr;};
struct apple_dart {unsigned char *regs;struct hw *hw;pthread_mutex_t lock,tcr_lock;};
#define spin_lock_irqsave(p,flags) do { (flags)=0; if ((p)!=&dart->tcr_lock) exit(42); if(pthread_mutex_lock(p)) exit(43); } while(0)
#define spin_unlock_irqrestore(p,flags) do { (void)(flags); if(pthread_mutex_unlock(p)) exit(44); } while(0)
static u32 readl(void *p){u32 v=*(u32*)p;sched_yield();return v;}
static void writel(u32 v,void *p){*(u32*)p=v;}
''' + func + r'''
struct input {struct apple_dart *dart;u32 sid;};
static void *worker(void *arg){struct input *i=arg;for(int n=0;n<1000;n++)apple_dart_s5l8960x_write_tcr(i->dart,i->sid,0x80);return NULL;}
int main(void){
 struct hw hw={0};u32 reg=0;struct apple_dart d={(unsigned char*)&reg,&hw,PTHREAD_MUTEX_INITIALIZER,PTHREAD_MUTEX_INITIALIZER};
 pthread_t threads[4];struct input args[4];
 if(pthread_mutex_lock(&d.lock))return 1;
 apple_dart_s5l8960x_write_tcr(&d,2,0x80);
 if(reg!=0x00800000)return 2;
 if(pthread_mutex_unlock(&d.lock))return 3;
 reg=0;
 for(u32 i=0;i<4;i++){args[i]=(struct input){&d,i};if(pthread_create(&threads[i],NULL,worker,&args[i]))return 4;}
 for(int i=0;i<4;i++)if(pthread_join(threads[i],NULL))return 5;
 if(reg!=0x80808080)return 6;
 apple_dart_s5l8960x_write_tcr(&d,4,0x80);
 apple_dart_s5l8960x_write_tcr(&d,1,0x100);
 if(reg!=0x80808080)return 7;
 return 0;
}
'''
with tempfile.TemporaryDirectory() as temp:
 p=Path(temp);(p/'test.c').write_text(program)
 subprocess.run(['cc','-std=c11','-Wall','-Wextra','-Werror','-pthread',str(p/'test.c'),'-o',str(p/'test')],check=True)
 subprocess.run([str(p/'test')],check=True,timeout=15)
print('Dedicated TCR lock, outer lock held, concurrent streams and bounds passed.')
