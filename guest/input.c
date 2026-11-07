/* SPDX-License-Identifier: MIT
 * VM-bound lifetime association followed by unchanged RVGPU input packets.
 * EOF, malformed input, heartbeat loss and termination release all owned keys.
 * Derived from vendor/wsx-proto/input/guest.c; device names carry the instance.
 */
#define _GNU_SOURCE
#include <sys/socket.h>
#include <linux/input.h>
#include <linux/uinput.h>
#include <linux/vm_sockets.h>
#include <sys/ioctl.h>
#include <poll.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <unistd.h>
#include <signal.h>
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdbool.h>
#include <stdint.h>
#include <time.h>
#include <librvgpu/rvgpu-protocol.h>
static volatile sig_atomic_t running = 1;
static int devices[3] = {-1,-1,-1};
static bool held[3][KEY_CNT];
static void stop(int sig) { (void)sig; running = 0; }
static int emit(int device, uint16_t type, uint16_t code, int value) {
 struct input_event event = {.type=type,.code=code,.value=value};
 return write(devices[device], &event, sizeof(event)) == sizeof(event) ? 0 : -1;
}
static int create_device(int index, const char *instance) {
 int fd = open("/dev/uinput", O_WRONLY | O_CLOEXEC); if (fd < 0) return -1;
 devices[index] = fd;
#define SET(request, value) do { if (ioctl(fd, request, value) < 0) return -1; } while (0)
 SET(UI_SET_EVBIT, EV_KEY);
 if (index == RVGPU_INPUT_KEYBOARD) {
  for (int key = 1; key <= 194; key++) SET(UI_SET_KEYBIT, key);
 } else {
  for (int key = BTN_LEFT; key <= BTN_MIDDLE; key++) SET(UI_SET_KEYBIT, key);
  SET(UI_SET_PROPBIT, INPUT_PROP_POINTER);
  if (index == RVGPU_INPUT_MOUSE) {
   SET(UI_SET_EVBIT, EV_REL);
   SET(UI_SET_RELBIT, REL_X); SET(UI_SET_RELBIT, REL_Y);
   SET(UI_SET_RELBIT, REL_WHEEL); SET(UI_SET_RELBIT, REL_HWHEEL);
  } else {
   SET(UI_SET_EVBIT, EV_ABS); SET(UI_SET_ABSBIT, ABS_X); SET(UI_SET_ABSBIT, ABS_Y);
   for (int axis = ABS_X; axis <= ABS_Y; axis++) {
    struct uinput_abs_setup abs = {.code=axis,.absinfo={.minimum=0,.maximum=65535}};
    if (ioctl(fd, UI_ABS_SETUP, &abs) < 0) return -1;
   }
  }
 }
 struct uinput_setup setup = {.id={.bustype=BUS_VIRTUAL,.vendor=0x5753,.product=index+1,.version=1}};
 snprintf(setup.name, sizeof(setup.name), "WSX %s %s", instance, index == RVGPU_INPUT_KEYBOARD ? "Keyboard" : index == RVGPU_INPUT_MOUSE_ABS ? "Pointer" : "Wheel");
 if (ioctl(fd, UI_DEV_SETUP, &setup) < 0 || ioctl(fd, UI_DEV_CREATE) < 0) return -1;
 return 0;
#undef SET
}
static void cleanup(void) {
 for (int i = 0; i < 3; i++) if (devices[i] >= 0) {
  for (int k = 0; k < KEY_CNT; k++) if (held[i][k]) emit(i, EV_KEY, k, 0);
  emit(i, EV_SYN, SYN_REPORT, 0); ioctl(devices[i], UI_DEV_DESTROY); close(devices[i]); devices[i]=-1;
 }
}
static int read_exact(int socket, void* data, size_t size) {
 size_t used = 0;
 while (running && used < size) {
  struct pollfd pollfd = {.fd=socket,.events=POLLIN};
  int ready = poll(&pollfd, 1, 3000);
  if (ready < 0 && errno == EINTR) continue;
  if (ready <= 0) return -1;
  if (!(pollfd.revents & POLLIN)) return (pollfd.revents & POLLHUP) && !used ? 1 : -1;
  ssize_t n = recv(socket, (char*)data + used, size - used, 0);
  if (n <= 0) return n == 0 && !used ? 1 : -1;
  used += (size_t)n;
 }
 return used == size ? 0 : -1;
}
static bool valid_event(int device, const struct rvgpu_input_event* e) {
 if (e->type == EV_SYN) return e->code == SYN_REPORT && e->value == 0;
 if (e->type == EV_KEY) {
  if (e->value != 0 && e->value != 1) return false;
  return device == RVGPU_INPUT_KEYBOARD ? e->code >= 1 && e->code <= 194 :
      e->code >= BTN_LEFT && e->code <= BTN_MIDDLE;
 }
 if (device == RVGPU_INPUT_MOUSE_ABS && e->type == EV_ABS)
  return (e->code == ABS_X || e->code == ABS_Y) && e->value >= 0 && e->value <= 65535;
 if (device == RVGPU_INPUT_MOUSE && e->type == EV_REL)
  return (e->code == REL_X || e->code == REL_Y || e->code == REL_WHEEL || e->code == REL_HWHEEL) && e->value >= -65535 && e->value <= 65535;
 return false;
}
int main(int argc, char** argv) {
 _Static_assert(sizeof(struct rvgpu_input_header)==4 && sizeof(struct rvgpu_input_event)==8, "RVGPU input wire");
 if (argc != 4 || strlen(argv[2]) != 36) { fprintf(stderr,"Usage: wsx-input-guest PORT INSTANCE READY-FILE\n"); return 2; }
 char* end; unsigned long port = strtoul(argv[1], &end, 10);
 if (*end || !port || port >= UINT32_MAX) return 2;
 for (unsigned i=0;i<36;i++) if ((i==8||i==13||i==18||i==23) ? argv[2][i]!='-' : !strchr("0123456789abcdef",argv[2][i])) return 2;
 struct sigaction action = {.sa_handler=stop}; sigemptyset(&action.sa_mask);
 sigaction(SIGINT,&action,NULL); sigaction(SIGTERM,&action,NULL); signal(SIGPIPE,SIG_IGN);
 atexit(cleanup);
 int peer = -1;
 for (unsigned attempt=0; running && attempt<300; attempt++) {
  peer = socket(AF_VSOCK, SOCK_STREAM | SOCK_CLOEXEC, 0); if (peer<0) break;
  struct sockaddr_vm address = {.svm_family=AF_VSOCK,.svm_cid=VMADDR_CID_HOST,.svm_port=(uint32_t)port};
  if (connect(peer,(struct sockaddr*)&address,sizeof(address))==0) break;
  close(peer);peer=-1;usleep(100000);
 }
 if (peer < 0) { perror("input connect"); return 1; }
 size_t used=0; while (used<36) { ssize_t n=send(peer,argv[2]+used,36-used,MSG_NOSIGNAL); if(n<=0){close(peer);return 1;}used+=(size_t)n; }
 char association[36];
 if (read_exact(peer,association,sizeof(association)) || memcmp(association,argv[2],36)) { close(peer);return 1; }
 for (int i=0;i<3;i++) if (create_device(i, argv[2])) { perror("uinput");close(peer);return 1; }
 int ready=open(argv[3],O_CREAT|O_EXCL|O_WRONLY|O_CLOEXEC,0600);
 if(ready<0){perror("input ready");close(peer);return 1;}
 close(ready); fprintf(stderr,"WSX_INPUT_GUEST: ready instance=%s\n",argv[2]);
 unsigned long packets=0; int result=0;
 while(running) {
  struct rvgpu_input_header h; struct rvgpu_input_event events[8];
  int status=read_exact(peer,&h,sizeof(h));
  if(status){result=status==1||!running?0:1;break;}
  if(h.dev<0||h.dev>=3||h.src||h.evnum>8){result=1;break;}
  if(!h.evnum)continue;
  if(read_exact(peer,events,h.evnum*sizeof(*events))){result=1;break;}
  bool valid=events[h.evnum-1].type==EV_SYN && events[h.evnum-1].code==SYN_REPORT;
  for(unsigned i=0;i<h.evnum;i++)valid=valid&&valid_event(h.dev,&events[i]);
  if(!valid){result=1;break;}
  for(unsigned i=0;i<h.evnum;i++) {
   struct rvgpu_input_event* e=&events[i];
   if(emit(h.dev,e->type,e->code,e->value)){result=1;running=0;break;}
   if(e->type==EV_KEY)held[h.dev][e->code]=e->value!=0;
  }
  packets++;
 }
 fprintf(stderr,"WSX_INPUT_GUEST: stopped packets=%lu result=%d\n",packets,result);
 unlink(argv[3]);close(peer);return result;
}
