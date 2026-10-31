/******************************************************************************
 * Robot A - "Duck Runner"                                   2026 Fall Game
 * KIPR Wombat, 4 gear motors on mecanum wheels, 3 servo flaps, tophats.
 *
 * Implements the Robot A column of STRATEGY.md section 4.
 * Every number marked CALIBRATE was budgeted, not measured: tune it on the
 * real robot before trusting the timeline.
 *
 * Motor ports follow last season's wiring (Botball robotics 2025_26.pdf):
 *   FR 0, FL 1, BR 2, BL 3.  Encoder: 1870 ticks per wheel revolution.
 *****************************************************************************/
#include <kipr/wombat.h>
#include <stdio.h>
#include <stdlib.h>    /* abs, labs */
#include <math.h>

/* ---------------------------------------------------------------- ports */
#define FR 0
#define FL 1
#define BR 2
#define BL 3
#define SERVO_GATE_C   0      /* intake flap, front            (regular servo) */
#define SERVO_GATE_B   1      /* pin flap, one duck from rear  (micro servo)   */
#define SERVO_GATE_A   2      /* exit flap, rear               (regular servo) */
#define TOPHAT_L       0      /* analog: left tape sensor at the lane mouth    */
#define TOPHAT_R       1      /* analog: right tape sensor                     */
#define ET_FRONT       2      /* analog: ET rangefinder looking forward        */
#define LIGHT_START    3      /* analog: starting-light sensor                 */
#define TOUCH_LANE     0      /* digital: pressed when the 5th duck is in      */

/* ---------------------------------------------------------------- calibration */
#define TICKS_PER_REV   1870.0
#define WHEEL_DIAM_IN   2.36                 /* CALIBRATE: 60 mm mecanum; last year's wheels were 3.0 */
#define TICKS_PER_INCH  (TICKS_PER_REV / (M_PI * WHEEL_DIAM_IN))
#define STRAFE_FACTOR   1.15                 /* CALIBRATE: mecanum wheels slip sideways */
#define TAPE_THRESHOLD  2700                 /* CALIBRATE: analog (12-bit) < this = black (last year 2700) */
#define LIGHT_ON        770                  /* CALIBRATE: analog < this = light on (last year 770) */
#define SPEED_FAST      80
#define SPEED_LINE      45                   /* line-following speed while swallowing ducks */
#define SPEED_SLOW      30
#define MATCH_END_S     118                  /* hard stop; rules DQ a robot still moving at 120 */

/* servo positions, CALIBRATE on the built flaps */
#define GATE_OPEN    1900
#define GATE_CLOSED  1000

/* ---------------------------------------------------------------- mecanum base */
/* vx: + forward (east at start), vy: + left (north at start), w: + counter-clockwise */
static void mecanum(int vx, int vy, int w) {
    /* Each wheel is a sum of up to three terms, so a mix can exceed motor()'s -100..100
       range. Scale all four together rather than letting motor() clip them one by one:
       clipping per wheel would silently bend the commanded direction. */
    int m[4] = { vx - vy - w, vx + vy + w, vx + vy - w, vx - vy + w };   /* FL, FR, BL, BR */
    int peak = 0;
    for (int i = 0; i < 4; i++)
        if (abs(m[i]) > peak) peak = abs(m[i]);
    if (peak > 100)
        for (int i = 0; i < 4; i++) m[i] = m[i] * 100 / peak;
    motor(FL, m[0]);
    motor(FR, m[1]);
    motor(BL, m[2]);
    motor(BR, m[3]);
}
static void stop_all(void) { ao(); }

/* Drive a straight distance in inches; dx forward, dy left. Pass exactly one non-zero:
   direction is quantised to the sign of dx/dy and the tick target is |dx|+|dy|, so a
   diagonal call drives 45 deg for a Manhattan distance and misses the waypoint. Split
   diagonals into two calls at the call site. */
static void move_in(double dx, double dy, int speed) {
    double dist = fabs(dx) + fabs(dy);
    double factor = (dy != 0) ? STRAFE_FACTOR : 1.0;
    long target = (long)(dist * TICKS_PER_INCH * factor);
    int vx = (dx > 0) - (dx < 0), vy = (dy > 0) - (dy < 0);
    cmpc(FL);
    mecanum(vx * speed, vy * speed, 0);
    while (labs(gmpc(FL)) < target && seconds() < MATCH_END_S) msleep(5);
    stop_all();
    if (labs(gmpc(FL)) < target)   /* ran out of match clock: say so, or the rest of the run
                                      silently no-ops and the log shows nothing wrong */
        printf("move_in(%.1f, %.1f) stopped at %ld/%ld ticks, t=%.1f s\n",
               dx, dy, labs(gmpc(FL)), target, seconds());
    msleep(150);
}

/* keep the lane mouth on the centre tape while creeping east, until the lane is full */
static void follow_tape_east(double inches, int speed) {
    long target = (long)(inches * TICKS_PER_INCH);
    cmpc(FL);
    /* the touch switch at the rear of the lane is the real stop condition; the distance
       is only the backstop for a switch that never trips */
    while (labs(gmpc(FL)) < target && !digital(TOUCH_LANE) && seconds() < MATCH_END_S) {
        int l = analog(TOPHAT_L) < TAPE_THRESHOLD;
        int r = analog(TOPHAT_R) < TAPE_THRESHOLD;
        if (l && !r)      mecanum(speed, +20, 0);   /* drifted right: nudge left  */
        else if (r && !l) mecanum(speed, -20, 0);   /* drifted left: nudge right  */
        else              mecanum(speed, 0, 0);
        msleep(10);
    }
    stop_all();
    printf("follow_tape_east: %ld/%ld ticks, lane full=%d, t=%.1f s\n",
           labs(gmpc(FL)), target, digital(TOUCH_LANE), seconds());
}

/* ---------------------------------------------------------------- escapement */
static void gates_init(void) {
    set_servo_position(SERVO_GATE_C, GATE_OPEN);     /* intake open while collecting */
    set_servo_position(SERVO_GATE_B, GATE_OPEN);
    set_servo_position(SERVO_GATE_A, GATE_CLOSED);   /* exit shut */
}

/* release exactly one duck: pin holds duck #2, exit opens, robot creeps forward, exit shuts */
static void drop_one_duck(void) {
    set_servo_position(SERVO_GATE_B, GATE_CLOSED);   /* pin the second duck from the rear */
    msleep(300);
    set_servo_position(SERVO_GATE_A, GATE_OPEN);
    msleep(300);
    move_in(2.5, 0, SPEED_SLOW);                     /* lane slides over the rear duck, it stays */
    set_servo_position(SERVO_GATE_A, GATE_CLOSED);
    msleep(250);
    set_servo_position(SERVO_GATE_B, GATE_OPEN);     /* remaining ducks settle to the rear */
    msleep(400);
}

/* ---------------------------------------------------------------- main */
int main(void) {
    enable_servos();
    gates_init();
    printf("Robot A ready. Waiting for the light.\n");
    while (analog(LIGHT_START) > LIGHT_ON) msleep(10);   /* wait_for_light(LIGHT_START) also works */
    shut_down_in(119.0);                                  /* safety: everything off before 120 s */

    /* 0-16 s: wait for Robot B to clear the upper cup (IR handshake could replace this) */
    msleep(16000);

    /* 16-24 s: north out of the small box, then onto the centre tape at x = 44 */
    move_in(0, 13.9, SPEED_FAST);            /* (54.3, 5.6) -> (54.3, 19.5) */
    /* two axis-aligned legs, not one diagonal: move_in() quantises direction to the sign of
       dx/dy, so a diagonal drives at a fixed 45 deg for a Manhattan tick target and lands
       somewhere else entirely. West first keeps us south of the tape, clear of the ducks. */
    move_in(-10.3, 0, SPEED_FAST);           /* -> (44, 19.5) */
    move_in(0, 6.1, SPEED_FAST);             /* -> (44, 25.6), at the lane mouth */

    /* 24-41 s: swallow the five ducks, line-following east */
    follow_tape_east(36.0, SPEED_LINE);      /* until the touch switch, or 36 in */
    set_servo_position(SERVO_GATE_C, GATE_CLOSED);

    /* zone 2 (TR): strafe north-east, drop, creep forward */
    move_in(0, 8.9, SPEED_FAST);  move_in(-0.5, 0, SPEED_SLOW);   /* -> (79.5, 34.5) */
    drop_one_duck();                                               /* duck at ~(72, 34.5) */

    /* zone 4 (MR) */
    move_in(0, -11.0, SPEED_FAST);                                 /* -> (81, 23.5) */
    drop_one_duck();                                               /* duck at ~(73.6, 23.5) */

    /* west along y = 17, hold until B has finished the cups (timed; IR message is better) */
    move_in(0, -6.5, SPEED_FAST);
    move_in(-25.6, 0, SPEED_FAST);                                 /* -> (56, 17) */
    while (seconds() < 74) msleep(50);

    /* zone 3 (ML) */
    move_in(0, 2.5, SPEED_FAST);                                   /* -> (56, 19.5) */
    move_in(-22.2, 0, SPEED_FAST);                                 /* -> (33.8, 19.5) */
    drop_one_duck();                                               /* duck at ~(26.5, 19.5) */

    /* up the centre column to y = 34.6, west, zone 1 (TL) */
    move_in(10.2, 0, SPEED_FAST);                                  /* -> (48, 19.5) */
    move_in(0, 15.1, SPEED_FAST);                                  /* -> (48, 34.6) */
    move_in(-14.2, 0, SPEED_FAST);                                 /* -> (33.8, 34.6) */
    drop_one_duck();                                               /* duck at ~(26.5, 34.6) */

    /* back down the centre column, west along the bottom, zone 5 (BL) */
    move_in(12.0, 0, SPEED_FAST);                                  /* -> (48, 34.6) */
    move_in(0, -29.0, SPEED_FAST);                                 /* -> (48, 5.6) */
    move_in(-14.0, 0, SPEED_FAST);                                 /* -> (34, 5.6) */
    drop_one_duck();                                               /* duck at ~(26.7, 5.6) */

    stop_all();
    disable_servos();
    printf("Robot A done at %.1f s\n", seconds());
    return 0;
}
