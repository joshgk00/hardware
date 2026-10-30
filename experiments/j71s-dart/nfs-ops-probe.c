/* Local NFSv4 smoke probe; use only with a disposable loopback export.
 * Creates and removes /ops-check on that export. It is not a kernel client test.
 */
#include <sys/time.h>
#include <fcntl.h>
#include <nfsc/libnfs.h>
#include <stdio.h>
#include <string.h>
#define CHECK(x) do { int r=(x); if (r<0) { fprintf(stderr, "%s: %s\n", #x, nfs_get_error(n)); return 1; } puts(#x " passed"); } while(0)
int main(void) {
 struct nfs_context *n=nfs_init_context(); struct nfsfh *f=NULL; char link[128]={0};
 if(!n)return 1;
 struct nfs_url *u=nfs_parse_url_dir(n,"nfs://127.0.0.1/orchard-root?version=4&nfsport=32061");
 if(!u)return 1;
 CHECK(nfs_mount(n,u->server,u->path));
 CHECK(nfs_mkdir(n,"/ops-check"));
 CHECK(nfs_creat(n,"/ops-check/original",0640,&f));
 CHECK(nfs_close(n,f));
 CHECK(nfs_open(n,"/ops-check/original",O_RDWR,&f));
 if (nfs_write(n,f,5,"hello") != 5) { fprintf(stderr,"short or failed NFS write: %s\n",nfs_get_error(n)); return 1; }
 puts("full NFS write passed");
 CHECK(nfs_close(n,f));
 CHECK(nfs_chmod(n,"/ops-check/original",0600));
 CHECK(nfs_link(n,"/ops-check/original","/ops-check/hard"));
 CHECK(nfs_symlink(n,"original","/ops-check/sym"));
 CHECK(nfs_readlink(n,"/ops-check/sym",link,sizeof(link)));
 if(strcmp(link,"original")){fprintf(stderr,"symlink mismatch\n");return 1;}
 CHECK(nfs_rename(n,"/ops-check/original","/ops-check/renamed"));
 CHECK(nfs_unlink(n,"/ops-check/sym"));
 CHECK(nfs_unlink(n,"/ops-check/hard"));
 CHECK(nfs_unlink(n,"/ops-check/renamed"));
 CHECK(nfs_rmdir(n,"/ops-check"));
 nfs_destroy_url(u);nfs_destroy_context(n);return 0;
}
