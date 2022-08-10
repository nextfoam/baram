#include <stdio.h>
#include <stdbool.h>
#include <unistd.h>
#include <signal.h>

static void
signal_handler(int signum)
{
    char buf[4];

    buf[0] = signum / 10 + '0';
    buf[1] = signum % 10 + '0';
    buf[2] = '\n';
    buf[3] = '\0';

    write(STDOUT_FILENO, buf, 4);
}

int
main(int argc, char *argv[])
{
    struct sigaction signal_action;

    signal_action.sa_handler = signal_handler;
    sigemptyset (&signal_action.sa_mask);
    signal_action.sa_flags = SA_RESTART ;

    sigaction (SIGABRT, &signal_action, NULL);
    sigaction (SIGHUP,  &signal_action, NULL);
    sigaction (SIGINT,  &signal_action, NULL);
    sigaction (SIGQUIT, &signal_action, NULL);
    sigaction (SIGTERM, &signal_action, NULL);
    sigaction (SIGUSR1, &signal_action, NULL);
    sigaction (SIGUSR2, &signal_action, NULL);
    sigaction (SIGTSTP, &signal_action, NULL);


    while(true)
    {
        sleep(1);
    }

    return 0;
}