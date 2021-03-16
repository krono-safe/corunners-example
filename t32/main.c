/************ Copyright Krono-Safe S.A. 2020, All rights reserved ************/

#include <t32.h> /* <--- this require the T32 C API */

#include <stdio.h>
#include <assert.h>
#include <stdlib.h>
#include <stdint.h>
#include <limits.h>
#include <signal.h>
#include <errno.h>
#include <string.h>
#include <unistd.h>

#define ERR(Fmt, ...) fprintf(stderr, "*** " Fmt "\n", ## __VA_ARGS__)
#define DIE(Code, Fmt, ...) \
  do { \
    fprintf(stderr, "*** " Fmt " (error code: %i)\n", ## __VA_ARGS__, Code); \
    exit(Code); \
  } while (0)


/* We have a buffer of 1024 elements, each element being a structure of size
 * 24.  These are hard-coded parameters, not that great, but it will do */
static uint8_t BUFFER[1024 * 24];


/**
 * This is a callback used with atexit(). It ensures T32_Exit() is
 * systematically called before the program exit, as long as the
 * program is not brutally terminated.
 */
static void cleanup(void)
{
  const int ret = T32_Exit();
  if (ret != T32_OK)
  { ERR("T32_Exit() failed with code %i", ret); }
}

static void sighandler(const int sig)
{
  exit(-sig);
}

static void set_signal_handler(const int sig)
{
  struct sigaction sa = {
    .sa_handler = &sighandler,
    .sa_flags = SA_RESTART,
  };
  sigemptyset(&sa.sa_mask);
  sigaction(sig, &sa, NULL);
}

/*****************************************************************************/

static void config_set(const char *const p1, const char *const p2)
{
  const int ret = T32_Config(p1, p2);
  if (ret != T32_OK)
  { DIE(ret, "Failed to set config '%s%s'", p1, p2); }
}

static int retry_get_state(int (*func)(int *p), int *state)
{
  int ret;
  int retry_count = 8;

  assert(state != NULL);
  assert(func != NULL);

again:
  ret = func(state);
  switch (ret)
  {
    /* Network errors actually happen there.... */
  case T32_ERR_COM_RECEIVE_FAIL: /* fallthrough */
  case T32_ERR_COM_TRANSMIT_FAIL:
    if (retry_count <= 0)
    { return ret; }
    retry_count--;
    sleep(5); /* Rest a bit */
    goto again;

  default:
    return ret;
  }
}

static void wait_exec(const int delay_s)
{
  for (;;)
  {
    int state;
    const int ret = retry_get_state(&T32_GetState, &state);
    if (ret != T32_OK)
    { DIE(ret, "Failed to query Trace32 program state"); }

    if (state == 0) /* Debug system down */
    {
      printf(" ERROR\n");
      DIE(-1, "System is down!?");
    }
    else if (state == 1) /* Debug system halted */
    {
      printf(" ERROR\n");
      DIE(-1, "System is halted!?");
    }
    else if (state == 2) /* Stopped */
    {
      printf(" done\n");
      break;
    }
    else if (state == 3) /* Running */
    {
      printf(".");
      fflush(stdout);
      sleep(delay_s);
    }
    else /* Full retard */
    {
      printf(" ERROR\n");
      DIE(-1, "Unknown status. What is going on?");
    }
  }
}

static void wait_practise(const int delay_s)
{
  for (;;)
  {
    int p_state;
    const int ret = retry_get_state(&T32_GetPracticeState, &p_state);
    if (ret != T32_OK)
    { DIE(ret, "Failed to query Trace32 state"); }

    if (p_state == 0) /* Finished */
    {
      printf(" done\n");
      break;
    }
    else if (p_state == 1) /* Running */
    {
      printf(".");
      fflush(stdout);
      sleep(delay_s);
    }
    else if (p_state == 2) /* Dialog open */
    {
      printf(" ERROR\n");
      DIE(-1, "Trace32 is in dialog mode. It waits for an input. DIE!");
    }
    else /* Full retard */
    {
      printf(" ERROR\n");
      DIE(-1, "Unknown status. What is going on?");
    }
  }
}

/**
 * Make Trace32 go to the next breakpoint.
 * This synchronouly wait for the execution to complete, WITHOUT TIMEOUT.
 */
static int next(void)
{
  uint32_t pp;
  char symbol[0xfc];
  int ret = T32_Go();
  if (ret != T32_OK)
  { DIE(ret, "Failed to advance after breakpoint"); }
  printf("Going to next breakpoint..."); fflush(stdout);
  wait_exec(5);
  ret = T32_ReadPP(&pp);
  if (ret != T32_OK)
  { ERR("Failed to retrieve curent program pointer. Error code: %d", ret); }
  ret = T32_GetSymbolFromAddress(symbol, pp, (int)0xfc);
  if (ret != T32_OK)
  { ERR("Failed to retrieve curent function symbol. Error code: %d", ret); }
  printf("Currently at %s. ", symbol); fflush(stdout);

  if(! strcmp(symbol, "em_raise") || ! strcmp(symbol, "em_early_raise"))
  { printf("\n"); return 1; }
  else return 0;
}

/**
 * Makes Trace32 synchronouly execute a CMM script \p arg.
 * The script \p arg is systematically converted to an absolute path.
 */
static void run_script(const char *const arg)
{
  int ret;

  /* Convert the script to an absolute path */
  char script[PATH_MAX] = "";
  if (NULL == realpath(arg, script))
  {
    const int err = errno;
    DIE(err, "realpath(%s) failed with error: %s", arg, strerror(err));
  }

  /* Ask T32 to run the script. If the function succeeds, T32 will be
   * loading the script asynchronously! */
  ret = T32_Cmd_f("DO \"%s\"", script);
  if (ret != T32_OK)
  { DIE(ret, "Failed to execute CMM script '%s'", script); }
  printf("Remotely running script '%s'. This may take some time", script);
  fflush(stdout);

  wait_practise(2);
}

static void in_target_reset(void)
{
  static const char cmd[] = "SYStem.RESetTarget";
  const int ret = T32_Cmd(cmd);
  if (ret != T32_OK)
  { DIE(ret, "Failed to execute '%s' (aka. 'In Target Reset')", cmd); }
  printf("Resetting. This may take some time");
  fflush(stdout);
  wait_practise(2);
}

/**
 * Reads a 32-bits (unsigned) variable with name \p name.
 */
static uint32_t read_u32(const char *const name)
{
  uint32_t low = 0, high = 0;
  const int ret = T32_ReadVariableValue(name, &low, &high);
  if (ret != T32_OK)
  { DIE(ret, "Failed to retrieve contents of variable '%s'", name); }
  if (high != 0)
  { DIE(-1, "Variable '%s' uses 64-bits", name); }
  return low;
}

int main(const int argc, const char *const argv[argc])
{
  /* Trivial getopts */
  if (argc != 3)
  {
    ERR("Usage: %s <script.cmm> <output.bin>", argv[0]);
    return 1;
  }
  const char *const script = argv[1];
  const char *const output = argv[2];

  /* Make sure we will (almost) always terminate the program by leaving T32 in
   * a clean state. */
  atexit(&cleanup);
  set_signal_handler(SIGINT);

  int ret;

  config_set("NODE=", "localhost");
  config_set("PACKLEN=", "1024");
  config_set("PORT=", "20000");

  ret = T32_Init();
  if (ret != T32_OK)
  { DIE(ret, "Failed to init T32"); }

  /* Attach to T32. The parameter is the device identifier.  T32_DEV_ICD and
   * T32_DEV_ICE are identical and mean the same thing: the debugger */
  ret = T32_Attach(T32_DEV_ICD);
  if (ret != T32_OK)
  { DIE(ret, "Failed to attach to the Trace32 device"); }

  /* Okay, we are ready!!! Now execute the script to flash the program */
  run_script(script);

  /* Make sure the board is reset... otherwise it may not work... */
  //in_target_reset();

  /* At this point, we are waiting at breakpoints, and check each time if we reached an error function.*/
  while(! next()){ }

  /* Okay, at this point trace32 is at the em_raise breakpoint. First check
   * that the error code is the one we expect from normal termination: */
  const uint32_t error = read_u32("error_id");
  if (error != 0x00030009)
  { DIE(-1, "Error ID expected is '0x%08X' but we have '0x%08X'", 0x00030009, error); }

  /* Now, retrieve the address of the buffer holding measures */
  const uint32_t address = read_u32("&k2_stubborn_measures");

  /* Retrieve the profiling buffer in-memory */
  ret = T32_ReadMemory(address, 0x0, BUFFER, sizeof(BUFFER));
  if (ret != T32_OK)
  { DIE(ret, "Failed to read memory from address 0x%08X", address); }

  /* And finally, dump the profiling buffer to the local filesystem */
  FILE *const file = fopen(output, "wb");
  if (! file)
  {
    const int err = errno;
    DIE(err, "Failed to open '%s' for writing: %s", output, strerror(err));
  }
  if (fwrite(BUFFER, 1, sizeof(BUFFER), file) != sizeof(BUFFER))
  {
    const int err = errno;
    fclose(file);
    DIE(err, "Failed to write to '%s': %s", output, strerror(err));
  }
  fclose(file);

  return 0;
}
