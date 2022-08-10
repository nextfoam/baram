#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <stdbool.h>

#include <unistd.h>

#include <signal.h>
#include <sys/wait.h>

static pid_t child = -1;

static void
daemonize()
{
    /* Our process ID and Session ID */
    pid_t pid, sid;

    /* Fork off the parent process */
    pid = fork();
    if (pid < 0)
    {
        exit(EXIT_FAILURE);
    }

    /* If we got a good PID, then
       we can exit the parent process. */
    if (pid > 0)
    {
        exit(EXIT_SUCCESS);
    }

    /* Create a new SID for the child process */
    sid = setsid();
    if (sid < 0)
    {
        /* Log the failure */
        exit(EXIT_FAILURE);
    }

}

static void
child_handler (int signum)
{

}

static void
forwarding_handler(int signum)
{
    kill(child, signum);
}

int
main(int argc, char *argv[])
{
    struct sigaction forwarding_action;
    struct sigaction child_action;

    int start = 0;

    // ignore all the arguments before "-cmdline", which are just for memo
    for (int i = 1; i < argc; i++)
    {
        if (!strcmp(argv[i], "-cmdline"))
        {
            start = i + 1;
            break;
        }
    }

    if (start == 0 )  // command not found
    {
        printf("command not found\n");
        exit(-1);
    }

    for (int i = 3; i<1024; i++)
        close(i);

    daemonize();

    child = fork();

    if (child == 0)
    {
        execvp(argv[start], &argv[start]);
    }
    else
    {
        close(0);
        close(1);
        close(2);

        forwarding_action.sa_handler = forwarding_handler;
        sigemptyset (&forwarding_action.sa_mask);
        forwarding_action.sa_flags = SA_RESTART ;

        sigaction (SIGABRT, &forwarding_action, NULL);
        sigaction (SIGHUP,  &forwarding_action, NULL);
        sigaction (SIGINT,  &forwarding_action, NULL);
        sigaction (SIGQUIT, &forwarding_action, NULL);
        sigaction (SIGTERM, &forwarding_action, NULL);
        sigaction (SIGUSR1, &forwarding_action, NULL);
        sigaction (SIGUSR2, &forwarding_action, NULL);
        sigaction (SIGTSTP, &forwarding_action, NULL);

        child_action.sa_handler = child_handler;
        sigemptyset (&child_action.sa_mask);
        child_action.sa_flags = SA_RESTART | SA_NOCLDSTOP;

        sigaction (SIGCHLD, &child_action, NULL);

        waitpid(child, NULL, 0);
    }

    return 0;
}