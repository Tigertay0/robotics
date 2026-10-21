/******************************************************************************
 * Robot B - "Point Scorer"                                  2026 Fall Game
 * KIPR Wombat, 2 gear motors (differential), servo arm + micro-servo claw,
 * cup-hook servo, camera, 2 tophats, ET, lever switch on the plow.
 *
 * Implements the Robot B column of STRATEGY.md section 4:
 *   upper cup -> wait -> lower cup + red pom -> 5 pom stacks -> pickleball 1
 *   -> red pom on the platform.
 * Numbers marked CALIBRATE were budgeted, not measured.
 *
 * Servo values are last season's measured ones (Botball robotics 2025_26.pdf)
 * for the same arm/claw servos; re-check after rebuilding.
 *****************************************************************************/
#include <kipr/wombat.h>
#include <stdio.h>
#include <math.h>

/* ---------------------------------------------------------------- ports */
#define LEFT   0
#define RIGHT  2
#define SERVO_ARM    1            /* shoulder (regular servo)      */
#define SERVO_CLAW   2            /* claw (micro servo)            */
#define SERVO_HOOK   3            /* cup hook on the right side    */
#define TOPHAT_L     0
#define TOPHAT_R     1
#define ET_FRONT     2
#define LIGHT_START  3
#define LEVER_PLOW   0            /* digital: plow touched something */
#define CAM_RED      0            /* camera channel 0 = find_red.conf, as last year */

/* ---------------------------------------------------------------- calibration */
#define TICKS_PER_REV   1870.0
#define WHEEL_DIAM_IN   2.75               /* CALIBRATE: Solarbotics wheel; last year's were 3.0 */
#define TICKS_PER_INCH  (TICKS_PER_REV / (M_PI * WHEEL_DIAM_IN))
#define TICKS_PER_DEG   13.0               /* CALIBRATE: last year's pivot constant (angle * 13) */
#define TAPE_THRESHOLD  2700
#define LIGHT_ON        770
#define SPEED_FAST      80
#define SPEED_PUSH      45
#define MATCH_END_S     118

#define ARM_UP        860                  /* measured last season */
#define ARM_DOWN     1750
#define ARM_PLATFORM  600                  /* CALIBRATE: claw above the 5.7 in platform edge */
#define CLAW_OPEN    2000
#define CLAW_CLOSED  1200
#define HOOK_UP      1000                  /* CALIBRATE */
#define HOOK_DOWN    1900

/* ---------------------------------------------------------------- base */
static void drive(int l, int r) { motor(LEFT, l); motor(RIGHT, r); }
static void stop_all(void) { ao(); }

static void forward_in(double inches, int speed) {
    long target = (long)(fabs(inches) * TICKS_PER_INCH);
    int s = inches < 0 ? -speed : speed;
    cmpc(LEFT);
    drive(s, s);
    while (labs(gmpc(LEFT)) < target && seconds() < MATCH_END_S) msleep(5);
    stop_all();
    msleep(150);
}
/* positive = counter-clockwise (turn left), in place */
static void turn_deg(double deg, int speed) {
    long target = (long)(fabs(deg) * TICKS_PER_DEG);
    cmpc(LEFT);
    if (deg > 0) drive(-speed, speed); else drive(speed, -speed);
    while (labs(gmpc(LEFT)) < target && seconds() < MATCH_END_S) msleep(5);
    stop_all();
    msleep(200);
}
/* gentle arc: inner wheel at half speed. sign of deg = direction as in turn_deg */
static void arc_in(double inches, double deg, int speed) {
    long target = (long)(fabs(inches) * TICKS_PER_INCH);
    cmpc(LEFT); cmpc(RIGHT);
    if (deg > 0) drive(speed / 2, speed); else drive(speed, speed / 2);
    while ((labs(gmpc(LEFT)) + labs(gmpc(RIGHT))) / 2 < target && seconds() < MATCH_END_S) msleep(5);
    stop_all();
}
/* drive forward until a tophat sees tape, then stop */
static void forward_to_tape(int speed) {
    drive(speed, speed);
    while (analog10(TOPHAT_L) >= TAPE_THRESHOLD && analog10(TOPHAT_R) >= TAPE_THRESHOLD && seconds() < MATCH_END_S) msleep(5);
    stop_all();
}

/* ---------------------------------------------------------------- tools */
static void flip_cup_with_right_wing(double push_in) {
    /* the cup is upside-down; the hook catches the rim, the wing rolls it upright
       while the robot keeps pushing. CALIBRATE the hook height on the real cup. */
    set_servo_position(SERVO_HOOK, HOOK_DOWN);
    msleep(300);
    forward_in(push_in, SPEED_PUSH);
    set_servo_position(SERVO_HOOK, HOOK_UP);
}

/* find the red pom with the camera, centre on it, grab it. returns 1 on success */
static int grab_red_pom(void) {
    set_servo_position(SERVO_CLAW, CLAW_OPEN);
    set_servo_position(SERVO_ARM, ARM_DOWN);
    msleep(400);
    camera_open();
    int found = 0;
    for (int tries = 0; tries < 40 && !found; tries++) {   /* ~4 s budget */
        camera_update();
        if (get_object_count(CAM_RED) > 0) {
            int x = get_object_center_x(CAM_RED, 0);        /* 0..159 */
            if (x < 70)       drive(-25, 25);
            else if (x > 90)  drive(25, -25);
            else { found = 1; stop_all(); }
        } else {
            drive(-25, 25);                                  /* scan */
        }
        msleep(100);
    }
    camera_close();
    stop_all();
    if (!found) { set_servo_position(SERVO_ARM, ARM_UP); return 0; }
    forward_in(2.0, 30);
    set_servo_position(SERVO_CLAW, CLAW_CLOSED);
    msleep(400);
    set_servo_position(SERVO_ARM, ARM_UP);
    msleep(400);
    return 1;
}

/* push one pom stack north off the tape: start 3.5 in south of the stack line */
static void push_stack_north(void) {
    forward_in(3.5, SPEED_PUSH);       /* stack ends ~2 in north of the tape edge */
    forward_in(-3.5, SPEED_FAST);
}

/* ---------------------------------------------------------------- main */
int main(void) {
    enable_servos();
    set_servo_position(SERVO_ARM, ARM_UP);
    set_servo_position(SERVO_CLAW, CLAW_OPEN);
    set_servo_position(SERVO_HOOK, HOOK_UP);
    printf("Robot B ready. Waiting for the light.\n");
    while (analog(LIGHT_START) > LIGHT_ON) msleep(10);
    shut_down_in(119.0);

    /* 0-16 s: out of zone 5 heading NE, left plow wing takes the upper cup north-east into zone 2 */
    arc_in(5.0, +45, SPEED_FAST);               /* (33, 5.6) -> facing NE */
    forward_in(17.5, SPEED_FAST);               /* -> ~(48.5, 21): wing meets the cup */
    forward_in(12.0, SPEED_PUSH);               /* cup rolls upright and slides to ~(59.5, 34) */
    arc_in(9.0, -45, SPEED_FAST);               /* -> ~(64, 32) facing east */

    /* 17-32 s: loop down the east side; face west by the lower cup at (68, 16) */
    arc_in(12.0, -60, SPEED_FAST);
    forward_in(10.0, SPEED_FAST);
    arc_in(8.0, -75, SPEED_FAST);               /* now heading west at ~(68, 16) */

    /* 32-50 s: wait for A to finish the duck run and the first two drops */
    while (seconds() < 50) msleep(50);

    /* 50-58 s: flip the lower cup with the right wing + hook, push it west into zone 5 */
    forward_in(11.4, SPEED_FAST);               /* -> (56.6, 16): wing meets the cup rim */
    flip_cup_with_right_wing(28.0);             /* cup ends ~(18.5, 7.3); hidden poms spill */

    /* 58-63 s: the red pom */
    forward_in(-1.0, SPEED_FAST);
    int have_red = grab_red_pom();
    if (!have_red) printf("red pom not found, skipping the platform\n");

    /* 63-86 s: five pom stacks, east to west, each pushed north into zone 1 */
    forward_in(-10.0, SPEED_FAST);              /* back east to x ~ 39.8 */
    turn_deg(+90, SPEED_FAST);                  /* face north */
    forward_to_tape(SPEED_FAST);                /* lower tape: y ~ 12 */
    forward_in(3.5, SPEED_FAST);                /* -> y ~ 15.5 */
    for (int k = 0; k < 5; k++) {
        push_stack_north();
        if (k < 4) {                            /* side-step 8 in west: back-arc then forward-arc */
            arc_in(-6.0, -40, SPEED_FAST);
            arc_in(6.0, +40, SPEED_FAST);
        }
    }

    /* 86-97 s: down to the bottom wall and east to pickleball 1 */
    forward_in(-5.0, SPEED_FAST);
    turn_deg(-90, SPEED_FAST);                  /* face east at ~(6.5, 14) */
    forward_in(27.5, SPEED_FAST);               /* -> (34, 14) */
    arc_in(10.0, -35, SPEED_FAST);              /* -> ~(42, 8) */
    arc_in(4.5, +35, SPEED_FAST);               /* -> (45, 5.3) facing east */
    set_servo_position(SERVO_HOOK, HOOK_DOWN);  /* hook sweeps the ball off its post */
    forward_in(2.5, SPEED_PUSH);
    set_servo_position(SERVO_HOOK, HOOK_UP);

    /* 97-104 s: push the ball under the platform, stop at x = 66 */
    forward_in(18.5, SPEED_PUSH);

    /* 104-112 s: red pom alone on the platform (big duck is allowed next to it) */
    if (have_red) {
        set_servo_position(SERVO_ARM, ARM_PLATFORM);
        msleep(1200);
        set_servo_position(SERVO_CLAW, CLAW_OPEN);
        msleep(400);
        set_servo_position(SERVO_ARM, ARM_UP);
    }

    stop_all();
    disable_servos();
    printf("Robot B done at %.1f s\n", seconds());
    return 0;
}
