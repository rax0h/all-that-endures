#define _GNU_SOURCE
#include <dlfcn.h>
#include <unistd.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <errno.h>
#include <execinfo.h>
static int output=-1;
static __thread int busy=0;
__attribute__((constructor)) static void initialize(void) {
    const char *path=getenv("ATE_FIXTURE_IO_LOG");
    if(path) output=open(path,O_WRONLY|O_CREAT|O_EXCL,0600);
}
static void record(int fd,long long length,long long before,int result,int error) {
    if(output<0||busy)return;
    busy=1;
    char link[64],path[4096];struct stat now;
    snprintf(link,sizeof(link),"/proc/self/fd/%d",fd);
    ssize_t count=readlink(link,path,sizeof(path)-1);
    if(count>=0)path[count]=0;else snprintf(path,sizeof(path),"unresolved");
    long long after=fstat(fd,&now)==0?(long long)now.st_size:-1;
    dprintf(output,"TRUNCATE fd=%d path=%s before=%lld requested=%lld after=%lld result=%d errno=%d\n",fd,path,before,length,after,result,error);
    void *frames[14];int total=backtrace(frames,14);backtrace_symbols_fd(frames,total,output);
    busy=0;
}
int ftruncate(int fd,off_t length) {
    static int (*next)(int,off_t)=NULL;
    if(!next)next=dlsym(RTLD_NEXT,"ftruncate");
    int prior=errno;struct stat state;long long before=fstat(fd,&state)==0?(long long)state.st_size:-1;errno=prior;
    int result=next(fd,length);int error=errno;record(fd,(long long)length,before,result,error);errno=error;return result;
}
int ftruncate64(int fd,off64_t length) {
    static int (*next)(int,off64_t)=NULL;
    if(!next)next=dlsym(RTLD_NEXT,"ftruncate64");
    int prior=errno;struct stat state;long long before=fstat(fd,&state)==0?(long long)state.st_size:-1;errno=prior;
    int result=next(fd,length);int error=errno;record(fd,(long long)length,before,result,error);errno=error;return result;
}
