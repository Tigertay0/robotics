/******************************************************************************
 * Robot A - "Duck Runner"                                   2026 Fall Game
 * KIPR Wombat, 4 gear motors on mecanum wheels, 3 servo flaps, tophats.
 *
 * Implements Robot A's route of plan v3 (tools/match_plan.py, checked by
 * tools/match_sim.py: no contact with Robot B or any piece it must not touch).
 * Starts in Zone 5 (large box). Every number marked CALIBRATE was budgeted,
 * not measured: tune it on the real robot before trusting the timeline.
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
#define TOUCH_LANE     0      /* digital: pressed while a duck sits at the exit gate */

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

/* Hand-off times (s after the light). The robots do not talk to each other, so every
   "wait for the other robot" is a fixed time. Same values as T_* in tools/match_plan.py,
   each padded past the moment the simulation says it is safe. CALIBRATE on the table. */
#define T_A_EAST   12.0      /* B has dragged the lower cup west and backed off it  */
#define T_A_WEST   60.0      /* B has left Zone 3 for the bottom wall               */
#define T_A_DOWN   66.0      /* B is parked at the platform                         */

/* A duck is 60 mm long and the exit flap sits 14 mm inside the chassis rear: the robot must move
   60 + 14 + margin = 84 mm (3.3 in) for the rear duck to be completely out. CALIBRATE. */
#define DROP_CREEP_IN   3.3

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

static double t_light;                 /* seconds() when the start light came on */

/* wait until t seconds after the start light */
static void wait_until_s(double t) {
    if (seconds() - t_light > t)       /* late: the hand-off is no longer guaranteed safe */
        printf("late for the %.0f s hand-off: t=%.1f s\n", t, seconds() - t_light);
    while (seconds() - t_light < t && seconds() < MATCH_END_S) msleep(20);
    if (seconds() >= MATCH_END_S)      /* match clock ran out: say so, as every other wait does */
        printf("wait_until_s(%.0f) hit MATCH_END_S at t=%.1f s\n", t, seconds() - t_light);
}

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
    /* Distance is the stop condition. The switch at the rear is NOT: the first duck reaches the
       exit gate (and presses it) while the others are still being swallowed. It is only logged. */
    while (labs(gmpc(FL)) < target && seconds() < MATCH_END_S) {
        int l = analog(TOPHAT_L) < TAPE_THRESHOLD;
        int r = analog(TOPHAT_R) < TAPE_THRESHOLD;
        if (l && !r)      mecanum(speed, +20, 0);   /* drifted right: nudge left  */
        else if (r && !l) mecanum(speed, -20, 0);   /* drifted left: nudge right  */
        else              mecanum(speed, 0, 0);
        msleep(10);
    }
    stop_all();
    printf("follow_tape_east: %ld/%ld ticks, duck at the exit gate=%d, t=%.1f s\n",
           labs(gmpc(FL)), target, digital(TOUCH_LANE), seconds());
}

/* ---------------------------------------------------------------- escapement */
static void gates_init(void) {
    set_servo_position(SERVO_GATE_C, GATE_OPEN);     /* intake open while collecting */
    set_servo_position(SERVO_GATE_B, GATE_OPEN);
    set_servo_position(SERVO_GATE_A, GATE_CLOSED);   /* exit shut */
}

/* After a drop the remaining ducks are one place forward in the lane: pin gate B carried them along.
   Roll forward one duck length with exit A shut and pin B open: the ducks stay on the floor and end up
   against the exit flap again. Call this before every drop except the first. CALIBRATE. */
#define SETTLE_IN   2.4
static void settle_ducks(void) {
    set_servo_position(SERVO_GATE_A, GATE_CLOSED);
    set_servo_position(SERVO_GATE_B, GATE_OPEN);
    msleep(200);
    move_in(SETTLE_IN, 0, SPEED_SLOW);
}

/* release exactly one duck: pin holds duck #2, exit opens, robot creeps forward, exit shuts */
static void drop_one_duck(void) {
    set_servo_position(SERVO_GATE_B, GATE_CLOSED);   /* pin the second duck from the rear */
    msleep(300);
    set_servo_position(SERVO_GATE_A, GATE_OPEN);
    msleep(300);
    move_in(DROP_CREEP_IN, 0, SPEED_SLOW);           /* lane slides off the rear duck, it stays */
    set_servo_position(SERVO_GATE_A, GATE_CLOSED);
    msleep(250);
    set_servo_position(SERVO_GATE_B, GATE_OPEN);     /* the others move to the rear in settle_ducks() */
    msleep(400);
}

/* ---------------------------------------------------------------- main */
int main(void) {
    enable_servos();
    gates_init();
    printf("Robot A ready. Waiting for the light.\n");
    while (analog(LIGHT_START) > LIGHT_ON) msleep(10);   /* wait_for_light(LIGHT_START) also works */
    t_light = seconds();
    shut_down_in(119.0);                                  /* safety: everything off before 120 s */

    /* Plan v3 (tools/match_plan.py, collision-checked by tools/match_sim.py). Frame: inches
       from the inside corner of the bottom-left PVC; A starts in Zone 5 at (28.5, 5.7)
       facing east. Every move is one axis-aligned leg: move_in() cannot drive diagonals. */

    /* 0-3 s: north out of Zone 5, then west, out of the way of B's cup drag along y 12 */
    move_in(0, 12.2, SPEED_FAST);                                  /* -> (28.5, 17.9) */
    move_in(-14.2, 0, SPEED_FAST);                                 /* -> (14.3, 17.9) */
    wait_until_s(T_A_EAST);

    /* side-push the red pom stack and the upper cup north into Zone 1 */
    move_in(25.0, 0, SPEED_FAST);                                  /* -> (39.3, 17.9), under the red stack */
    move_in(0, 10.7, SPEED_SLOW);                                  /* -> (39.3, 28.6): stack + cup go north */
    move_in(0, -3.2, SPEED_FAST);                                  /* -> (39.3, 25.4), lane mouth on the tape */

    /* swallow the five ducks, line-following east */
    /* far enough for the 5th duck to be completely behind intake gate C: 4 ducks are stacked in front of it */
    follow_tape_east(39.1, SPEED_LINE);                            /* -> (78.4, 25.4) */
    set_servo_position(SERVO_GATE_C, GATE_CLOSED);
    msleep(300);
    move_in(-2.5, 0, SPEED_FAST);                                  /* -> (75.9, 25.4): gate C carries the ducks back */

    /* the lane is first in, first out: red leaves first */
    move_in(0, 7.6, SPEED_FAST);                                   /* -> (75.9, 33) */
    /* a dropped duck stays 2.5 in behind the robot's centre (where the rear duck sat in the lane) */
    drop_one_duck();                                               /* Zone 2: red duck at ~(73.4, 33); A -> (79.2, 33) */
    move_in(0, -15.4, SPEED_FAST);                                 /* -> (79.2, 17.6) */
    move_in(-5.2, 0, SPEED_SLOW);                                  /* -> (74, 17.6) */
    settle_ducks();                                                /* -> (76.4, 17.6) */
    drop_one_duck();                                               /* Zone 4: green duck at ~(73.9, 17.6); A -> (79.7, 17.6) */
    move_in(0, 7.3, SPEED_FAST);                                   /* -> (79.7, 24.9) */
    move_in(-35.6, 0, SPEED_FAST);                                 /* -> (44.1, 24.9), west along the empty lane */
    move_in(0, 3.3, SPEED_FAST);                                   /* -> (44.1, 28.2) */
    settle_ducks();                                                /* -> (46.5, 28.2) */
    drop_one_duck();                                               /* Zone 1: lavender duck at ~(44, 28.2); A -> (49.8, 28.2) */
    move_in(0, -7.2, SPEED_FAST);                                  /* -> (49.8, 21) */
    move_in(2.8, 0, SPEED_SLOW);                                   /* -> (52.6, 21), wait clear of B's descent */
    wait_until_s(T_A_WEST);

    move_in(-16.5, 0, SPEED_FAST);                                 /* -> (36.1, 21), through Zone 3 */
    wait_until_s(T_A_DOWN);
    move_in(0, -14.2, SPEED_FAST);                                 /* -> (36.1, 6.8), into Zone 5 */
    settle_ducks();                                                /* -> (38.5, 6.8) */
    drop_one_duck();                                               /* Zone 5: blue duck at ~(36, 6.8); A -> (41.8, 6.8) */
    move_in(0.5, 0, SPEED_SLOW);                                   /* -> (42.3, 6.8) */
    move_in(0, 14.2, SPEED_FAST);                                  /* -> (42.3, 21) */
    settle_ducks();                                                /* -> (44.7, 21) */
    drop_one_duck();                                               /* Zone 3: yellow duck at ~(42.2, 21); A -> (48, 21) */

    stop_all();
    disable_servos();
    printf("Robot A done at %.1f s\n", seconds());
    return 0;
}
