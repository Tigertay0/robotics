/******************************************************************************
 * Robot B - "Point Scorer"                                  2026 Fall Game
 * KIPR Wombat, 2 gear motors (differential), servo arm + claw (printed jaw, print 2,
 * with a liftarm finger on a standard servo), cup-hook servo, camera, 2 tophats, ET, plow lever.
 *
 * Implements Robot B's route of plan v3 (tools/match_plan.py, checked by
 * tools/match_sim.py): starts in the small box facing west at (63.8, 7.15);
 *   lower cup dragged west + flipped into Zone 5 -> red pom -> 4 pom stacks
 *   -> pickleball 1 -> red pom on the platform.
 * B's first run stays south of the duck lane: it never comes near a duck.
 * Numbers marked CALIBRATE were budgeted, not measured.
 *
 * Servo values are last season's measured ones (Botball robotics 2025_26.pdf)
 * for the same arm/claw servos; re-check after rebuilding.
 *****************************************************************************/
#include <kipr/wombat.h>
#include <stdio.h>
#include <stdlib.h>    /* labs */
#include <math.h>

/* ---------------------------------------------------------------- ports */
#define LEFT   0
#define RIGHT  2
#define SERVO_ARM    1            /* shoulder (regular servo)      */
#define SERVO_CLAW   2            /* claw finger (standard servo)  */
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
#define TRACK_IN        6.06               /* CALIBRATE: wheel centre to wheel centre (154 mm) */
#define TAPE_THRESHOLD  2700               /* CALIBRATE: analog (12-bit) < this = black */
#define LIGHT_ON        770
#define SPEED_FAST      80
#define SPEED_PUSH      45
#define MATCH_END_S     118

/* Hand-off time (s after the light): A has swallowed the ducks past the centre line.
   Same as T_B_north in tools/match_plan.py, padded past the safe moment. CALIBRATE. */
#define T_B_NORTH       26.0

#define ARM_UP        860                  /* measured last season */
#define ARM_DOWN     1750
#define ARM_PLATFORM  600                  /* CALIBRATE: claw above the 5.7 in platform edge */
#define CLAW_OPEN    2000                  /* CALIBRATE: liftarm finger swung out, away from the printed jaw */
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
    if (labs(gmpc(LEFT)) < target)   /* ran out of match clock: say so, or every later move
                                        silently no-ops and the log shows nothing wrong */
        printf("forward_in(%.1f) stopped at %ld/%ld ticks, t=%.1f s\n",
               inches, labs(gmpc(LEFT)), target, seconds());
    msleep(150);
}
/* positive = counter-clockwise (turn left), in place */
static void turn_deg(double deg, int speed) {
    long target = (long)(fabs(deg) * TICKS_PER_DEG);
    cmpc(LEFT);
    if (deg > 0) drive(-speed, speed); else drive(speed, -speed);
    while (labs(gmpc(LEFT)) < target && seconds() < MATCH_END_S) msleep(5);
    stop_all();
    if (labs(gmpc(LEFT)) < target)
        printf("turn_deg(%.1f) stopped at %ld/%ld ticks, t=%.1f s\n",
               deg, labs(gmpc(LEFT)), target, seconds());
    msleep(200);
}
/* arc of a given radius (inches, to the robot centre); deg > 0 = left (CCW), as turn_deg */
static void arc_r(double radius, double deg, int speed) {
    double ro = radius + TRACK_IN / 2, ri = radius - TRACK_IN / 2;
    int inner = (int)(speed * ri / ro);
    long target = (long)(fabs(deg) * M_PI / 180.0 * ro * TICKS_PER_INCH);   /* outer wheel path */
    int outer_port = deg > 0 ? RIGHT : LEFT;
    cmpc(outer_port);
    if (deg > 0) drive(inner, speed); else drive(speed, inner);
    while (labs(gmpc(outer_port)) < target && seconds() < MATCH_END_S) msleep(5);
    stop_all();
    if (labs(gmpc(outer_port)) < target)
        printf("arc_r(%.1f, %.1f) stopped short, t=%.1f s\n", radius, deg, seconds());
    msleep(150);                 /* settle, as forward_in and turn_deg do */
}

static double t_light;          /* seconds() when the start light came on */

/* wait until t seconds after the start light */
static void wait_until_s(double t) {
    if (seconds() - t_light > t)       /* late: the hand-off is no longer guaranteed safe */
        printf("late for the %.0f s hand-off: t=%.1f s\n", t, seconds() - t_light);
    while (seconds() - t_light < t) msleep(20);
}

/* ---------------------------------------------------------------- tools */
/* The hook catches the upside-down lower cup's rim and drags it west along the lower
   tape; a 20 deg pivot to the left then rolls it upright off the tape (the right plow
   wing pushes its base). CALIBRATE the hook height on the real cup. */
static void drag_and_flip_cup(double drag_in) {
    set_servo_position(SERVO_HOOK, HOOK_DOWN);
    msleep(300);
    forward_in(drag_in, SPEED_PUSH);
    turn_deg(+20, SPEED_PUSH);
    set_servo_position(SERVO_HOOK, HOOK_UP);
    msleep(300);
}

/* Find the red pom with the camera, centre on it, grab it. Returns 1 on success.
   Everything after this call is dead reckoning from the pre-scan pose, so the scan
   rotation and the approach are both undone before returning, on success and failure
   alike. Without that, a pom that is a few degrees off frame leaves the robot facing
   an arbitrary direction for the whole rest of the match. */
static int grab_red_pom(void) {
    set_servo_position(SERVO_CLAW, CLAW_OPEN);
    set_servo_position(SERVO_ARM, ARM_DOWN);
    msleep(400);
    camera_open();
    const int CAM_TRIES = 40;                                /* x 100 ms = ~4 s budget */
    int found = 0;
    cmpc(LEFT);                                              /* net scan rotation, in ticks */
    for (int tries = 0; tries < CAM_TRIES && !found; tries++) {
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
    long spun = gmpc(LEFT);                                  /* signed: which way we turned */
    if (found) {
        forward_in(2.0, 30);
        set_servo_position(SERVO_CLAW, CLAW_CLOSED);
        msleep(400);
        set_servo_position(SERVO_ARM, ARM_UP);
        msleep(400);
        forward_in(-2.0, 30);                                /* undo the approach */
    } else {
        printf("red pom not seen in %d camera frames\n", CAM_TRIES);
        set_servo_position(SERVO_ARM, ARM_UP);
    }
    /* unwind the scan rotation back to the heading the caller assumes */
    if (labs(spun) > 20) {
        cmpc(LEFT);
        if (spun > 0) drive(-25, 25); else drive(25, -25);   /* spun>0 = turned right: turn back left */
        while (labs(gmpc(LEFT)) < labs(spun) && seconds() < MATCH_END_S) msleep(5);
        stop_all();
        msleep(200);
    }
    return found;
}

/* facing north on the travel line: push one pom stack into Zone 1 and back off */
static void push_stack_north(double push_in) {
    forward_in(push_in, SPEED_PUSH);
    forward_in(-push_in, SPEED_FAST);
}

/* ---------------------------------------------------------------- main */
int main(void) {
    enable_servos();
    set_servo_position(SERVO_ARM, ARM_UP);
    set_servo_position(SERVO_CLAW, CLAW_OPEN);
    set_servo_position(SERVO_HOOK, HOOK_UP);
    printf("Robot B ready. Waiting for the light.\n");
    while (analog(LIGHT_START) > LIGHT_ON) msleep(10);
    t_light = seconds();
    shut_down_in(119.0);

    /* 0-7 s: the lower cup (hook side = right = north while facing west) */
    forward_in(8.4, SPEED_PUSH);                /* (63.8, 7.15) -> (55.4, 7.15): hook meets the cup */
    drag_and_flip_cup(18.4);                    /* -> (37, 7.15); cup upright at ~(27, 8.9), its poms spill */
    forward_in(-2.5, SPEED_FAST);               /* back off along 200 deg -> (39.4, 8.0) */
    turn_deg(-20, SPEED_FAST);                  /* square up facing west */
    forward_in(-2.45, SPEED_FAST);              /* -> (41.8, 8.0): claw clear of the cup */

    /* 7-10 s: the red pom */
    int have_red = grab_red_pom();
    if (!have_red) printf("red pom not found, skipping the platform\n");

    /* wait (holding the pom) until A has swallowed the ducks past the centre line */
    wait_until_s(T_B_NORTH);
    turn_deg(-90, SPEED_FAST);                  /* facing west -> clockwise 90 = face north */
    forward_in(9.5, SPEED_FAST);                /* -> (41.8, 17.5), the Zone 3 travel line */
    turn_deg(+90, SPEED_FAST);                  /* face west */

    /* 4 pom stacks, east to west, each pushed north into Zone 1 (A already moved the red one) */
    const double stack_x[4] = { 32.0, 24.0, 16.0, 11.0 };     /* B centre; the gold stack is at x 8 */
    const double push_in[4] = { 9.48, 9.48, 9.48, 5.48 };      /* gold only to y 29: clears turquoise */
    double x = 41.8;
    for (int k = 0; k < 4; k++) {
        forward_in(x - stack_x[k], SPEED_FAST);
        x = stack_x[k];
        turn_deg(-90, SPEED_FAST);              /* face north */
        push_stack_north(push_in[k]);
        if (k < 3) turn_deg(+90, SPEED_FAST);   /* face west again */
    }

    /* down to the bottom wall east of the cup, then east to pickleball 1 */
    turn_deg(-90, SPEED_FAST);                  /* north -> east at (11, 17.5) */
    forward_in(21.5, SPEED_FAST);               /* -> (32.5, 17.5) */
    arc_r(5.0, -90, SPEED_PUSH);                /* -> (37.5, 12.5) facing south */
    arc_r(4.9, +90, SPEED_PUSH);                /* -> (42.4, 7.6) facing east */
    set_servo_position(SERVO_HOOK, HOOK_DOWN);  /* hook sweeps the ball off its post */
    forward_in(2.5, SPEED_PUSH);
    set_servo_position(SERVO_HOOK, HOOK_UP);
    forward_in(14.0, SPEED_PUSH);               /* -> (58.9, 7.6): ball rolls under the platform */

    /* red pom alone on the platform (the big duck is allowed next to it) */
    if (have_red) {
        set_servo_position(SERVO_ARM, ARM_PLATFORM);
        msleep(1200);
        set_servo_position(SERVO_CLAW, CLAW_OPEN);
        msleep(400);
        set_servo_position(SERVO_ARM, ARM_UP);
    }

    stop_all();
    disable_servos();
    printf("Robot B done at %.1f s\n", seconds() - t_light);
    return 0;
}
